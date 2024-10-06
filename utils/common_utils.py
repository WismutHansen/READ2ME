import os
import re
import datetime
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TRCK, APIC
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import logging
from num2words import num2words


def write_markdown_file(md_file_path, text, url=None):
    with open(md_file_path, "w", encoding="utf-8") as md_file_handle:
        md_file_handle.write(text)
        if url:
            md_file_handle.write(f"\n\nSource: {url}")


def read_markdown_file(md_file_path):
    try:
        with open(md_file_path, "r", encoding="utf-8") as md_file_handle:
            return md_file_handle.read()
    except FileNotFoundError:
        print(f"Error: {md_file_path} not found.")
        return None


def shorten_title(title):
    # Shorten the title to 8 words max
    words = title.split()
    short_title = "_".join(words[:8])
    # Replace spaces with underscores and remove special characters not allowed in filenames
    short_title = re.sub(r"[^a-zA-Z0-9_]", "", short_title)
    return short_title


def shorten_text(text):
    words = text.split()
    if len(words) > 400:
        short_text = " ".join(words[:400])
    else:
        short_text = text
    return short_text


def split_text(text, max_words=1500):
    def count_words(text):
        return len(re.findall(r"\w+", text))

    def split_into_paragraphs(text):
        return text.split("\n\n")

    def split_into_sentences(text):
        return re.split(r"(?<=[.!?]) +", text)

    words = count_words(text)
    logging.debug(f"Total number of words in text: {words}")

    if words <= max_words:
        return [text]

    paragraphs = split_into_paragraphs(text)
    chunks = []
    current_chunk = ""
    current_word_count = 0

    for paragraph in paragraphs:
        paragraph_word_count = count_words(paragraph)
        logging.debug(f"Paragraph word count: {paragraph_word_count}")

        if current_word_count + paragraph_word_count <= max_words:
            current_chunk += paragraph + "\n\n"
            current_word_count += paragraph_word_count
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if paragraph_word_count > max_words:
                sentences = split_into_sentences(paragraph)
                for sentence in sentences:
                    sentence_word_count = count_words(sentence)
                    logging.debug(f"Sentence word count: {sentence_word_count}")

                    if current_word_count + sentence_word_count <= max_words:
                        current_chunk += sentence + " "
                        current_word_count += sentence_word_count
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
                        current_word_count = sentence_word_count
            else:
                current_chunk = paragraph + "\n\n"
                current_word_count = paragraph_word_count
            current_chunk = ""
            current_word_count = 0

    if current_chunk:
        chunks.append(current_chunk.strip())

    logging.debug(f"Number of chunks created: {len(chunks)}")
    return chunks


def strip_markdown(text):
    # Removes special characters from the input text

    disallowed_chars = '"<>[]{}|\\~`^*!#$()_;'
    symbol_text_pairs = [
        (" & ", " and "),
        (" % ", " percent "),
        (" @ ", " at "),
        (" = ", " equals "),
        (" + ", " plus "),
        (" / ", " slash "),
        (" $ ", " dollar "),
        (" € ", " euro "),
        (" £ ", " pound "),
        (" ¥ ", " yen "),
        (" ¢ ", " cent "),
        (" ® ", "registered trade mark "),
        (" © ", " copyright "),
    ]

    # Remove special characters
    cleaned_text = "".join(filter(lambda x: x not in disallowed_chars, text))

    # Replace symbols with their text equivalents
    for symbol, text_equivalent in symbol_text_pairs:
        cleaned_text = cleaned_text.replace(symbol, text_equivalent)

    # Remove brackets containing only numbers
    cleaned_text = re.sub(r"\[\d+\]", "", cleaned_text)

    # Remove instances where a number is directly after a word or a name
    cleaned_text = re.sub(r"(\b\w+\b)\d+", r"\1", cleaned_text)

    # Remove instances of more than two hyphens
    cleaned_text = re.sub(r"-{2,}", "", cleaned_text)

    return cleaned_text


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
        existing_files = [
            f for f in os.listdir(subfolder) if f.startswith(f"{file_number:03d}_")
        ]
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


