from logging import Logger
import time
from lib.constants import Constants
from lib.dashboard_server import DashboardServer
from lib.job_queue import JobQueue
from lib.metrics_server import MetricsServer
from lib.structures import YtScraperConfig, JobType
from lib.worker import ScraperWorker
from scraper import YtScraper


class ScraperService:
    def __init__(self, constants: Constants, logger: Logger):
        self.constants = constants
        self.logger = logger
        self.config = YtScraperConfig()
        self.scraper = YtScraper(self.constants, self.config)
        self.job_queue = JobQueue(constants=self.constants)
        self.workers = []
        self.num_workers = self.constants.MAX_WORKERS
        self.metrics_server = MetricsServer(
            logger=self.logger, port=self.constants.METRICS_PORT
        )
        self.dashboard_server = DashboardServer(
            logger=self.logger, port=self.constants.DASHBOARD_PORT
        )

    def start(self):
        self.metrics_server.start()
        self.dashboard_server.start()

        for i in range(self.num_workers):
            worker = ScraperWorker(
                self.constants, self.logger, i, self.job_queue, self.scraper
            )
            worker.start()
            self.workers.append(worker)

        self.logger.info("Scraper service started, polling for new jobs.")

        # adding new unscraped channels
        while not self.job_queue.is_full():
            channels = self.config.channel_db.get_unscraped_channels()
            if channels:
                for channel in channels:
                    self.job_queue.add_job(
                        channel_name=channel, job_type=JobType.channel_info, data=None
                    )

                self.logger.info(f"Added {len(channels)} new channels to queue.")

            time.sleep(60)

    def stop(self):
        for worker in self.workers:
            worker.running = False

        for worker in self.workers:
            worker.join()

        self.metrics_server.stop()
        self.dashboard_server.stop()
