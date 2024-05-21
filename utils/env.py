import os
from dotenv import load_dotenv

def setup_env():
    def check_env_file_exists(directory='.'):
        env_file_path = os.path.join(directory, '.env')
        return os.path.isfile(env_file_path)

    if check_env_file_exists():
        load_dotenv()
        output_dir = os.getenv("OUTPUT_DIR")
        urls_file = os.getenv("URL_FILE")
        img_pth = os.getenv("IMG_PATH")
    else:
        output_dir = "Output"
        urls_file = "urls.txt"
        img_pth = "front.jpg"

    return output_dir, urls_file, img_pth
