import logging
import os

_log_file = os.environ.get("GOL_LOG_FILE", "gol_eval.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_file),
    ]
)

logger = logging.getLogger(__name__)