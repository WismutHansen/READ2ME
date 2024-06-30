import os
from dotenv import load_dotenv
import logging

def setup_env():
    print("Starting setup_env()")

    task_file = "tasks.json"

    if not os.path.isfile(task_file):
        print("Creating tasks.json")
        with open(task_file, "w") as f:
            pass  # This creates an empty tasks.json file
     
    def check_env_file_exists(directory="."):
        env_file_path = os.path.join(directory, ".env")
        exists = os.path.isfile(env_file_path)
        print(f".env file exists: {exists}")
        return exists

    if check_env_file_exists():
        print("Loading .env file")
        load_dotenv()
        
        output_dir = os.getenv("OUTPUT_DIR", "Output")
        img_pth = os.getenv("IMG_PATH", "front.jpg")
        sources_file_path = os.getenv("SOURCES_FILE", "sources.txt")
        keywords_file_path = os.getenv("KEYWORDS_FILE", "keywords.txt")
        
    else:
        print(".env file not found, using default values")
        output_dir = "Output"
        img_pth = "front.jpg"
        sources_file_path = "sources.txt"
        keywords_file_path = "keywords.txt"

    if not os.path.isfile(sources_file_path):
        print("Creating sources.txt")
        with open(sources_file_path, "w") as f:
            pass  # This creates an empty sources.txt file
    
    if not os.path.isfile(keywords_file_path):
        print("Creating keywords.txt")
        with open(keywords_file_path, "w") as f:
            pass  # This creates an empty keywords.txt file

    logging.info("Setup complete, following values will be used:")
    logging.info("Output folder: "+os.path.abspath(output_dir))
    logging.info("Task file: "+os.path.abspath(task_file))
    logging.info("Album Art Image: "+os.path.abspath(img_pth))
    logging.info("Sources Textfile: "+os.path.abspath(sources_file_path))
    logging.info("Keywords Textfile: "+os.path.abspath(keywords_file_path))
    
    return output_dir, task_file, img_pth, sources_file_path, keywords_file_path


def print_env_contents():
    env_path = '.env'
    if os.path.isfile(env_path):
        print("Contents of .env file:")
        with open(env_path, 'r') as f:
            print(f.read())
    else:
        print(".env file not found")


if __name__ == "__main__":
    output_dir, task_file, img_pth, sources_file_path, keywords_file_path = setup_env()
    print_env_contents()
    print("Setup complete, following values will be used:")
    print("Output folder: "+os.path.abspath(output_dir))
    print("Task file: "+os.path.abspath(task_file))
    print("Album Art Image: "+os.path.abspath(img_pth))
    print("Sources Textfile: "+os.path.abspath(sources_file_path))
    print("Keywords Textfile: "+os.path.abspath(keywords_file_path))
