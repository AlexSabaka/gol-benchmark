import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_of_life_eval.log'),
        # logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)