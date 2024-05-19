# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg for edge_tts and cifs-utils for mounting SMB shares
RUN apt-get update && \
    apt-get install -y ffmpeg cifs-utils && \
    apt-get clean

# Install fonts for PIL
RUN apt-get install -y fonts-dejavu-core

# Set environment variables
ENV OUTPUT_DIR="Output"
ENV URL_FILE="urls.txt"
ENV IMG_PATH="front.jpg"

# Make port 7777 available to the world outside this container
EXPOSE 7777

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7777"]
