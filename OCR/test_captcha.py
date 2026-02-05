import ddddocr
import os
from PIL import Image

# 修复 Pillow 兼容性问题
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# 初始化识别器 (只需初始化一次)
ocr = ddddocr.DdddOcr()

def test_local_images():
    # 获取当前文件夹下的所有文件
    files = os.listdir('.')
    
    print(f"{'图片文件名':<20} | {'识别结果':<10}")
    print("-" * 35)

    count = 0
    
    for filename in files:
        # 只处理 jpg 和 png 图片
        if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
            try:
                # 以二进制模式打开图片
                with open(filename, 'rb') as f:
                    img_bytes = f.read()
                
                # 开始识别
                res = ocr.classification(img_bytes)
                
                # 打印结果
                print(f"{filename:<20} | {res:<10}")
                count += 1
                
            except Exception as e:
                print(f"{filename:<20} | ❌ 出错: {e}")

    if count == 0:
        print("⚠️ 当前目录下没有找到 .jpg 或 .png 图片，请先下载几张验证码放进来。")

if __name__ == "__main__":
    print("🚀 开始测试本地验证码识别...\n")
    test_local_images()
    print("\n✅ 测试结束")