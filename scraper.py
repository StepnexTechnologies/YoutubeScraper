import os
import csv
from queue import Queue
from threading import Lock
from datetime import datetime

from lib.constants import Constants
from lib.errors import ScraperRuntimeError
from lib.structures import YtScraperConfig
from lib.utils import get_logger, save_to_json, get_webdriver
from scrapers.live_streams import get_live_streams

from scrapers.shorts import get_shorts
from scrapers.videos import get_video_info
from scrapers.channel_info import get_channel_info
from scrapers.community_posts import get_community_posts


class YtScraper:
    def __init__(self, driver_pool: Queue, config: YtScraperConfig = YtScraperConfig()):
        self.log_directory = config.log_directory
        self.data_directory = config.data_directory
        self.metadata_file = os.path.join(self.data_directory, "run_metadata.csv")
        self.constants = Constants
        self.logger = get_logger(
            config.log_directory, print_to_console=config.print_logs_to_console
        )
        self.driver_pool = driver_pool
        self.thread_lock = Lock()

    def pre_run_setup(self):
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)

    def post_run_step(self):
        while not self.driver_pool.full():
            self.driver_pool.put(get_webdriver())

    def store_metadata(
        self,
        channel_name,
        info_scraped,
        videos_scraped,
        shorts_scraped,
        community_posts_scraped,
        channel_live_streams_scraped,
    ):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = [
            timestamp,
            channel_name,
            info_scraped,
            videos_scraped,
            shorts_scraped,
            community_posts_scraped,
            channel_live_streams_scraped,
        ]

        with self.thread_lock:
            with open(self.metadata_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(metadata)

    def scrape_channel_info(self, channel_name, save_json: bool = True) -> bool:
        if not os.path.exists(f"{self.data_directory}/{channel_name}"):
            os.makedirs(f"{self.data_directory}/{channel_name}")

        channel_info_driver = self.driver_pool.get()

        try:
            if not os.path.exists(f"{self.data_directory}/{channel_name}"):
                os.makedirs(f"{self.data_directory}/{channel_name}")

            channel_info = get_channel_info(
                channel_info_driver,
                channel_name,
                Constants,
                self.logger,
            )

            if save_json:
                save_to_json(
                    f"{self.data_directory}/{channel_name}/{self.constants.INFO_FILE_NAME}",
                    channel_info.model_dump_json(indent=4),
                )
            self.driver_pool.put(channel_info_driver)
            return True

        except ScraperRuntimeError:
            self.driver_pool.put(get_webdriver())
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel info for {channel_name}: {e}"
            )
            self.driver_pool.put(channel_info_driver)
            return False

    def scrape_channel_videos(self, channel_name) -> bool:
        if not os.path.exists(
            f"{self.data_directory}/{channel_name}/{self.constants.VIDEOS_DIRECTORY}"
        ):
            os.makedirs(
                f"{self.data_directory}/{channel_name}/{self.constants.VIDEOS_DIRECTORY}"
            )

        videos_info_driver = self.driver_pool.get()
        videos_details_driver = self.driver_pool.get()

        try:
            get_video_info(
                videos_info_driver,
                videos_details_driver,
                channel_name,
                self.constants,
                self.logger,
            )
            self.driver_pool.put(videos_info_driver)
            return True

        except ScraperRuntimeError:
            self.driver_pool.put(get_webdriver())
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel video info for {channel_name}: {e}"
            )
            self.driver_pool.put(videos_info_driver)
            return False

    def scrape_channel_shorts(self, channel_name) -> bool:
        if not os.path.exists(
            f"{self.data_directory}/{channel_name}/{self.constants.SHORTS_DIRECTORY}"
        ):
            os.makedirs(
                f"{self.data_directory}/{channel_name}/{self.constants.SHORTS_DIRECTORY}"
            )

        shorts_info_driver = self.driver_pool.get()
        shorts_details_driver = self.driver_pool.get()

        try:
            get_shorts(
                channel_name,
                shorts_info_driver,
                shorts_details_driver,
                self.constants,
                self.logger,
            )
            self.driver_pool.put(shorts_info_driver)
            self.driver_pool.put(shorts_details_driver)
            return True

        except ScraperRuntimeError:
            self.driver_pool.put(get_webdriver())
            self.driver_pool.put(get_webdriver())
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel shorts info for {channel_name}: {e}"
            )
            self.driver_pool.put(shorts_info_driver)
            self.driver_pool.put(shorts_details_driver)
            return False

    def scrape_channel_community_posts(self, channel_name) -> bool:
        if not os.path.exists(
            f"{self.data_directory}/{channel_name}/{self.constants.COMMUNITY_POSTS_DIRECTORY}"
        ):
            os.makedirs(
                f"{self.data_directory}/{channel_name}/{self.constants.COMMUNITY_POSTS_DIRECTORY}"
            )

        community_posts_driver = self.driver_pool.get()
        comments_posts_driver = self.driver_pool.get()
        try:
            get_community_posts(
                channel_name,
                comments_posts_driver,
                community_posts_driver,
                self.constants,
                self.logger,
            )
            self.driver_pool.put(community_posts_driver)
            return True

        except ScraperRuntimeError:
            self.driver_pool.put(get_webdriver())
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel community posts info for {channel_name}: {e}"
            )
            self.driver_pool.put(community_posts_driver)
            return False

    def scrape_channel_live_streams(self, channel_name) -> bool:
        if not os.path.exists(
            f"{self.data_directory}/{channel_name}/{self.constants.LIVE_STREAMS_DIRECTORY}"
        ):
            os.makedirs(
                f"{self.data_directory}/{channel_name}/{self.constants.LIVE_STREAMS_DIRECTORY}"
            )

        live_streams_driver = self.driver_pool.get()
        try:
            get_live_streams(
                channel_name, live_streams_driver, self.constants, self.logger
            )
            self.driver_pool.put(live_streams_driver)
            return True

        except ScraperRuntimeError:
            self.driver_pool.put(get_webdriver())
            return False

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel community posts info for {channel_name}: {e}"
            )
            self.driver_pool.put(live_streams_driver)
            return False

    def run(self, channel_name: str, store_run_metadata: bool = False):
        (
            info_scraped,
            videos_scraped,
            shorts_scraped,
            community_posts_scraped,
            channel_live_streams_scraped,
        ) = (
            False,
            False,
            False,
            False,
            False,
        )
        try:
            self.pre_run_setup()
            # info_scraped = self.scrape_channel_info(channel_name=channel_name)
            # shorts_scraped = self.scrape_channel_shorts(channel_name=channel_name)
            # videos_scraped = self.scrape_channel_videos(channel_name=channel_name)
            # community_posts_scraped = self.scrape_channel_community_posts(
            #     channel_name=channel_name
            # )
            # channel_live_streams_scraped = self.scrape_channel_live_streams(
            #     channel_name=channel_name
            # )
            self.post_run_step()

        except Exception as e:
            self.logger.critical(f"Scraping process failed: {e}")
        finally:
            self.logger.info(f"Scraping complete for {channel_name}")
            if store_run_metadata:
                self.store_metadata(
                    channel_name,
                    info_scraped,
                    videos_scraped,
                    shorts_scraped,
                    community_posts_scraped,
                    channel_live_streams_scraped,
                )
