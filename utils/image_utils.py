import os
from PIL import Image, ImageDraw, ImageFont


def create_image_with_date(image_path: str, output_path: str, date_text: str):
    if not os.path.exists(output_path):
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        font_path = "Fonts/PermanentMarker.ttf"
        font = ImageFont.truetype(font_path, 50)
        width, height = image.size
        text_bbox = draw.textbbox((0, 0), date_text, font=font)
        text_width, text_height = (
            text_bbox[2] - text_bbox[0],
            text_bbox[3] - text_bbox[1],
        )
        position = ((width - text_width) // 2, height - text_height - 35)
        draw.text(position, date_text, font=font, fill="black")
        image.save(output_path)
