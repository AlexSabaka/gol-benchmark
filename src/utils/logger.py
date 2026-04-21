import logging
import os
from pathlib import Path

# Resolve log file path:
#   1. GOL_LOG_FILE env override (explicit, wins) — preserved for back-compat.
#   2. Otherwise use WebConfig.log_file (routes through data/logs/).
_log_file = os.environ.get("GOL_LOG_FILE")
if not _log_file:
    try:
        from src.web.config import web_config
        _log_file = web_config.log_file
    except Exception:
        _log_file = "gol_eval.log"

Path(_log_file).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_file),
    ]
)

logger = logging.getLogger(__name__)
