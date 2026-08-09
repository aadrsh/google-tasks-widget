import os
from PIL import Image, ImageDraw

res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
os.makedirs(res_dir, exist_ok=True)

def create_white_plus():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([26, 12, 38, 52], fill=(255, 255, 255, 255))
    draw.rectangle([12, 26, 52, 38], fill=(255, 255, 255, 255))
    img.save(os.path.join(res_dir, 'plus.png'))

def create_white_refresh():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.arc([10, 10, 54, 54], start=45, end=315, fill=(255, 255, 255, 255), width=8)
    draw.polygon([(48, 8), (58, 22), (38, 22)], fill=(255, 255, 255, 255))
    img.save(os.path.join(res_dir, 'refresh.png'))

def create_white_edit():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Pencil shaft (pointing 45 degrees diagonally from bottom-left to top-right)
    draw.polygon([(16, 44), (20, 48), (48, 20), (44, 16)], fill=(255, 255, 255, 255))
    # Sharp pencil tip pointing down-left
    draw.polygon([(8, 56), (16, 44), (20, 48)], fill=(77, 168, 218, 255))
    # Eraser cap at top-right
    draw.polygon([(44, 16), (48, 20), (54, 14), (50, 10)], fill=(77, 168, 218, 255))
    img.save(os.path.join(res_dir, 'edit.png'))

def create_white_delete():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Trash lid
    draw.rectangle([14, 12, 50, 18], fill=(255, 255, 255, 255))
    draw.rectangle([24, 8, 40, 12], fill=(255, 255, 255, 255))
    # Trash body
    draw.polygon([(18, 22), (46, 22), (42, 56), (22, 56)], fill=(255, 255, 255, 255))
    # Inner slots
    draw.rectangle([25, 28, 28, 50], fill=(255, 107, 107, 255))
    draw.rectangle([30, 28, 33, 50], fill=(255, 107, 107, 255))
    draw.rectangle([35, 28, 38, 50], fill=(255, 107, 107, 255))
    img.save(os.path.join(res_dir, 'delete.png'))

if __name__ == '__main__':
    create_white_plus()
    create_white_refresh()
    create_white_edit()
    create_white_delete()
    print("Rotated 45-degree diagonal edit pencil generated!")
