import threading
from queue import Queue
from typing import Optional

from lib.constants import Constants
from lib.structures import ScrapeInfoJob, JobType


class JobQueue:
    def __init__(self, constants: Constants, max_size: int = 1000):
        self.queue = Queue(maxsize=max_size)
        self.processing = set()
        self.constants = constants
        self.lock = threading.Lock()

    def add_job(
        self, channel_name: str, job_type: JobType, data: Optional[dict]
    ) -> None:
        job = ScrapeInfoJob(channel_name=channel_name, job_type=job_type, data=data)
        self.queue.put(job)
        self.constants.QUEUE_SIZE.inc()

    def get_job(self) -> Optional[ScrapeInfoJob]:
        if self.queue.empty():
            return None
        job = self.queue.get()
        with self.lock:
            self.processing.add(job.channel_name)
        self.constants.QUEUE_SIZE.dec()
        return job

    def complete_job(self, channel_name: str) -> None:
        with self.lock:
            self.processing.discard(channel_name)

    def is_full(self) -> bool:
        return self.queue.full()

    def is_empty(self) -> bool:
        return self.queue.empty()
