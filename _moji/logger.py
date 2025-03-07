from os import path, mkdir
import logging
from logging.handlers import RotatingFileHandler

ROOT_DIR = path.dirname(path.abspath(__file__))
log_folder = f"{ROOT_DIR}/.logs"
# Creating the log folder if it doesn't exist
if not path.exists(log_folder):
    mkdir(log_folder)
log_path = f"{ROOT_DIR}/.logs/server.log"
error_log_path = f"{ROOT_DIR}/.logs/error.log"

# Configuring logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        # logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# # Adding a new handler for errors only
# error_handler = logging.FileHandler(error_log_path)
# error_handler.setLevel(logging.ERROR)
# error_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
# error_handler.setFormatter(error_formatter)
# logger.addHandler(error_handler)

# # Setting up rotation: Max size 5 MB, backup count 3
# handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
# logger.addHandler(handler)
