import logging
import os
import sys
import threading
import time
from queue import Queue
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from prometheus_client import start_http_server, Counter, Histogram, Gauge

from db import YtChannelDB
from lib.constants import Constants
from lib.errors import ScraperRuntimeError
from lib.structures import YtScraperConfig
from lib.utils import get_webdriver, get_logger
from scrapers.channel_info import get_channel_info


# metrics
CHANNEL_SCRAPES = Counter(
    "channel_scrapes_total",
    "Total number of channel scraping attempts",
    ["status", "type"],
)

SCRAPE_DURATION = Histogram(
    "scrape_duration_seconds",
    "Time spent scraping channels",
    buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

TOTAL_SCRAPE_DURATION = Counter(
    "total_scrape_duration",
    "Total time taken for scraping",
    ["status", "type"],
)

ACTIVE_SCRAPES = Gauge(
    "active_scrapes", "Number of currently active scraping operations"
)

JOBS_PROCESSED = Counter(
    "jobs_processed_total", "Total number of jobs processed", ["status"]
)

QUEUE_SIZE = Gauge("job_queue_size", "Current number of jobs in queue")


channel_db = YtChannelDB()


@dataclass
class ScrapeJob:
    channel_name: str
    created_at: datetime


class YtScraper:
    def __init__(self, config: YtScraperConfig = YtScraperConfig()):
        self.log_directory = config.log_directory
        self.data_directory = config.data_directory
        self.metadata_file = os.path.join(self.data_directory, "run_metadata.csv")
        self.constants = Constants
        self.logger = get_logger(
            config.log_directory, print_to_console=config.print_logs_to_console
        )
        self.thread_lock = threading.Lock()

    def scrape_channel_info(self, channel_name) -> bool:
        if not os.path.exists(f"{self.data_directory}/{channel_name}"):
            os.makedirs(f"{self.data_directory}/{channel_name}")

        channel_info_driver = get_webdriver()

        try:
            if not os.path.exists(f"{self.data_directory}/{channel_name}"):
                os.makedirs(f"{self.data_directory}/{channel_name}")

            channel_info_scraped = get_channel_info(
                channel_info_driver, channel_name, Constants, self.logger, channel_db
            )

            if channel_info_scraped:
                return True
            return False

        except ScraperRuntimeError:
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel info for {channel_name}: {e}"
            )
            return False

        finally:
            channel_info_driver.quit()


class JobQueue:
    def __init__(self, max_size: int = 1000):
        self.queue = Queue(maxsize=max_size)
        self.processing = set()
        self.lock = threading.Lock()

    def add_job(self, channel_name: str) -> None:
        job = ScrapeJob(channel_name=channel_name, created_at=datetime.now())
        self.queue.put(job)
        QUEUE_SIZE.inc()

    def get_job(self) -> Optional[ScrapeJob]:
        if self.queue.empty():
            return None
        job = self.queue.get()
        with self.lock:
            self.processing.add(job.channel_name)
        QUEUE_SIZE.dec()
        return job

    def complete_job(self, channel_name: str) -> None:
        with self.lock:
            self.processing.discard(channel_name)

    def is_full(self) -> bool:
        return self.queue.full()

    def is_empty(self) -> bool:
        return self.queue.empty()


class ScraperWorker(threading.Thread):
    def __init__(self, worker_id: int, job_queue: JobQueue, scraper: YtScraper):
        super().__init__(name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.scraper = scraper
        self.running = True

    def run(self):
        logger.info(f"Worker {self.worker_id} started execution...")
        while self.running:
            job = self.job_queue.get_job()
            if not job:
                time.sleep(1)
                continue

            try:
                ACTIVE_SCRAPES.inc()
                logger.info(f"Worker {self.worker_id} processing {job.channel_name}")

                # Scrape channel info
                success = self.scraper.scrape_channel_info(job.channel_name)
                if success:
                    logger.info(f"{job.channel_name} scraped")

                    JOBS_PROCESSED.labels(status="success").inc()
                else:
                    JOBS_PROCESSED.labels(status="failure").inc()

            except Exception as e:
                logger.error(f"Error processing {job.channel_name}: {str(e)}")
                JOBS_PROCESSED.labels(status="failure").inc()

            finally:
                ACTIVE_SCRAPES.dec()
                self.job_queue.complete_job(job.channel_name)


class MetricsServer:
    def __init__(self, port: int = 8000):
        self.port = port
        self.server_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self):
        def run_metrics_server():
            start_http_server(self.port)
            while self.running:
                time.sleep(1)

        self.running = True
        self.server_thread = threading.Thread(
            target=run_metrics_server, name="metrics-server", daemon=True
        )
        self.server_thread.start()
        logger.info(f"Metrics server started on port {self.port}")

    def stop(self):
        self.running = False
        if self.server_thread:
            self.server_thread.join()


class ScraperService:
    def __init__(self, num_workers: int = 4, metrics_port: int = 5001):
        self.config = YtScraperConfig(
            log_directory=Constants.LOGS_DIRECTORY,
            data_directory=Constants.DATA_DIRECTORY,
            print_logs_to_console=True,
        )
        self.scraper = YtScraper(self.config)
        self.job_queue = JobQueue()
        self.workers = []
        self.num_workers = num_workers
        self.metrics_server = MetricsServer(port=metrics_port)

    def start(self):
        # Start metrics server
        self.metrics_server.start()

        # Create and start worker threads
        for i in range(self.num_workers):
            worker = ScraperWorker(i, self.job_queue, self.scraper)
            worker.start()
            self.workers.append(worker)

        logger.info("Scraper service started, polling for new jobs.")

        # Continuous polling for new unscraped channels
        while not self.job_queue.is_full():
            channels = channel_db.get_unscraped_channels()
            if channels:
                for channel in channels:
                    self.job_queue.add_job(channel)

                logger.info(f"Added {len(channels)} new channels to queue.")

            time.sleep(60)

    def stop(self):
        # Stop all workers
        for worker in self.workers:
            worker.running = False

        # Wait for all workers to complete
        for worker in self.workers:
            worker.join()

        # Stop metrics server
        self.metrics_server.stop()


if __name__ == "__main__":
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
    # logger.addHandler(console_handler)
    try:
        service = ScraperService(num_workers=3)
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
