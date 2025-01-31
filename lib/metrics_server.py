import threading
import time
from logging import Logger
from typing import Optional

from prometheus_client import start_http_server


class MetricsServer:
    def __init__(self, logger: Logger, port: int):
        self.port = port
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self.logger = logger

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
        self.logger.info(f"Metrics server started on port {self.port}")

    def stop(self):
        self.running = False
        if self.server_thread:
            self.server_thread.join()
