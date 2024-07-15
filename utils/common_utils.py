import os
import re
import datetime
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TRCK, APIC
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment

def shorten_title(title):
    # Shorten the title to 8 words max
    words = title.split()
    short_title = "_".join(words[:8])
    # Replace spaces with underscores and remove special characters not allowed in filenames
    short_title = re.sub(r'[^a-zA-Z0-9_]', '', short_title)
    return short_title

def shorten_text(text):
    words = text.split()
    if len(words) > 400:
        short_text = ' '.join(words[:400])
    else:
        short_text = text
    return short_text


def get_date_subfolder(output_dir):
    current_date = datetime.date.today().strftime("%Y%m%d")
    subfolder = os.path.join(output_dir, current_date)
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
    return subfolder


async def get_output_files(output_dir, title):
    subfolder = get_date_subfolder(output_dir)
    short_title = shorten_title(title)
    file_number = 1
    while True:
        base_file_name = f"{subfolder}/{file_number:03d}_{short_title}"
        mp3_file_name = f"{base_file_name}.mp3"
        md_file_name = f"{base_file_name}.md"
        
        # Check if any files start with the same three-digit number
        existing_files = [f for f in os.listdir(subfolder) if f.startswith(f"{file_number:03d}_")]
        if not existing_files:
            return base_file_name, mp3_file_name, md_file_name
        file_number += 1


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


def add_mp3_tags(mp3_file: str, title: str, img_pth: str, output_dir: str):
    track_number = os.path.basename(mp3_file).split("_")[-1].split(".")[0]
    try:
        audio = ID3(mp3_file)
    except Exception:
        audio = ID3()
    if title:
        audio.add(TIT2(encoding=3, text=title))
    audio.add(
        TALB(encoding=3, text=f"READ2ME{datetime.date.today().strftime('%Y%m%d')}")
    )
    audio.add(TPE1(encoding=3, text="READ2ME"))
    audio.add(TCON(encoding=3, text="Spoken Audio"))
    audio.add(TRCK(encoding=3, text=str(track_number)))
    date_text = datetime.date.today().strftime("%Y-%m-%d")
    image_path = img_pth
    output_image_path = os.path.join(get_date_subfolder(output_dir), "cover.jpg")
    create_image_with_date(image_path, output_image_path, date_text)
    with open(output_image_path, "rb") as img_file:
        audio.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=img_file.read(),
            )
        )
    audio.save(mp3_file)


def convert_wav_to_mp3(wav_file: str, mp3_file: str, bitrate: str = "192k"):
    # Load WAV file
    audio = AudioSegment.from_wav(wav_file)
    
    # Export as MP3 with specified bitrate and other parameters to maintain quality
    audio.export(mp3_file, format="mp3", bitrate=bitrate, parameters=["-q:a", "0"])
    
    # Remove the original WAV file
    os.remove(wav_file)
