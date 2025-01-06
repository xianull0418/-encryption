from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from utils.crypto import encrypt_text, decrypt_text
from utils.file_crypto import FileEncryptor
from utils.watermark.word import WordWatermark
from utils.watermark.ppt import PPTWatermark
from utils.watermark.pdf import PDFWatermark
import os
import base64
import tempfile

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 支持的水印处理器
WATERMARK_HANDLERS = {
    '.docx': WordWatermark(),
    '.pptx': PPTWatermark(),
    '.pdf': PDFWatermark()
}

@app.route('/')
def index():
    return redirect(url_for('text_page'))

@app.route('/text')
def text_page():
    return render_template('text.html')

@app.route('/file')
def file_page():
    return render_template('file.html')

@app.route('/watermark')
def watermark_page():
    return render_template('watermark.html')

# 文本加密解密路由
@app.route('/encrypt', methods=['POST'])
def encrypt():
    text = request.form['text']
    secret = request.form['secret']
    result = encrypt_text(text, secret)
    return jsonify({'result': result, 'action': '加密'})

@app.route('/decrypt', methods=['POST'])
def decrypt():
    text = request.form['text']
    result = decrypt_text(text)
    return jsonify({'result': result, 'action': '解密'})

# 文件加密解密路由
@app.route('/encrypt_file', methods=['POST'])
def encrypt_file():
    if 'file' not in request.files:
        return jsonify({'result': [{'error': "未找到文件"}], 'action': '错误'})
    
    files = request.files.getlist('file')  # 获取所有文件
    username = request.form.get('username', '')
    content = request.form.get('content', '')  # 要隐藏的信息
    
    if not files or files[0].filename == '':
        return jsonify({'result': [{'error': "未选择文件"}], 'action': '错误'})
    
    if not username or not content:
        return jsonify({'result': [{'error': "请提供用户名和要隐藏的信息"}], 'action': '错误'})
    
    results = []
    for file in files:
        filename = file.filename
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # 保存上传的文件
            file.save(input_path)
            
            # 获取文件类型并处理
            ext = os.path.splitext(filename)[1].lower()
            if ext in WATERMARK_HANDLERS:
                try:
                    # 添加水印（隐藏信息）
                    handler = WATERMARK_HANDLERS[ext]
                    watermarked_path = handler.embed_watermark(
                        input_path,
                        {
                            'content': content,  # 要隐藏的信息
                            'user': username     # 用户名
                        },
                        username  # 使用用户名作为密钥
                    )
                    
                    # 读取处理后的文件并返回
                    with open(watermarked_path, 'rb') as f:
                        file_content = f.read()
                        results.append({
                            'filename': f'processed_{filename}',
                            'content': base64.b64encode(file_content).decode('utf-8')
                        })
                    
                    # 清理处理后的文件
                    if os.path.exists(watermarked_path):
                        os.remove(watermarked_path)
                    
                except Exception as e:
                    results.append({'error': f"{filename}: 处理失败 - {str(e)}"})
            else:
                results.append({'error': f"{filename}: 不支持的文件类型"})
            
        except Exception as e:
            results.append({'error': f"{filename}: {str(e)}"})
        finally:
            # 清理临时文件
            if os.path.exists(input_path):
                os.remove(input_path)
    
    if not results:
        return jsonify({'result': [{'error': "处理失败"}], 'action': '错误'})
    
    return jsonify({
        'result': results,
        'action': '处理完成'
    })

# 水印相关路由
@app.route('/api/embed_watermark', methods=['POST'])
def embed_watermark():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未找到文件'})
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'message': '未选择文件'})
        
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in WATERMARK_HANDLERS:
            return jsonify({'success': False, 'message': '不支持的文件类型'})
        
        content = request.form.get('content')
        user = request.form.get('user')
        password = request.form.get('password')
        
        if not all([content, user, password]):
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(temp_path)
        
        try:
            handler = WATERMARK_HANDLERS[ext]
            watermarked_path = handler.embed_watermark(
                temp_path,
                {'content': content, 'user': user},
                password
            )
            
            return send_file(
                watermarked_path,
                as_attachment=True,
                download_name=os.path.basename(watermarked_path)
            )
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(watermarked_path):
                os.remove(watermarked_path)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理失败: {str(e)}'
        })

@app.route('/api/verify_watermark', methods=['POST'])
def verify_watermark():
    try:
        # 验证文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未找到文件'})
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'message': '未选择文件'})
        
        # 验证文件类型
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in WATERMARK_HANDLERS:
            return jsonify({'success': False, 'message': '不支持的文件类型'})
        
        # 验证密码
        password = request.form.get('password')
        if not password:
            return jsonify({'success': False, 'message': '未提供密码'})
        
        # 保存上传的文件
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(temp_path)
        
        try:
            # 验证水印
            handler = WATERMARK_HANDLERS[ext]
            success, result = handler.verify_watermark(temp_path, password)
            
            if success:
                return jsonify({
                    'success': True,
                    'watermark': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result
                })
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'验证失败: {str(e)}'
        })

# 错误处理
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'success': False,
        'message': '文件大小超过限制'
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        'success': False,
        'message': '服务器内部错误'
    }), 500

@app.route('/decrypt_file', methods=['POST'])
def decrypt_file():
    if 'file' not in request.files:
        return jsonify({'result': [{'error': "未找到文件"}], 'action': '错误'})
    
    files = request.files.getlist('file')  # 获取所有文件
    
    if not files or files[0].filename == '':
        return jsonify({'result': [{'error': "未选择文件"}], 'action': '错误'})
    
    results = []
    for file in files:
        filename = file.filename
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            # 保存上传的文件
            file.save(input_path)
            
            # 获取文件类型并处理
            ext = os.path.splitext(filename)[1].lower()
            if ext in WATERMARK_HANDLERS:
                try:
                    # 提取水印
                    handler = WATERMARK_HANDLERS[ext]
                    hidden_info = handler.extract_watermark(input_path)
                    
                    if hidden_info:
                        results.append({
                            'filename': filename,
                            'content': hidden_info
                        })
                    else:
                        results.append({'error': f"{filename}: 未找到隐藏信息"})
                    
                except Exception as e:
                    results.append({'error': f"{filename}: 处理失败 - {str(e)}"})
            else:
                results.append({'error': f"{filename}: 不支持的文件类型"})
            
        except Exception as e:
            results.append({'error': f"{filename}: {str(e)}"})
        finally:
            # 清理临时文件
            if os.path.exists(input_path):
                os.remove(input_path)
    
    if not results:
        return jsonify({'result': [{'error': "处理失败"}], 'action': '错误'})
    
    # 格式化结果
    formatted_results = []
    for result in results:
        if 'error' in result:
            formatted_results.append(result)
        else:
            formatted_results.append({
                'filename': result['filename'],
                'content': {
                    'content': result['content'].get('content', ''),
                    'user': result['content'].get('user', '')
                }
            })
    
    return jsonify({
        'result': formatted_results,
        'action': '处理完成'
    })

if __name__ == '__main__':
    app.run(debug=True) 