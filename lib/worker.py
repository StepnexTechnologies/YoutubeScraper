import threading
import time
from logging import Logger

from lib.constants import Constants
from lib.job_queue import JobQueue
from lib.structures import JobType
from scraper import YtScraper


class ScraperWorker(threading.Thread):
    def __init__(
        self,
        constants: Constants,
        logger: Logger,
        worker_id: int,
        job_queue: JobQueue,
        scraper: YtScraper,
    ):
        super().__init__(name=f"Worker-{worker_id}")
        self.constants = constants
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.scraper = scraper
        self.running = True
        self.logger = logger

    def run(self):
        self.logger.info(f"Worker {self.worker_id} started execution...")
        while self.running:
            job = self.job_queue.get_job()
            if not job:
                time.sleep(1)
                continue

            try:
                self.constants.ACTIVE_SCRAPES.inc()
                self.logger.info(
                    f"Worker {self.worker_id} processing {job.channel_name}"
                )

                if job.job_type == JobType.channel_info:
                    # scrape channel info
                    success, channel_id = self.scraper.scrape_channel_info(
                        job.channel_name
                    )
                    if success:
                        self.logger.info(f"{job.channel_name} channel info scraped")
                        self.constants.JOBS_PROCESSED.labels(status="success").inc()

                        # adding job for fetching videos basic info
                        self.job_queue.add_job(
                            channel_name=job.channel_name,
                            job_type=JobType.videos_basic_info,
                            data={"channel_id": channel_id},
                        )
                        self.logger.info(
                            f"Added video info scraping job for {job.channel_name}."
                        )
                    else:
                        self.constants.JOBS_PROCESSED.labels(status="failure").inc()
                elif job.job_type == JobType.videos_basic_info:
                    # scrape videos basic info
                    success = self.scraper.scrape_channel_videos_basic_info(
                        job.channel_name, job.data["channel_id"]
                    )
                    if success:
                        self.logger.info(
                            f"{job.channel_name} channel videos basic info scraped"
                        )
                        self.constants.JOBS_PROCESSED.labels(status="success").inc()
                        # add other jobs here

                    else:
                        self.constants.JOBS_PROCESSED.labels(status="failure").inc()

            except Exception as e:
                self.logger.error(f"Error processing {job.channel_name}: {str(e)}")
                self.constants.JOBS_PROCESSED.labels(status="failure").inc()

            finally:
                self.constants.ACTIVE_SCRAPES.dec()
                self.job_queue.complete_job(job.channel_name)
