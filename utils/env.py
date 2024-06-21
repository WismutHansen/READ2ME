import os
from dotenv import load_dotenv

def setup_env():
    def check_env_file_exists(directory="."):
        env_file_path = os.path.join(directory, ".env")
        return os.path.isfile(env_file_path)

    def check_if_files_exist(directory="."):
        sources_file_path = os.path.join(directory, "sources.txt")
        keywords_file_path = os.path.join(directory, "keywords.txt")
        return os.path.isfile(sources_file_path) and os.path.isfile(keywords_file_path)

    if check_env_file_exists():
        load_dotenv()
        output_dir = os.getenv("OUTPUT_DIR", "Output")
        task_file = os.getenv("TASK_FILE", "tasks.txt")
        img_pth = os.getenv("IMG_PATH", "front.jpg")
        sources_file_path = os.getenv("SOURCES_FILE", "sources.txt")
        keywords_file_path = os.getenv("KEYWORDS_FILE", "keywords.txt")
    else:
        output_dir = "Output"
        task_file = "tasks.txt"
        img_pth = "front.jpg"
        sources_file_path = "sources.txt"
        keywords_file_path = "keywords.txt"

    if not os.path.isfile(sources_file_path):
        print("Creating sources.txt")
        with open(sources_file_path, 'w') as f:
            pass  # This creates an empty sources.txt file

    if not os.path.isfile(keywords_file_path):
        print("Creating keywords.txt")
        with open(keywords_file_path, 'w') as f:
            pass  # This creates an empty keywords.txt file

    return output_dir, task_file, img_pth, sources_file_path, keywords_file_path

if __name__ == "__main__":
    output_dir, task_file, img_pth, sources_file_path, keywords_file_path = setup_env()
    print(output_dir)
    print(task_file)
    print(img_pth)
    print(sources_file_path)
    print(keywords_file_path)
