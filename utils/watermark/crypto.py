from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import os
import json
import zlib

class WatermarkCrypto:
    def __init__(self):
        self.ZERO_WIDTH_CHARS = {
            '0': '\u200b',  # 零宽空格
            '1': '\u200c',  # 零宽非连接符
            '2': '\u200d',  # 零宽连接符
            '3': '\u2060',  # 词组连接符
            '4': '\u2061',  # 函数应用
            '5': '\u2062',  # 不可见乘号
            '6': '\u2063',  # 不可见分隔符
            '7': '\u2064',  # 不可见加号
        }
        self.SALT_LENGTH = 16
        self.IV_LENGTH = 16

    def _calculate_checksum(self, data):
        """计算校验和"""
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(data)
        return base64.b64encode(hasher.finalize()).decode()

    def _verify_checksum(self, data, checksum):
        """验证校验和"""
        return self._calculate_checksum(data) == checksum

    def encrypt_data(self, data, password):
        """加密数据"""
        try:
            # 1. 生成加密密钥
            key, salt = self.generate_key(password)
            fernet = Fernet(key)
            
            # 2. 压缩数据
            compressed_data = zlib.compress(json.dumps(data).encode())
            
            # 3. 加密数据
            encrypted_data = fernet.encrypt(compressed_data)
            
            # 4. 添加校验和
            checksum = self._calculate_checksum(encrypted_data)
            
            # 5. 组合最终数据
            final_data = {
                'salt': base64.b64encode(salt).decode(),
                'data': base64.b64encode(encrypted_data).decode(),
                'checksum': checksum
            }
            
            return final_data
        except Exception as e:
            print(f"Encryption error: {str(e)}")
            raise

    def decrypt_data(self, encrypted_package, password):
        """解密数据"""
        try:
            # 1. 解析数据包
            salt = base64.b64decode(encrypted_package['salt'])
            encrypted_data = base64.b64decode(encrypted_package['data'])
            checksum = encrypted_package['checksum']
            
            # 2. 验证校验和
            if not self._verify_checksum(encrypted_data, checksum):
                raise ValueError("数据完整性验证失败")
            
            # 3. 生成解密密钥
            key, _ = self.generate_key(password, salt)
            fernet = Fernet(key)
            
            # 4. 解密数据
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # 5. 解压数据
            decompressed_data = zlib.decompress(decrypted_data)
            
            return json.loads(decompressed_data)
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            raise ValueError(f"解密失败: {str(e)}")

    def generate_key(self, password, salt=None):
        """生成加密密钥"""
        if salt is None:
            salt = os.urandom(self.SALT_LENGTH)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    def encode_to_zero_width(self, data):
        """将数据编码为零宽字符"""
        try:
            # 1. 将数据转换为base64
            base64_data = base64.b64encode(json.dumps(data).encode()).decode()
            
            # 2. 转换为8进制字符串
            oct_str = ''.join(format(ord(c), '08o') for c in base64_data)
            
            # 3. 使用零宽字符编码
            result = ''
            for digit in oct_str:
                result += self.ZERO_WIDTH_CHARS[digit]
            
            return result
        except Exception as e:
            print(f"Encoding error: {str(e)}")
            raise

    def decode_from_zero_width(self, text):
        """从零宽字符解码数据"""
        try:
            # 1. 提取零宽字符
            zero_width_chars = []
            reverse_map = {v: k for k, v in self.ZERO_WIDTH_CHARS.items()}
            
            for char in text:
                if char in reverse_map:
                    zero_width_chars.append(reverse_map[char])
            
            if not zero_width_chars:
                return None
            
            # 2. 转换回8进制字符串
            oct_str = ''.join(zero_width_chars)
            
            # 3. 转换为原始字符串
            base64_data = ''
            for i in range(0, len(oct_str), 8):
                oct_group = oct_str[i:i+8]
                if len(oct_group) == 8:
                    base64_data += chr(int(oct_group, 8))
            
            # 4. 解码base64数据
            decoded_data = base64.b64decode(base64_data).decode()
            return json.loads(decoded_data)
            
        except Exception as e:
            print(f"Decoding error: {str(e)}")
            return None 