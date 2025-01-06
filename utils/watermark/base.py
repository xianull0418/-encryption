from abc import ABC, abstractmethod
import time
import socket
from .crypto import WatermarkCrypto

class WatermarkBase(ABC):
    def __init__(self):
        self.timestamp = time.time()
        self.ip = socket.gethostbyname(socket.gethostname())
        self.crypto = WatermarkCrypto()
    
    def generate_watermark(self, content, user_info, password):
        """生成水印信息"""
        watermark_data = {
            'content': content,
            'user': user_info,
            'timestamp': self.timestamp,
            'ip': self.ip,
            'type': self.__class__.__name__
        }
        
        # 加密水印数据
        encrypted_data = self.crypto.encrypt_data(watermark_data, password)
        
        # 生成零宽字符编码
        zero_width_data = self.crypto.encode_to_zero_width(encrypted_data)
        
        return {
            'encrypted': encrypted_data,
            'zero_width': zero_width_data
        }
    
    def verify_watermark(self, file_path, password):
        """验证水印"""
        try:
            # 提取水印
            watermark_data = self.extract_watermark(file_path)
            if not watermark_data:
                return False, "未找到水印"
            
            # 解密水印
            decrypted_data = self.crypto.decrypt_data(watermark_data, password)
            
            # 验证文件类型
            if decrypted_data.get('type') != self.__class__.__name__:
                return False, "水印类型不匹配"
            
            return True, decrypted_data
            
        except Exception as e:
            return False, f"水印验证失败: {str(e)}"
    
    @abstractmethod
    def embed_watermark(self, file_path, watermark_data):
        """嵌入水印"""
        pass
    
    @abstractmethod
    def extract_watermark(self, file_path):
        """提取水印"""
        pass 