def get_mp3_duration(file_path):
    audio = MP3(file_path)
    return audio.info.length


def estimate_word_duration(word):
    # Convert numbers to words for better duration estimation
    if word.isdigit():
        word = num2words(int(word))

    # Count syllables (this is a simple approximation)
    syllables = len(re.findall(r"[aeiou]", word.lower())) + 1

    # Estimate duration based on syllables (adjust these values as needed)
    base_duration = 0.2  # seconds
    syllable_duration = 0.06  # seconds per syllable

    return base_duration + (syllables * syllable_duration)


def is_end_of_sentence(word):
    return word.endswith((".", "!", "?"))


def generate_word_timestamps(duration, text):
    words = text.split()
    estimated_durations = [estimate_word_duration(word) for word in words]

    # Add pause durations
    word_pause = 0.2  # seconds
    sentence_pause = 1.5  # seconds
    pause_durations = [
        sentence_pause if is_end_of_sentence(word) else word_pause for word in words
    ]

    # Calculate total estimated duration including pauses
    total_estimated_duration = sum(estimated_durations) + sum(pause_durations)

    # Scale factor to match actual audio duration
    scale_factor = duration / total_estimated_duration

    timestamps = []
    current_time = 0.0

    for word, est_duration, pause in zip(words, estimated_durations, pause_durations):
        word_duration = est_duration * scale_factor
        pause_duration = pause * scale_factor
        start_time = current_time
        end_time = start_time + word_duration
        timestamps.append((word, start_time, end_time))
        current_time = end_time + pause_duration

    return timestamps


def save_subtitles(timestamps, output_file):
    with open(output_file, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")
        for i, (word, start, end) in enumerate(timestamps, 1):
            file.write(f"{i}\n")
            file.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            file.write(f"{word}\n\n")


def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def create_subtitle_test_html(mp3_file, vtt_file, output_html):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Subtitle Test</title>
        <style>
            .subtitle-container {{
                width: 100%;
                min-height: 50px;
                border: 1px solid #ccc;
                padding: 10px;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <audio controls>
            <source src="{mp3_file}" type="audio/mpeg">
            <track kind="subtitles" src="{vtt_file}" default>
        </audio>
        <div class="subtitle-container" id="subtitle-display"></div>

        <script>
            const audio = document.querySelector('audio');
            const track = audio.textTracks[0];
            const subtitleDisplay = document.getElementById('subtitle-display');

            track.mode = 'hidden';
            track.addEventListener('cuechange', () => {{
                if (track.activeCues.length > 0) {{
                    subtitleDisplay.textContent = track.activeCues[0].text;
                }} else {{
                    subtitleDisplay.textContent = '';
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Test HTML created at: {output_html}")


def generate_vtt_for_directory(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".mp3"):
                mp3_path = os.path.join(root, file)
                md_path = os.path.splitext(mp3_path)[0] + ".md"
                vtt_path = os.path.splitext(mp3_path)[0] + ".vtt"
                html_path = os.path.splitext(mp3_path)[0] + ".html"

                if os.path.exists(md_path) and not os.path.exists(vtt_path):
                    print(f"Generating VTT for: {mp3_path}")

                    # Get MP3 duration
                    duration = get_mp3_duration(mp3_path)

                    # Read text from MD file
                    with open(md_path, "r", encoding="utf-8") as md_file:
                        text = md_file.read()

                    # Generate timestamps
                    timestamps = generate_word_timestamps(duration, text)

                    # Save VTT file
                    save_subtitles(timestamps, vtt_path)

                    # Create test HTML
                    create_subtitle_test_html(
                        os.path.basename(mp3_path),
                        os.path.basename(vtt_path),
                        html_path,
                    )

                    print(f"VTT file created: {vtt_path}")
                    print(f"Test HTML created: {html_path}")


if __name__ == "__main__":
    output_dir = input("Enter the output directory: ")
    generate_vtt_for_directory(output_dir)

