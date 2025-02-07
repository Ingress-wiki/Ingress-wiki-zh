import os
import re
import requests
import subprocess
from pathlib import Path
from PIL import Image
from urllib.parse import urlparse
import hashlib
from bs4 import BeautifulSoup
import markdown

def is_image_url(url):
    """检查URL是否是图片链接"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    parsed = urlparse(url)
    return any(parsed.path.lower().endswith(ext) for ext in image_extensions)

def download_image(url, save_path):
    """下载图片"""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    return False

def convert_to_webp(input_path, output_path, quality=80):
    """转换图片为WebP格式"""
    try:
        subprocess.run(['cwebp', '-q', str(quality), input_path, '-o', output_path], 
                      check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def process_markdown_file(file_path):
    """处理Markdown文件中的图片"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式查找Markdown中的图片引用
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    changes_made = False
    
    def replace_image(match):
        nonlocal changes_made
        alt_text = match.group(1)
        image_url = match.group(2)
        
        # 如果已经是相对路径引用，跳过
        if image_url.startswith('./images/'):
            return match.group(0)
        
        if not is_image_url(image_url):
            return match.group(0)
            
        # 创建images目录
        image_dir = Path(file_path).parent / 'images'
        image_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        image_filename = f"{url_hash}.webp"
        image_path = image_dir / image_filename
        
        # 下载并转换图片
        temp_path = image_path.with_suffix('.temp')
        if download_image(image_url, temp_path):
            if convert_to_webp(str(temp_path), str(image_path)):
                temp_path.unlink()  # 删除临时文件
                changes_made = True
                return f'![{alt_text}](./images/{image_filename})'
        
        if temp_path.exists():
            temp_path.unlink()
        return match.group(0)
    
    new_content = re.sub(image_pattern, replace_image, content)
    
    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

def main():
    # 获取当前PR中修改的文件
    changed_files = subprocess.check_output(['git', 'diff', '--name-only', 'origin/main'])
    changed_files = changed_files.decode().splitlines()
    
    # 处理所有修改的Markdown文件
    for file_path in changed_files:
        if file_path.endswith('.md'):
            print(f"Processing {file_path}...")
            if process_markdown_file(file_path):
                print(f"Updated images in {file_path}")

if __name__ == '__main__':
    main() 