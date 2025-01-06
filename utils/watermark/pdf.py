from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from io import BytesIO
from .base import WatermarkBase
import random
import json
import hashlib
import os
from PyPDF2.generic import DecodedStreamObject, EncodedStreamObject, NameObject, createStringObject, ArrayObject, DictionaryObject

class PDFWatermark(WatermarkBase):
    def embed_watermark(self, file_path, watermark_data, password):
        """在PDF文档中嵌入水印"""
        try:
            reader = PdfReader(file_path)
            writer = PdfWriter()
            
            # 准备要嵌入的核心数据
            core_data = {
                'content': watermark_data['content'],
                'user': watermark_data['user']
            }
            
            # 1. 在XMP元数据中嵌入
            self._embed_in_xmp(writer, core_data)
            
            # 2. 在文档目录中嵌入
            self._embed_in_catalog(writer, core_data)
            
            # 3. 复制并处理所有页面
            for page in reader.pages:
                # 复制原始页面
                writer.add_page(page)
                # 在页面结构中嵌入水印
                self._embed_in_page_structure(writer.pages[-1], core_data)
            
            # 保存文档
            output_path = os.path.join(os.path.dirname(file_path), 
                                     f'processed_{os.path.basename(file_path)}')
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            print(f"Error in embed_watermark: {str(e)}")
            raise

    def _embed_in_xmp(self, writer, core_data):
        """在XMP元数据中嵌入水印"""
        try:
            # 生成唯一标识
            xmp_id = hashlib.sha256(json.dumps(core_data).encode()).hexdigest()[:8]
            
            # 创建XMP元数据
            xmp = f"""<?xpacket begin='' id='{xmp_id}'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
    <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
        <rdf:Description rdf:about=''
            xmlns:dc='http://purl.org/dc/elements/1.1/'>
            <dc:description>{self._hide_in_property(json.dumps(core_data))}</dc:description>
        </rdf:Description>
    </rdf:RDF>
</x:xmpmeta>
<?xpacket end='r'?>"""
            
            # 创建元数据流对象
            metadata = DecodedStreamObject()
            metadata.set_data(xmp.encode('utf-8'))
            
            # 添加到文档目录
            writer._info = DictionaryObject()
            writer._info[NameObject('/Metadata')] = metadata
            
        except Exception as e:
            print(f"Error embedding in XMP: {str(e)}")

    def _embed_in_catalog(self, writer, core_data):
        """在文档目录中嵌入水印"""
        try:
            # 生成唯一标识
            catalog_id = hashlib.sha256(json.dumps(core_data).encode()).hexdigest()[:8]
            
            # 创建自定义数据对象
            custom_data = DictionaryObject()
            custom_data[NameObject('/WatermarkID')] = createStringObject(catalog_id)
            custom_data[NameObject('/Data')] = createStringObject(
                self._hide_in_property(json.dumps(core_data))
            )
            
            # 添加到文档目录
            if not hasattr(writer, '_root_object'):
                writer._root_object = DictionaryObject()
            writer._root_object[NameObject('/WatermarkData')] = custom_data
            
        except Exception as e:
            print(f"Error embedding in catalog: {str(e)}")

    def _embed_in_page_structure(self, page, core_data):
        """在页面结构中嵌入水印"""
        try:
            # 生成唯一标识
            page_id = hashlib.sha256(json.dumps(core_data).encode()).hexdigest()[:8]
            
            # 创建自定义数据对象
            custom_data = DictionaryObject()
            custom_data[NameObject('/WatermarkID')] = createStringObject(page_id)
            custom_data[NameObject('/Data')] = createStringObject(
                self._hide_in_property(json.dumps(core_data))
            )
            
            # 添加到页面字典
            page[NameObject('/WatermarkData')] = custom_data
            
        except Exception as e:
            print(f"Error embedding in page structure: {str(e)}")

    def extract_watermark(self, file_path):
        """从PDF文档中提取水印"""
        try:
            reader = PdfReader(file_path)
            watermark_data = None
            
            # 1. 从XMP元数据中提取
            xmp_data = self._extract_from_xmp(reader)
            if xmp_data:
                watermark_data = xmp_data
            
            # 2. 从目录中提取
            catalog_data = self._extract_from_catalog(reader)
            if catalog_data:
                # 验证数据一致性
                if watermark_data and watermark_data != catalog_data:
                    return None
                watermark_data = catalog_data
            
            # 3. 从页面结构中提取
            page_data = self._extract_from_page_structure(reader)
            if page_data:
                # 验证数据一致性
                if watermark_data and watermark_data != page_data:
                    return None
                watermark_data = page_data
            
            return watermark_data
            
        except Exception as e:
            print(f"Error extracting watermark: {str(e)}")
            return None

    def _extract_from_xmp(self, reader):
        """从XMP元数据中提取水印"""
        try:
            if reader.trailer and '/Root' in reader.trailer:
                root = reader.trailer['/Root']
                if '/Metadata' in root:
                    xmp = root['/Metadata'].get_data()
                    # 解析XMP并提取数据
                    if b'<dc:description>' in xmp:
                        start = xmp.find(b'<dc:description>') + len(b'<dc:description>')
                        end = xmp.find(b'</dc:description>')
                        hidden_data = xmp[start:end].decode('utf-8')
                        return json.loads(self._reveal_from_property(hidden_data))
            return None
        except Exception as e:
            print(f"Error extracting from XMP: {str(e)}")
            return None

    def _extract_from_catalog(self, reader):
        """从目录中提取水印"""
        try:
            if reader.trailer and '/Root' in reader.trailer:
                root = reader.trailer['/Root']
                if '/WatermarkData' in root:
                    watermark_data = root['/WatermarkData']
                    if '/Data' in watermark_data:
                        hidden_data = str(watermark_data['/Data'])
                        return json.loads(self._reveal_from_property(hidden_data))
            return None
        except Exception as e:
            print(f"Error extracting from catalog: {str(e)}")
            return None

    def _extract_from_page_structure(self, reader):
        """从页面结构中提取水印"""
        try:
            for page in reader.pages:
                if '/WatermarkData' in page:
                    watermark_data = page['/WatermarkData']
                    if '/Data' in watermark_data:
                        hidden_data = str(watermark_data['/Data'])
                        return json.loads(self._reveal_from_property(hidden_data))
            return None
        except Exception as e:
            print(f"Error extracting from page structure: {str(e)}")
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