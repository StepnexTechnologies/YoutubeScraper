import sys
import time
import logging

from lib.constants import Constants
from service import ScraperService
from logging.handlers import TimedRotatingFileHandler

# Primary Setup
constants = Constants()

# Logging Setup
formatter = logging.Formatter(
    "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)

file_handler = TimedRotatingFileHandler(
    "logs/app.log",
    when="midnight",
    interval=1,
    backupCount=7,
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

if __name__ == "__main__":
    try:
        service = ScraperService(
            constants=constants,
            logger=logger,
            num_workers=constants.MAX_WORKERS,
            metrics_port=constants.METRICS_PORT,
        )
        service.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            service.stop()

    except Exception as exp:
        logger.error(f"Fatal error: {str(exp)}")
        sys.exit(1)
