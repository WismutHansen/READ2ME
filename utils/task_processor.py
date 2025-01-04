import asyncio
from hashlib import new
import logging
from threading import Thread
from database.crud import (
    ArticleData,
    TextData,
    PodcastData,
    create_article,
    create_text,
    create_podcast_db_entry,
    update_article,
    update_text,
    update_podcast,
)
from llm.LLM_calls import podcast, story, generate_title, tldr
from TTS.tts_engines import (
    EdgeTTSEngine,
    # F5TTSEngine,
    # PiperTTSEngine,
    # StyleTTS2Engine,
    # OuteTTSEngine,
    OpenAITTSEngine,
    KokoroTTSEngine,
)
from TTS.tts_functions import PodcastGenerator
from utils.env import setup_env
from utils.history_handler import add_to_history, check_history
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
                current_task = task.get("task")

                if not all([task_type, content, tts_engine, current_task]):
                    logging.error(f"Invalid task format: {task}")
                    continue

                # Check if the URL has been processed before
                if task_type == "url" and await check_history(content):
                    logging.info(f"URL {content} has already been processed. Skipping.")
                    continue

                try:
                    if tts_engine == "openai":
                        tts_engine = OpenAITTSEngine("test")
                    # if tts_engine == "piper":
                    #     tts_engine = PiperTTSEngine("TTS/piper_tts/voices/")
                    elif tts_engine == "edge":
                        tts_engine = EdgeTTSEngine()
                    # elif tts_engine == "F5":
                    #     tts_engine = F5TTSEngine("TTS/voices/")
                    # elif tts_engine == "OuteTTS":
                    #     tts_engine = OuteTTSEngine(
                    #         voice_dir="TTS/voices/",
                    #         model_path="OuteAI/OuteTTS-0.2-500M-GGUF",
                    #         language="en",
                    #         n_gpu_layers=-1,
                    #     )
                    # else:
                    #     tts_engine = StyleTTS2Engine()
                    else:
                        tts_engine = KokoroTTSEngine("http://192.168.1.213:8880")

                    if task_type == "url" and current_task == "full":
                        new_article = ArticleData(url=content)
                        article_id = create_article(new_article)
                        text, title, tl_dr = await extract_text(content, article_id)
                        if not text or len(text.strip()) == 0:
                            logging.error(f"Text extraction failed for URL: {content}")
                            continue
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            audio, vtt_file = await tts_engine.generate_audio(
                                text, voice
                            )
                            audio = await tts_engine.export_audio(
                                audio, text, title, vtt_file, audio_type="url/full"
                            )
                            new_article = ArticleData(audio_file=audio)
                            update_article(article_id, new_article)
                        except Exception as e:
                            logging.error(
                                f"Error creating audio for URL {content}: {e}"
                            )
                        await add_to_history(
                            content
                        )  # Add URL to history after processing

                    elif task_type == "text" and current_task == "full":
                        # Text to audio processing
                        title = generate_title(content)
                        new_text = TextData(title=title, text=content)
                        id = create_text(new_text)
                        print(f"text {id} added to database")
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            print(f"using voice: {voice}")
                            audio, vtt_file = await tts_engine.generate_audio(
                                content, voice
                            )
                            await tts_engine.export_audio(
                                audio,
                                content,
                                title,
                                vtt_file,
                                audio_type="text/full",
                                text_id=id,
                            )
                        except Exception as e:
                            logging.error(f"Error creating audio for text: {e}")

                    elif task_type == "text" and current_task == "podcast":
                        # Generate the podcast script
                        new_text = TextData(text=content)
                        id = create_text(new_text)
                        print(f"text {id} added to database")
                        try:
                            script, title = podcast(content)
                            logging.info("Generating podcast script form seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text from URL: {content}"
                                )
                                continue
                            logging.info(script)
                            new_podcast = PodcastData(text=script, title=title)
                            podcast_id = create_podcast_db_entry(new_podcast)
                            logging.info(
                                f"Podcast script added to db. Podcast ID: {podcast_id}"
                            )
                        except Exception as e:
                            logging.error(
                                f"Error generating podcast script for text: {e}"
                            )
                            continue
                        try:
                            podcast_gen = PodcastGenerator(tts_engine)
                            await podcast_gen.create_podcast_audio(
                                script, title, podcast_id=podcast_id
                            )

                        except Exception as e:
                            logging.error(f"Error creating podcast audio for text: {e}")
                    elif task_type == "url" and current_task == "tldr":
                        new_article = ArticleData(url=content)
                        article_id = create_article(new_article)
                        text, title, tl_dr = await extract_text(content, article_id)
                        if text is None:
                            logging.error("Text extraction failed")
                            if not text or len(text.strip()) == 0:
                                logging.error(
                                    f"Text extraction failed for URL: {content}"
                                )
                                return
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            if voice is None:
                                logging.error("Failed to pick voice")
                                return
                            audio, _ = await tts_engine.generate_audio(tl_dr, voice)
                            await tts_engine.export_audio(
                                audio,
                                tl_dr,
                                title,
                                audio_type="url/tldr",
                                article_id=article_id,
                            )
                        except Exception as e:
                            logging.error(
                                f"Error creating audio for URL {content}: {e}"
                            )
                        await add_to_history(
                            content
                        )  # Add URL to history after processing
                        pass
                    elif task_type == "text" and current_task == "tldr":
                        # Text to audio processing
                        title = generate_title(content)
                        tl_dr = tldr(content)
                        new_text = TextData(text=content, title=title, tl_dr=tl_dr)
                        id = create_text(new_text)
                        print(f"text {id} added to database")
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            audio, vtt_file = await tts_engine.generate_audio(
                                tl_dr, voice
                            )
                            await tts_engine.export_audio(
                                audio,
                                tl_dr,
                                title,
                                vtt_file,
                                audio_type="text/tldr",
                                text_id=id,
                            )
                        except Exception as e:
                            logging.error(f"Error creating audio for text/summary: {e}")

                    elif current_task == "podcast":
                        # Podcast creation processing
                        # Extract the text from the URL
                        new_article = ArticleData(url=content)
                        article_id = create_article(new_article)
                        try:
                            text, title, tl_dr = await extract_text(content, article_id)
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
                            script, title = podcast(text)
                            logging.info("Generating podcast script form seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text from URL: {content}"
                                )
                                continue
                            logging.info(script)
                            new_podcast = PodcastData(text=script, title=title)
                            podcast_id = create_podcast_db_entry(new_podcast)
                        except Exception as e:
                            logging.error(
                                f"Error generating podcast script for URL {content}: {e}"
                            )
                            continue

                        # Create the podcast audio
                        try:
                            podcast_gen = PodcastGenerator(tts_engine)
                            audio = await podcast_gen.create_podcast_audio(
                                script, title, podcast_id=podcast_id
                            )
                            logging.info("Generating podcast audio")
                        except Exception as e:
                            logging.error(
                                f"Error creating podcast audio for URL {content}: {e}"
                            )
                            continue

                    elif current_task == "story":
                        # Extract the text from the URL
                        if task_type == "url":
                            try:
                                text, title, tl_dr = await extract_text(content)
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
                        elif task_type == "text":
                            text = content
                        # Generate the story script
                        try:
                            script = story(content)
                            logging.info("Generating story text from seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Story generation failed for text from URL: {content}"
                                )
                                continue
                        except Exception as e:
                            logging.error(
                                f"Error generating story text for URL {content}: {e}"
                            )
                            continue

                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            audio, vtt_file = await tts_engine.generate_audio(
                                script, voice
                            )
                            await tts_engine.export_audio(
                                audio, script, audio_type="story"
                            )
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
