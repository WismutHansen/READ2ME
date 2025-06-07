import os
import re
import sys
import subprocess
import datetime
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TRCK, APIC
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import logging
from num2words import num2words
from typing import Optional


def download_file(url, save_path):
    # Install cloudscraper library within the virtual environment
    subprocess.run([sys.executable, "-m", "pip", "install", "cloudscraper"], check=True)
    import cloudscraper

    print(f"Downloading from {url}")
    scraper = cloudscraper.create_scraper()
    with scraper.get(url, stream=True) as r:
        r.raise_for_status()
        total_length = int(r.headers.get("content-length", 0))
        dl = 0
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    dl += len(chunk)
                    f.write(chunk)
                    done = int(50 * dl / total_length)
                    print(
                        f"\r[{'=' * done}{' ' * (50 - done)}] {dl / total_length * 100:.2f}%",
                        end="",
                    )
    print("\nDownload complete.")


def preprocess_text(text: str, min_chars: int = 50) -> list:
    """
    Preprocess text to split into sentences while handling edge cases like abbreviations and domain names.
    Combines short sentences to ensure each section has at least `min_chars` characters.
    """
    # Replace " | " with "."
    text = text.replace(" | ", ". ")

    # Add a period if a sentence lacks punctuation before a newline
    text = re.sub(r"(?<![.?!])\n", ".\n", text)

    # Comprehensive list of common abbreviations
    abbreviations = {
        "U.S.",
        "U.K.",
        "e.g.",
        "i.e.",
        "etc.",
        "Dr.",
        "Mr.",
        "Mrs.",
        "Ms.",
        "Prof.",
        "Sr.",
        "Jr.",
        "Inc.",
        "Ltd.",
        "Corp.",
        "Co.",
        "St.",
        "Mt.",
        "Gov.",
        "Gen.",
        "Col.",
        "Capt.",
        "Sgt.",
        "Lt.",
        "Ave.",
        "Dept.",
        "Est.",
        "Fig.",
        "Univ.",
        "Assn.",
        "Bros.",
        "Hosp.",
        "No.",
        "Rep.",
        "Sen.",
        "Hon.",
        "Rev.",
        "Messrs.",
        "Mmes.",
        "Pres.",
        "Supt.",
        "Treas.",
        "Adm.",
        "Cmdr.",
        "Attys.",
        "Pvt.",
        "Maj.",
        "Brig.",
        "Ft.",
        "Cpl.",
        "Twp.",
        "Ph.D.",
        "M.D.",
        "D.D.S.",
        "R.N.",
    }

    # Enhanced domain pattern
    domain_pattern = re.compile(
        r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|gov|edu|io|co|uk|us|de|fr|es|ru|jp|cn|info|biz|me|tv|ly)\b"
    )

    # Tokenize text into potential sentences
    tokens = re.split(r"(?<=[.?!])\s+", text.strip())

    # Rejoin tokens where splits incorrectly occurred (e.g., after abbreviations or domains)
    sentences = []
    for token in tokens:
        if sentences and (token in abbreviations or domain_pattern.match(token)):
            sentences[-1] += f" {token}"
        else:
            sentences.append(token)

    # Combine short sentences
    combined_sentences = []
    buffer = ""

    for sentence in sentences:
        if len(buffer) + len(sentence) + 1 < min_chars:  # Add 1 for the space
            buffer += f" {sentence}" if buffer else sentence
        else:
            if buffer:
                combined_sentences.append(buffer.strip())
            buffer = sentence

    if buffer:  # Add any remaining text in the buffer
        combined_sentences.append(buffer.strip())

    # Remove empty strings and trim whitespace
    return [sentence.strip() for sentence in combined_sentences if sentence.strip()]


def sanitize_filename(filename):
    """
    Remove or replace invalid characters in filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', "", filename).strip()


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


def create_image_with_date(
    image_path: str,
    output_path: str,
    date_text: str,
    audio_type: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    """
    Creates an image with a date overlay and an optional color tint based on the audio type.

    The function loads an image from `image_path`, applies a semi-transparent color tint if a valid
    `audio_type` is provided, and then adds centered date text at the bottom of the image. The final
    image is saved to `output_path` only if the file does not already exist.

    Parameters:
        image_path (str): The file path of the input image.
        output_path (str): The file path to save the modified image.
        date_text (str): The text (typically a date) to overlay on the image.
        audio_type (Optional[str]): Type of audio content which determines the tint color. Supported values:
            - "url/full"  : Blue tint.
            - "url/tldr"  : Red tint.
            - "text/full" : Yellow tint.
            - "text/tldr" : Green tint.
            - "podcast"   : Purple tint.
            - "story"     : Pink tint.
            If None or unrecognized, no tint is applied.
        title (Optional[str]): An optional title parameter (currently not used).

    Returns:
        None
    """
    if not os.path.exists(output_path):
        image = Image.open(image_path).convert("RGBA")

        # Determine tint color based on audio_type
        if audio_type == "url/full":
            tint_color = (0, 0, 255, 128)  # Blue
        elif audio_type == "url/tldr":
            tint_color = (255, 0, 0, 128)  # Red
        elif audio_type == "text/full":
            tint_color = (255, 255, 0, 128)  # Yellow
        elif audio_type == "text/tldr":
            tint_color = (0, 255, 0, 128)  # Green
        elif audio_type == "podcast":
            tint_color = (128, 0, 128, 128)  # Purple
        elif audio_type == "story":
            tint_color = (255, 192, 203, 128)  # Pink
        else:
            tint_color = None  # No tint if type is None or unrecognized

        # Apply tint if a matching type is found
        if tint_color:
            tint_overlay = Image.new("RGBA", image.size, tint_color)
            image = Image.alpha_composite(image, tint_overlay)

        # Reinitialize drawing context after applying tint
        draw = ImageDraw.Draw(image)

        # Define font
        font_path = "Fonts/PermanentMarker.ttf"
        font = ImageFont.truetype(font_path, 50)

        # Draw date text
        width, height = image.size
        text_bbox = draw.textbbox((0, 0), date_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        position = ((width - text_width) // 2, height - text_height - 35)
        draw.text(position, date_text, font=font, fill="black")

        # Save the image
        image.convert("RGB").save(output_path)


def add_mp3_tags(
    mp3_file: str,
    title: str,
    img_pth: str,
    output_dir: str,
    audio_type: Optional[str] = None,
):
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
    output_image_path = os.path.join(
        get_date_subfolder(output_dir), title + "_cover.jpg"
    )
    create_image_with_date(image_path, output_image_path, date_text, audio_type, title)
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
