import os
from dotenv import load_dotenv

def setup_env():
    def check_env_file_exists(directory='.'):
        env_file_path = os.path.join(directory, '.env')
        return os.path.isfile(env_file_path)

    if check_env_file_exists():
        load_dotenv()
        output_dir = os.getenv("OUTPUT_DIR")
        task_file = os.getenv("TASK_FILE")
        img_pth = os.getenv("IMG_PATH")
    else:
        output_dir = "Output"
        task_file = "tasks.txt"
        img_pth = "front.jpg"

    return output_dir, task_file, img_pth

if __name__ == "__main__":
    output_dir, task_file, img_pth = setup_env()
    print(output_dir)
    print(task_file)
    print(img_pth)
