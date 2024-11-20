# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
RUN cp .env.example .env
#
# Install ffmpeg for edge_tts and cifs-utils for mounting SMB shares
RUN apt-get update && \
  apt-get install -y git ffmpeg cifs-utils espeak-ng build-essential && \
  apt-get clean
#
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_stts2.txt
RUN pip install --no-cache-dir -r requirements_F5.txt
RUN python3 -m TTS.setup_piper


# Install fonts for PIL
RUN apt-get install -y fonts-dejavu-core
RUN playwright install

# Make port 7777 available to the world outside this container
EXPOSE 7777

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7777"]
