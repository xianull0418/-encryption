from cryptography.fernet import Fernet
import os
import base64

class FileEncryptor:
    def __init__(self, key=None):
        """初始化加密器，可以提供密钥或自动生成"""
        if key:
            self.key = base64.urlsafe_b64encode(key.ljust(32)[:32].encode())
        else:
            self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)

    def encrypt_file(self, input_path, output_path=None):
        """加密文件"""
        if output_path is None:
            filename, ext = os.path.splitext(input_path)
            output_path = f"{filename}_encrypted{ext}"

        try:
            # 读取原文件
            with open(input_path, 'rb') as file:
                file_data = file.read()

            # 加密数据
            encrypted_data = self.cipher_suite.encrypt(file_data)

            # 保存加密后的文件
            with open(output_path, 'wb') as file:
                file.write(encrypted_data)

            return output_path

        except Exception as e:
            raise Exception(f"加密文件时出错: {str(e)}")

    def decrypt_file(self, input_path, output_path=None):
        """解密文件"""
        if output_path is None:
            filename, ext = os.path.splitext(input_path)
            output_path = f"{filename}_decrypted{ext}"

        try:
            # 读取加密文件
            with open(input_path, 'rb') as file:
                encrypted_data = file.read()

            # 解密数据
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)

            # 保存解密后的文件
            with open(output_path, 'wb') as file:
                file.write(decrypted_data)

            return output_path

        except Exception as e:
            raise Exception(f"解密文件时出错: {str(e)}") 