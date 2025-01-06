from docx import Document
import docx.oxml as oxml
from docx.shared import RGBColor, Pt
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from .base import WatermarkBase
import random
import json
import os
import hashlib

class WordWatermark(WatermarkBase):
    def __init__(self):
        super().__init__()
        self.watermark_locations = []

    def embed_watermark(self, file_path, watermark_data, password):
        """在Word文档中嵌入水印"""
        try:
            doc = Document(file_path)
            
            # 准备要嵌入的核心数据
            core_data = {
                'content': watermark_data['content'],
                'user': watermark_data['user']
            }
            
            # 1. 在文档样式中嵌入
            self._embed_in_styles(doc, core_data)
            
            # 2. 在文档关系中嵌入
            self._embed_in_rels(doc, core_data)
            
            # 3. 在自定义XML中嵌入
            self._embed_in_custom_xml(doc, core_data)
            
            # 保存文档
            output_path = os.path.join(os.path.dirname(file_path), 
                                     f'processed_{os.path.basename(file_path)}')
            doc.save(output_path)
            return output_path
            
        except Exception as e:
            print(f"Error in embed_watermark: {str(e)}")
            raise

    def _embed_in_styles(self, doc, core_data):
        """在文档样式中嵌入水印"""
        try:
            # 获取默认样式
            default_style = doc.styles['Normal']._element
            
            # 生成唯一的rsid值并存储完整数据
            rsid_data = {
                'rsid': hashlib.sha256(json.dumps(core_data).encode()).hexdigest()[:8],
                'data': self._hide_in_property(json.dumps(core_data))
            }
            
            # 在样式属性中嵌入信息
            default_style.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsid', 
                             json.dumps(rsid_data))
            
            # 记录位置
            self.watermark_locations.append(('style', rsid_data['rsid']))
            
        except Exception as e:
            print(f"Error embedding in styles: {str(e)}")

    def _embed_in_rels(self, doc, core_data):
        """在文档关系中嵌入水印"""
        try:
            # 获取文档主要部分
            main_part = doc.part
            
            # 创建一个新的自定义XML部分
            custom_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <watermark xmlns="http://schemas.custom.org/watermark/1.0">
                <data>{self._hide_in_property(json.dumps(core_data))}</data>
            </watermark>"""
            
            # 添加自定义XML部分
            custom_part = main_part._package.parts.add_part(
                '/customXml/item1.xml',
                content_type='application/xml',
                blob=custom_xml.encode('utf-8')
            )
            
            # 添加关系
            rel_id = main_part.relate_to(custom_part, 'http://schemas.custom.org/watermark')
            
            # 记录位置
            self.watermark_locations.append(('rel', rel_id))
            
        except Exception as e:
            print(f"Error embedding in rels: {str(e)}")

    def _embed_in_custom_xml(self, doc, core_data):
        """在自定义XML中嵌入水印"""
        try:
            # 创建自定义XML
            custom_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <watermark:settings xmlns:watermark="http://schemas.custom.org/watermark/1.0">
                <watermark:data>{self._hide_in_property(json.dumps(core_data))}</watermark:data>
                <watermark:hash>{hashlib.sha256(json.dumps(core_data).encode()).hexdigest()}</watermark:hash>
            </watermark:settings>"""
            
            # 添加到文档
            settings_part = doc.part._package.parts.add_part(
                '/customXml/item2.xml',
                content_type='application/xml',
                blob=custom_xml.encode('utf-8')
            )
            
            # 记录位置
            self.watermark_locations.append(('xml', settings_part.partname))
            
        except Exception as e:
            print(f"Error embedding in custom xml: {str(e)}")

    def extract_watermark(self, file_path):
        """从Word文档中提取水印"""
        try:
            doc = Document(file_path)
            watermark_data = None
            
            # 1. 从样式中提取
            style_data = self._extract_from_styles(doc)
            if style_data:
                watermark_data = style_data
            
            # 2. 从关系中提取
            rel_data = self._extract_from_rels(doc)
            if rel_data:
                # 验证数据一致性
                if watermark_data and watermark_data != rel_data:
                    return None
                watermark_data = rel_data
            
            # 3. 从自定义XML中提取
            xml_data = self._extract_from_custom_xml(doc)
            if xml_data:
                # 验证数据一致性
                if watermark_data and watermark_data != xml_data:
                    return None
                watermark_data = xml_data
            
            return watermark_data
            
        except Exception as e:
            print(f"Error extracting watermark: {str(e)}")
            return None

    def _extract_from_styles(self, doc):
        """从文档样式中提取水印"""
        try:
            # 获取默认样式
            default_style = doc.styles['Normal']._element
            
            # 获取rsid值
            rsid_json = default_style.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rsid')
            
            if rsid_json:
                try:
                    # 解析存储的数据
                    rsid_data = json.loads(rsid_json)
                    if isinstance(rsid_data, dict) and 'data' in rsid_data:
                        # 解码隐藏的数据
                        hidden_data = self._reveal_from_property(rsid_data['data'])
                        if hidden_data:
                            return json.loads(hidden_data)
                except:
                    pass
            return None
        except Exception as e:
            print(f"Error extracting from styles: {str(e)}")
            return None

    def _extract_from_rels(self, doc):
        """从文档关系中提取水印"""
        try:
            main_part = doc.part
            
            # 遍历所有关系
            for rel in main_part.rels:
                if main_part.rels[rel].reltype == 'http://schemas.custom.org/watermark':
                    # 获取自定义XML部分
                    custom_part = main_part.rels[rel].target_part
                    xml_data = custom_part.blob.decode('utf-8')
                    
                    # 提取数据
                    if '<data>' in xml_data and '</data>' in xml_data:
                        start = xml_data.find('<data>') + len('<data>')
                        end = xml_data.find('</data>')
                        hidden_data = xml_data[start:end]
                        
                        # 解码数据
                        decoded_data = self._reveal_from_property(hidden_data)
                        if decoded_data:
                            return json.loads(decoded_data)
            return None
        except Exception as e:
            print(f"Error extracting from rels: {str(e)}")
            return None

    def _extract_from_custom_xml(self, doc):
        """从自定义XML中提取水印"""
        try:
            # 遍历所有部分
            for part in doc.part.package.parts:
                if part.partname.startswith('/customXml/'):
                    xml_data = part.blob.decode('utf-8')
                    
                    # 检查是否是水印XML
                    if '<watermark:data>' in xml_data and '</watermark:data>' in xml_data:
                        start = xml_data.find('<watermark:data>') + len('<watermark:data>')
                        end = xml_data.find('</watermark:data>')
                        hidden_data = xml_data[start:end]
                        
                        # 解码数据
                        decoded_data = self._reveal_from_property(hidden_data)
                        if decoded_data:
                            return json.loads(decoded_data)
            return None
        except Exception as e:
            print(f"Error extracting from custom xml: {str(e)}")
            return None

    def _hide_in_property(self, text):
        """将信息隐藏在属性值中"""
        if not text:
            return ''
        # 使用特殊字符混淆数据
        chars = list(text)
        for i in range(len(chars)):
            if i % 2 == 0:
                chars.insert(i, '\u200b')
        return ''.join(chars)

    def _reveal_from_property(self, text):
        """从属性值中提取信息"""
        if not text:
            return ''
        return ''.join(c for c in text if c != '\u200b')

    def _combine_watermark_parts(self, parts):
        """合并并验证水印部分"""
        if not parts:
            return None
            
        # 验证所有部分的一致性
        reference = parts[0]
        for part in parts[1:]:
            if part != reference:
                return None
        
        return reference 