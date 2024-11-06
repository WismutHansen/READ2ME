#!/bin/bash

INPUT_DIR="/Users/tommyfalkowski/Code/READ2ME/TTS/voices"
OUTPUT_DIR="/Users/tommyfalkowski/Code/READ2ME/TTS/voices_converted"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.wav; do
  filename=$(basename "$file")
  ffmpeg -y -i "$file" -acodec pcm_s16le -ac 1 -ar 24000 "$OUTPUT_DIR/$filename"
done
