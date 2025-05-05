import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd
import matplotlib.pyplot as plt

def create_image(filename, text):
    # 创建一个简单的图片
    img = Image.new('RGB', (800, 400), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), text, fill='black')
    img.save(filename)

def create_pdf_with_image(filename, text):
    # 创建一个包含图片和文字的PDF
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, text)
    c.save()

def create_pdf_with_table(filename, data):
    # 创建一个包含表格的PDF
    df = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center')
    plt.savefig(filename)

def main():
    # 创建图片文件
    create_image('import_files/game_screenshot.jpg', '黑神话：悟空 - 游戏截图')
    create_image('import_files/character_portrait.png', '孙悟空角色立绘')

    # 创建带图片的PDF
    create_pdf_with_image('import_files/game_manual.pdf', '黑神话：悟空 - 游戏手册')

    # 创建带表格的PDF
    data = {
        '角色': ['孙悟空', '唐僧', '猪八戒', '沙僧'],
        '等级': [50, 30, 45, 40],
        '生命值': [1000, 500, 800, 700],
        '攻击力': [200, 50, 150, 120]
    }
    create_pdf_with_table('import_files/character_stats.pdf', data)

if __name__ == '__main__':
    main() 