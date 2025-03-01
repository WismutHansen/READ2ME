#!/usr/bin/env python3
# enums.py
# -*- coding: utf-8 -*-
"""
Enumerations for fixed expressions used across the application
"""

from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InputType(str, Enum):
    URL = "url"
    TEXT = "text"
    PDF = "pdf"


class TaskType(str, Enum):
    FULL = "full"
    TLDR = "tldr"
    PODCAST = "podcast"
    STORY = "story"


class TTSEngine(str, Enum):
    EDGE = "EdgeTTSEngine"
    OPENAI = "OpenAITTSEngine"
    KOKORO = "KokoroTTSEngine"
