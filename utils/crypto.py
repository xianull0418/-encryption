# 零宽字符编码
ZERO_WIDTH_SPACE = '\u200b'  # 零宽空格
ZERO_WIDTH_NON_JOINER = '\u200c'  # 零宽非连接符
ZERO_WIDTH_JOINER = '\u200d'  # 零宽连接符

def encrypt_text(text, secret):
    """文本加密函数"""
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        if isinstance(secret, bytes):
            secret = secret.decode('utf-8')
        
        # 将密钥转换为二进制字符串
        binary_secret = ''.join(format(ord(c), '08b') for c in secret)
        
        # 添加固定的开始和结束标记
        marker = '11111111'  # 8个1作为标记
        final_binary = marker + binary_secret + marker
        
        print(f"Binary secret: {binary_secret}")
        print(f"Final binary: {final_binary}")
        print(f"Binary length: {len(final_binary)}")
        
        # 使用零宽字符替换二进制位
        zero_width_secret = ''
        for bit in final_binary:
            if bit == '0':
                zero_width_secret += ZERO_WIDTH_SPACE
            else:
                zero_width_secret += ZERO_WIDTH_JOINER
        
        result = text + zero_width_secret
        print(f"Original text length: {len(text)}")
        print(f"Encrypted text length: {len(result)}")
        print(f"Zero-width characters: {len(zero_width_secret)}")
        return result
    except Exception as e:
        print(f"Encryption error: {str(e)}")
        return text

def decrypt_text(text):
    """文本解密函数"""
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        # 提取零宽字符
        zero_width_chars = []
        for c in text:
            if c in [ZERO_WIDTH_SPACE, ZERO_WIDTH_JOINER]:
                zero_width_chars.append(c)
        
        print(f"Found {len(zero_width_chars)} zero-width characters")
        
        if not zero_width_chars:
            print("No zero-width characters found")
            return ""
        
        # 转换回二进制字符串
        binary_secret = ''
        for c in zero_width_chars:
            if c == ZERO_WIDTH_SPACE:
                binary_secret += '0'
            elif c == ZERO_WIDTH_JOINER:
                binary_secret += '1'
        
        print(f"Full binary string: {binary_secret}")
        
        # 查找开始和结束标记
        marker = '11111111'
        start_pos = binary_secret.find(marker)
        if start_pos == -1:
            print("Start marker not found")
            return ""
            
        end_pos = binary_secret.rfind(marker)
        if end_pos == -1 or end_pos == start_pos:
            print("End marker not found")
            return ""
        
        # 提取实际的二进制数据（不包括标记）
        binary_data = binary_secret[start_pos + 8:end_pos]
        print(f"Extracted binary data: {binary_data}")
        print(f"Binary data length: {len(binary_data)}")
        
        # 确保二进制数据长度是8的倍数
        if len(binary_data) % 8 != 0:
            missing_bits = 8 - (len(binary_data) % 8)
            binary_data = binary_data + '0' * missing_bits
            print(f"Padded binary data: {binary_data}")
            print(f"New binary data length: {len(binary_data)}")
        
        # 转换为字符
        secret = ''
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i:i+8]
            try:
                char_code = int(byte, 2)
                secret += chr(char_code)
                print(f"Converted byte {byte} to character {chr(char_code)}")
            except ValueError as e:
                print(f"Error converting binary to character: {str(e)}")
                continue
        
        print(f"Decrypted secret: {secret}")
        return secret
    except Exception as e:
        print(f"Decryption error: {str(e)}")
        return "" 