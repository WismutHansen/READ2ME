import asyncio
import logging
from threading import Event, Thread

from requests.api import get

from database.crud import create_podcast_db_entry, create_text, create_article
import database.state
from llm.LLM_calls import podcast, story, generate_title, tldr
from TTS.tts_engines import EdgeTTSEngine, F5TTSEngine
from TTS.tts_functions import PodcastGenerator
from utils.env import setup_env
from utils.history_handler import add_to_history, check_history
from utils.podcast.castify import create_podcast_audio
from utils.synthesize import read_text
from utils.synthesize import synthesize_text_to_speech as synthesize_edge_tts
from utils.task_file_handler import clear_tasks, get_tasks
from utils.text_extraction import extract_text

output_dir, task_file, img_pth, sources_file = setup_env()


def process_tasks(stop_event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def process():
        while not stop_event.is_set():
            tasks = await get_tasks()
            if tasks:
                logging.info(f"Tasks retrieved: {tasks}")

            for task in tasks:
                task_type = task.get("type")
                content = task.get("content")
                tts_engine = task.get("tts_engine")
                task = task.get("task")

                if not all([task_type, content, tts_engine]):
                    logging.error(f"Invalid task format: {task}")
                    continue

                # Check if the URL has been processed before
                if task_type == "url" and await check_history(content):
                    logging.info(f"URL {content} has already been processed. Skipping.")
                    continue

                try:
                    if task_type == "url" and (task is None or task == "full"):
                        # URL to audio processing
                        if tts_engine == "styletts2":
                            from utils.synthesize_styletts2 import say_with_styletts2

                            await say_with_styletts2(content, output_dir, img_pth)
                        elif tts_engine == "piper":
                            from utils.synthesize_piper import url_with_piper

                            await url_with_piper(content, output_dir, img_pth)
                        elif tts_engine == "F5":
                            text, title = await extract_text(content)
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                voices = await f5_tts.get_available_voices()
                                voice = await f5_tts.pick_random_voice(voices)
                                audio, _ = await f5_tts.generate_audio(text, voice)
                                await f5_tts.export_audio(audio, text, title)
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for URL {content}: {e}"
                                )
                        else:
                            text, title = await extract_text(content)
                            try:
                                edge_tts = EdgeTTSEngine()
                                voices = await edge_tts.get_available_voices()
                                voice = await edge_tts.pick_random_voice(voices)
                                audio, vtt_file = await edge_tts.generate_audio(
                                    text, voice
                                )
                                await edge_tts.export_audio(
                                    audio, text, title, vtt_file
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for URL {content}: {e}"
                                )
                        await add_to_history(
                            content
                        )  # Add URL to history after processing

                    elif task_type == "text" and (task is None or task == "full"):
                        # Text to audio processing
                        title = generate_title(content)
                        current_text = database.state.get_current_text()
                        if current_text:
                            current_text.text = content
                            current_text.title = title
                            create_text(current_text)
                        if tts_engine == "styletts2":
                            from utils.synthesize_styletts2 import (
                                text_to_speech_with_styletts2,
                            )

                            await text_to_speech_with_styletts2(
                                content, title, output_dir, img_pth
                            )
                        elif tts_engine == "F5":
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                voices = await f5_tts.get_available_voices()
                                voice = await f5_tts.pick_random_voice(voices)
                                audio, _ = await f5_tts.generate_audio(content, voice)
                                await f5_tts.export_audio(audio, content, title)
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for URL {content}: {e}"
                                )
                        elif tts_engine == "piper":
                            from utils.synthesize_piper import read_text_piper

                            await read_text_piper(content, output_dir, img_pth, title)
                        else:
                            try:
                                edge_tts = EdgeTTSEngine()
                                voices = await edge_tts.get_available_voices()
                                voice = await edge_tts.pick_random_voice(voices)
                                audio, vtt_file = await edge_tts.generate_audio(
                                    content, voice
                                )
                                await edge_tts.export_audio(
                                    audio, content, title, vtt_file
                                )
                            except Exception as e:
                                logging.error(f"Error creating audio for text: {e}")
                    elif task_type == "text" and task == "podcast":
                        # Podcast creation processing
                        # Generate the podcast script
                        try:
                            script = podcast(content)
                            logging.info("Generating podcast script form seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text from URL: {content}"
                                )
                                continue
                            logging.info(script)
                        except Exception as e:
                            logging.error(
                                f"Error generating podcast script for URL {content}: {e}"
                            )
                            continue
                        title = generate_title(script)
                        # Create the podcast audio
                        if tts_engine == "edge":
                            try:
                                edge_tts = EdgeTTSEngine()
                                podcast_gen = PodcastGenerator(edge_tts)
                                audio_file = await podcast_gen.create_podcast_audio(
                                    script
                                )
                                logging.info("Generating podcast audio")
                            except Exception as e:
                                logging.error(
                                    f"Error creating podcast audio for URL {content}: {e}"
                                )
                                continue
                        elif tts_engine == "F5":
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                podcast_gen = PodcastGenerator(f5_tts)
                                audio_file = await podcast_gen.create_podcast_audio(
                                    script
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating podcast audio for URL {content}: {e}"
                                )
                    elif task_type == "url" and task == "tldr":
                        text, title = await extract_text(content)
                        tl_dr = tldr(text)
                        # URL to audio processing
                        if tts_engine == "styletts2":
                            from utils.synthesize_styletts2 import (
                                text_to_speech_with_styletts2,
                            )

                            await text_to_speech_with_styletts2(
                                tl_dr, title, output_dir, img_pth
                            )
                        elif tts_engine == "piper":
                            from utils.synthesize_piper import read_text_piper

                            await read_text_piper(tl_dr, output_dir, img_pth)
                        elif tts_engine == "F5":
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                voices = await f5_tts.get_available_voices()
                                voice = await f5_tts.pick_random_voice(voices)
                                audio, _ = await f5_tts.generate_audio(tl_dr, voice)
                                await f5_tts.export_audio(audio, tl_dr, title)
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for URL {content}: {e}"
                                )
                        else:
                            try:
                                edge_tts = EdgeTTSEngine()
                                voices = await edge_tts.get_available_voices()
                                voice = await edge_tts.pick_random_voice(voices)
                                audio, vtt_file = await edge_tts.generate_audio(
                                    tl_dr, voice
                                )
                                await edge_tts.export_audio(
                                    audio, tl_dr, title, vtt_file
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for URL/summary: {e}"
                                )
                        await add_to_history(
                            content
                        )  # Add URL to history after processing
                        pass
                    elif task_type == "text" and task == "tldr":
                        # Text to audio processing
                        title = generate_title(content)
                        tl_dr = tldr(content)

                        if tts_engine == "edge":
                            try:
                                edge_tts = EdgeTTSEngine()
                                voices = await edge_tts.get_available_voices()
                                voice = await edge_tts.pick_random_voice(voices)
                                audio, vtt_file = await edge_tts.generate_audio(
                                    tl_dr, voice
                                )
                                await edge_tts.export_audio(
                                    audio, tl_dr, title, vtt_file
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for text/summary: {e}"
                                )

                        elif tts_engine == "F5":
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                voices = await f5_tts.get_available_voices()
                                voice = await f5_tts.pick_random_voice(voices)
                                audio, _ = await f5_tts.generate_audio(tl_dr, voice)
                                await f5_tts.export_audio(audio, tl_dr, title)
                            except Exception as e:
                                logging.error(
                                    f"Error creating audio for text/summary: {e}"
                                )

                        current_text = database.state.get_current_text()
                        if current_text:
                            current_text.text = content
                            current_text.title = title
                            current_text.tl_dr = tl_dr
                            create_text(current_text)
                            logging.info("text/summary added to database")

                    elif task_type == "podcast":
                        # Podcast creation processing
                        # Extract the text from the URL
                        try:
                            text, title = await extract_text(content)
                            if not text or len(text.strip()) == 0:
                                logging.error(
                                    f"Text extraction failed for URL: {content}"
                                )
                                continue
                        except Exception as e:
                            logging.error(
                                f"Error extracting text from URL {content}: {e}"
                            )
                            continue

                        # Generate the podcast script
                        try:
                            script = podcast(text)
                            logging.info("Generating podcast script form seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text from URL: {content}"
                                )
                                continue
                            logging.info(script)
                        except Exception as e:
                            logging.error(
                                f"Error generating podcast script for URL {content}: {e}"
                            )
                            continue

                        # Create the podcast audio
                        if tts_engine == "edge":
                            try:
                                edge_tts = EdgeTTSEngine()
                                podcast_gen = PodcastGenerator(edge_tts)
                                audio_file = await podcast_gen.create_podcast_audio(
                                    script
                                )
                                logging.info("Generating podcast audio")
                            except Exception as e:
                                logging.error(
                                    f"Error creating podcast audio for URL {content}: {e}"
                                )
                                continue
                        elif tts_engine == "F5":
                            try:
                                f5_tts = F5TTSEngine("utils/voices/")
                                podcast_gen = PodcastGenerator(f5_tts)
                                audio_file = await podcast_gen.create_podcast_audio(
                                    script
                                )
                            except Exception as e:
                                logging.error(
                                    f"Error creating podcast audio for URL {content}: {e}"
                                )
                    elif task_type == "story":
                        # Extract the text from the URL
                        try:
                            text, title = await extract_text(content)
                            if not text or len(text.strip()) == 0:
                                logging.error(
                                    f"Text extraction failed for URL: {content}"
                                )
                                continue
                        except Exception as e:
                            logging.error(
                                f"Error extracting text from URL {content}: {e}"
                            )
                            continue

                        # Generate the podcast script
                        try:
                            script = story(text, "Spanish")
                            logging.info("Generating story text from seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast story generation failed for text from URL: {content}"
                                )
                                continue
                        except Exception as e:
                            logging.error(
                                f"Error generating story text for URL {content}: {e}"
                            )
                            continue

                        # Create the podcast audio
                        try:
                            await read_text(script, output_dir, img_pth)
                            logging.info("Generating story audio")
                        except Exception as e:
                            logging.error(
                                f"Error creating story audio for URL {content}: {e}"
                            )
                            continue
                    else:
                        logging.error(f"Unknown task type: {task_type}")

                except Exception as e:
                    logging.error(f"Unhandled exception processing task {task}: {e}")

            if tasks:
                await clear_tasks()
            await asyncio.sleep(5)

    loop.run_until_complete(process())


def start_task_processor(stop_event):
    thread = Thread(target=process_tasks, args=(stop_event,))
    thread.daemon = True
    thread.start()
    return thread
