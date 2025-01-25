import os
from queue import Queue
from typing import Optional

from community_posts import get_community_posts
from constants import Constants
from shorts import get_shorts
from videos import get_video_info
from structures import ChannelInfo, YtScraperConfig
from channel_info import get_channel_info
from utils import get_logger, save_to_json


class YtScraper:
    max_retry_count = Constants.MAX_RETRY_COUNT

    def __init__(self, driver_pool: Queue, config: YtScraperConfig = YtScraperConfig()):
        self.log_directory = config.log_directory
        self.data_directory = config.data_directory

        self.constants = Constants

        self.logger = get_logger(
            config.log_directory, print_to_console=config.print_logs_to_console
        )

        self.driver_pool = driver_pool

    def pre_run_setup(self):
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)

    def scrape_channel_info(self, channel_name, save_json: bool = True):
        if not os.path.exists(f"{self.data_directory}/{channel_name}"):
            os.makedirs(f"{self.data_directory}/{channel_name}")

        channel_info_driver = self.driver_pool.get()

        try:
            if not os.path.exists(f"{self.data_directory}/{channel_name}"):
                os.makedirs(f"{self.data_directory}/{channel_name}")

            channel_info = get_channel_info(
                channel_info_driver,  # Use the shared driver
                channel_name,
                Constants,
                self.logger,
            )

            if save_json:
                save_to_json(
                    f"{self.data_directory}/{channel_name}/channel_info.json",
                    channel_info.model_dump_json(indent=4),
                )
            return channel_info

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel info for {channel_name}: {e}"
            )
            return None

        finally:
            self.driver_pool.put(channel_info_driver)

    def scrape_channel_videos(self, channel_name):
        if not os.path.exists(f"{self.data_directory}/{channel_name}/videos"):
            os.makedirs(f"{self.data_directory}/{channel_name}/videos")

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
        except Exception as e:
            self.logger.error(
                f"Error while scraping channel video info for {channel_name}: {e}"
            )
        finally:
            self.driver_pool.put(videos_info_driver)

    def scrape_channel_shorts(self, channel_name) -> Optional[ChannelInfo]:
        if not os.path.exists(f"{self.data_directory}/{channel_name}/shorts"):
            os.makedirs(f"{self.data_directory}/{channel_name}/shorts")

        shorts_info_driver = self.driver_pool.get()
        shorts_details_driver = self.driver_pool.get()

        try:
            shorts = get_shorts(
                channel_name,
                shorts_info_driver,
                shorts_details_driver,
                self.constants,
                self.logger,
            )
            return shorts
        except Exception as e:
            self.logger.error(
                f"Error while scraping channel shorts info for {channel_name}: {e}"
            )
            return None
        finally:
            self.driver_pool.put(shorts_info_driver)
            self.driver_pool.put(shorts_details_driver)

    def scrape_channel_community_posts(self, channel_name):
        if not os.path.exists(f"{self.data_directory}/{channel_name}/community_posts"):
            os.makedirs(f"{self.data_directory}/{channel_name}/community_posts")
        community_posts_driver = self.driver_pool.get()

        try:
            get_community_posts(channel_name, community_posts_driver, self.logger)
        except Exception as e:
            self.logger.error(
                f"Error while scraping channel community posts info for {channel_name}: {e}"
            )
        finally:
            self.driver_pool.put(community_posts_driver)

    def run(self, channel_name: list[str]):
        try:
            self.pre_run_setup()
            self.scrape_channel_info(channel_name=channel_name)
            self.scrape_channel_videos(channel_name=channel_name)
            self.scrape_channel_shorts(channel_name=channel_name)
            self.scrape_channel_community_posts(channel_name=channel_name)
        except Exception as e:
            self.logger.critical(f"Scraping process failed: {e}")
        finally:
            self.logger.info(f"Scraping complete for {channel_name}")
