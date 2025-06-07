#!/usr/bin/env python3
# task_processor.py
# -*- coding: utf-8 -*-
"""
Functions for handling
"""

import asyncio
import logging
from threading import Thread, Event
from typing import Any, Dict, List, Optional, Tuple
import os

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
    OpenAITTSEngine,
    KokoroTTSEngine,
    ChatterboxEngine,
)
from TTS.tts_functions import PodcastGenerator
from utils.env import setup_env
from utils.history_handler import add_to_history, check_history
from utils.task_file_handler import (
    clear_tasks,
    get_tasks,
    update_task_status,
    update_task_progress,
    save_tasks,
)
from utils.text_extraction import extract_text
from utils.common_enums import TaskStatus, InputType, TaskType

output_dir, task_file, img_pth, sources_file = setup_env()


def create_progress_callback(task_id: str):
    """Create a progress callback function for a specific task."""
    async def progress_callback(progress: int):
        await update_task_progress(task_id, progress)
    return progress_callback


def process_tasks(stop_event: Event) -> None:
    """
    Continuously fetches tasks from a queue, processes them accordingly,
    and marks them as completed. This function runs in its own event loop
    within a separate thread.

    :param stop_event: A threading.Event object used to signal when to stop the loop.
    """

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def process() -> None:
        """
        Inner async function that contains the main loop for:
        1) Pulling tasks from the queue.
        2) Checking task validity.
        3) Processing tasks (text/audio/podcast generation).
        4) Marking tasks as completed.
        5) Sleeping briefly before the next iteration.
        """
        while not stop_event.is_set():
            tasks: List[Dict[str, Any]] = await get_tasks()
            # if tasks:
            #     logging.info(f"Tasks retrieved: {tasks}")

            completed_task_ids = []  # Track successfully completed tasks
            failed_task_ids = []  # Track failed tasks

            for task in tasks:
                task_id: Optional[str] = task.get("id")
                # Convert string to enum for input_type
                input_type_str: Optional[str] = task.get("type")
                input_type = InputType(input_type_str) if input_type_str else None

                content: Optional[str] = task.get("content")
                tts_engine_name: Optional[str] = task.get("tts_engine")

                # Convert string to enum for task_type
                task_type_str: Optional[str] = task.get("task")
                task_type = TaskType(task_type_str) if task_type_str else None

                status: Optional[str] = task.get("status")

                if not all([task_id, input_type, content, tts_engine_name, task_type]):
                    logging.error(f"Invalid task format: {task}")
                    continue

                if status != TaskStatus.PENDING.value:  # Compare with enum value
                    continue
                await update_task_status(task_id, TaskStatus.PROCESSING)
                # Check if the URL has been processed before
                if input_type == InputType.URL and await check_history(content):
                    logging.info(f"URL {content} has already been processed. Skipping.")
                    continue

                try:
                    # Initialize TTS engine
                    if tts_engine_name == "openai":
                        tts_engine = OpenAITTSEngine()
                    elif tts_engine_name == "edge":
                        tts_engine = EdgeTTSEngine()
                    elif tts_engine_name == "chatterbox":
                        tts_engine = ChatterboxEngine(voice_dir="TTS/voices")
                    else:
                        tts_engine = KokoroTTSEngine()

                    # URL with full article TTS
                    if input_type == InputType.URL and task_type == TaskType.FULL:
                        new_article = ArticleData(url=content)
                        article_id: int = create_article(new_article)
                        text, title, tl_dr = await extract_text(content, article_id)
                        if not text or len(text.strip()) == 0:
                            logging.error(f"Text extraction failed for URL: {content}")
                            await update_task_status(task_id, TaskStatus.FAILED)
                            continue
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            # Create progress callback for ChatterboxEngine
                            if tts_engine_name == "chatterbox":
                                progress_cb = create_progress_callback(task_id)
                                audio, vtt_file = await tts_engine.generate_audio(
                                    text, voice, progress_callback=progress_cb
                                )
                            else:
                                audio, vtt_file = await tts_engine.generate_audio(
                                    text, voice
                                )
                            audio = await tts_engine.export_audio(
                                audio, text, title, vtt_file, audio_type="url/full"
                            )
                            updated_article = ArticleData(audio_file=audio)
                            update_article(article_id, updated_article)
                        except Exception as e:
                            logging.error(
                                f"Error creating audio for URL {content}: {e}"
                            )
                        await update_task_status(task_id, TaskStatus.COMPLETED)
                        await add_to_history(content)

                    # Text to audio (full)
                    elif input_type == InputType.TEXT and task_type == TaskType.FULL:
                        title: str = generate_title(content)
                        new_text = TextData(title=title, text=content)
                        text_id: int = create_text(new_text)
                        print(f"text {text_id} added to database")

                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            print(f"using voice: {voice}")
                            # Create progress callback for ChatterboxEngine
                            if tts_engine_name == "chatterbox":
                                progress_cb = create_progress_callback(task_id)
                                audio, vtt_file = await tts_engine.generate_audio(
                                    content, voice, progress_callback=progress_cb
                                )
                            else:
                                audio, vtt_file = await tts_engine.generate_audio(
                                    content, voice
                                )
                            await tts_engine.export_audio(
                                audio,
                                content,
                                title,
                                vtt_file,
                                audio_type="text/full",
                                text_id=text_id,
                            )
                        except Exception as e:
                            logging.error(f"Error creating audio for text: {e}")

                        await update_task_status(task_id, TaskStatus.COMPLETED)
                    # Text to podcast script generation
                    elif input_type == InputType.TEXT and task_type == TaskType.PODCAST:
                        new_text = TextData(text=content)
                        text_id: int = create_text(new_text)
                        print(f"text {text_id} added to database")

                        try:
                            script, generated_title = podcast(content)
                            logging.info("Generating podcast script from seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text: {content}"
                                )
                                continue
                            logging.info(script)
                            new_podcast = PodcastData(
                                text=script, title=generated_title
                            )
                            podcast_id: int = create_podcast_db_entry(new_podcast)
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
                                script, generated_title, podcast_id=podcast_id
                            )
                        except Exception as e:
                            logging.error(f"Error creating podcast audio for text: {e}")

                        await update_task_status(task_id, TaskStatus.COMPLETED)

                    # URL TTS summary (TL;DR)
                    elif input_type == InputType.URL and task_type == TaskType.TLDR:
                        new_article = ArticleData(url=content)
                        article_id = create_article(new_article)
                        text, title, tl_dr = await extract_text(content, article_id)

                        if not text or len(text.strip()) == 0:
                            logging.error(f"Text extraction failed for URL: {content}")
                            continue

                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            if voice is None:
                                logging.error("Failed to pick voice")
                                continue
                            # Create progress callback for ChatterboxEngine
                            if tts_engine_name == "chatterbox":
                                progress_cb = create_progress_callback(task_id)
                                audio, _ = await tts_engine.generate_audio(tl_dr, voice, progress_callback=progress_cb)
                            else:
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
                        await update_task_status(task_id, TaskStatus.COMPLETED)
                        await add_to_history(content)

                    # Text TTS summary (TL;DR)
                    elif input_type == InputType.TEXT and task_type == TaskType.TLDR:
                        title: str = generate_title(content)
                        text_tldr: str = tldr(content)
                        new_text = TextData(text=content, title=title, tl_dr=text_tldr)
                        text_id = create_text(new_text)
                        print(f"text {text_id} added to database")

                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            # Create progress callback for ChatterboxEngine
                            if tts_engine_name == "chatterbox":
                                progress_cb = create_progress_callback(task_id)
                                audio, vtt_file = await tts_engine.generate_audio(
                                    text_tldr, voice, progress_callback=progress_cb
                                )
                            else:
                                audio, vtt_file = await tts_engine.generate_audio(
                                    text_tldr, voice
                                )
                            await tts_engine.export_audio(
                                audio,
                                text_tldr,
                                title,
                                vtt_file,
                                audio_type="text/tldr",
                                text_id=text_id,
                            )
                        except Exception as e:
                            logging.error(f"Error creating audio for text/summary: {e}")

                        await update_task_status(task_id, TaskStatus.COMPLETED)

                    # URL to Podcast
                    elif task_type == "podcast":
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
                            script, generated_title = podcast(text)
                            logging.info("Generating podcast script from seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Podcast script generation failed for text from URL: {content}"
                                )
                                continue
                            logging.info(script)
                            new_podcast = PodcastData(
                                text=script, title=generated_title
                            )
                            podcast_id: int = create_podcast_db_entry(new_podcast)
                        except Exception as e:
                            logging.error(
                                f"Error generating podcast script for URL {content}: {e}"
                            )
                            continue

                        # Create the podcast audio
                        try:
                            podcast_gen = PodcastGenerator(tts_engine)
                            await podcast_gen.create_podcast_audio(
                                script, generated_title, podcast_id=podcast_id
                            )
                            logging.info("Generating podcast audio")
                        except Exception as e:
                            logging.error(
                                f"Error creating podcast audio for URL {content}: {e}"
                            )
                            continue

                        await update_task_status(task_id, TaskStatus.COMPLETED)
                        await add_to_history(content)

                    # Story from URL or Text
                    elif task_type == TaskType.STORY:
                        if input_type == InputType.URL:
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
                        elif input_type == "text":
                            text = content

                        # Generate the story script
                        try:
                            script: str = story(content)
                            logging.info("Generating story text from seed text")
                            if not script or len(script.strip()) == 0:
                                logging.error(
                                    f"Story generation failed for text: {content}"
                                )
                                continue
                        except Exception as e:
                            logging.error(
                                f"Error generating story text for: {content}, {e}"
                            )
                            continue

                        # Create audio for the generated story
                        try:
                            voices = await tts_engine.get_available_voices()
                            voice = await tts_engine.pick_random_voice(voices)
                            # Create progress callback for ChatterboxEngine
                            if tts_engine_name == "chatterbox":
                                progress_cb = create_progress_callback(task_id)
                                audio, vtt_file = await tts_engine.generate_audio(
                                    script, voice, progress_callback=progress_cb
                                )
                            else:
                                audio, vtt_file = await tts_engine.generate_audio(
                                    script, voice
                                )
                            await tts_engine.export_audio(
                                audio, script, audio_type="story"
                            )
                        except Exception as e:
                            logging.error(f"Error creating story audio: {e}")
                            continue
                        await update_task_status(task_id, TaskStatus.COMPLETED)
                        await add_to_history(content)
                    else:
                        logging.error(f"Unknown task type: {input_type}")

                    # If we reach here without exceptions, add to completed tasks
                    completed_task_ids.append(task_id)
                    await update_task_status(task_id, TaskStatus.COMPLETED)

                except Exception as e:
                    logging.error(f"Unhandled exception processing task {task}: {e}")
                    failed_task_ids.append(task_id)
                    await update_task_status(task_id, TaskStatus.FAILED)

            # Update tasks file to remove only completed tasks
            if completed_task_ids or failed_task_ids:
                remaining_tasks = [
                    task
                    for task in tasks
                    if task.get("id") not in completed_task_ids
                    and task.get("id") not in failed_task_ids
                ]
                await save_tasks(remaining_tasks)

            await asyncio.sleep(5)

    loop.run_until_complete(process())


def start_task_processor(stop_event: Event) -> Thread:
    """
    Starts the background thread that processes tasks.

    :param stop_event: A threading.Event object used to stop the background thread.
    :return: The Thread object that is running the task processing.
    """
    thread = Thread(target=process_tasks, args=(stop_event,))
    thread.daemon = True
    thread.start()
    return thread
