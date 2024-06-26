import logging
import sys

class ForcedFlushHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logging(log_file_path):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            ForcedFlushHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ],
    )