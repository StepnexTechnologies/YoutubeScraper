import os
import yaml
import json
import signal
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

# import sentry_sdk
from tenacity import retry, stop_after_attempt, wait_exponential
from Yt.shorts import get_shorts
from videos import get_video_info
from channel_info import get_channel_info
from utils import get_logger, get_webdriver
from structures import ChannelInfo, VideoInfo, ShortInfo
from constants import Constants


class ScraperConfigError(Exception):
    """Configuration error for the scraper."""

    pass


class ScraperRuntimeError(Exception):
    """Runtime error during scraping process."""

    pass


@dataclass
class ScraperConfig:
    """Configuration for the YouTube scraper."""

    log_directory: str = "logs"
    data_directory: str = "temp_data"
    max_retries: int = 1
    timeout: int = 30
    proxy: Optional[str] = None
    # sentry_dsn: Optional[str] = None


class YtScraper:
    def __init__(self, config: ScraperConfig = ScraperConfig()):
        """
        Initialize the YouTube scraper with robust configuration.

        Args:
            config (ScraperConfig): Configuration parameters for the scraper
        """
        self._validate_config(config)

        # Setup logging
        self.logger = get_logger(config.log_directory)

        # # Setup error tracking
        # if config.sentry_dsn:
        #     sentry_sdk.init(dsn=config.sentry_dsn)

        # Webdriver management
        self._drivers = {
            "channel_info": self._create_safe_driver(),
            "video_details": self._create_safe_driver(),
            "shorts_info": self._create_safe_driver(),
            "shorts_details": self._create_safe_driver(),
        }

        self.config = config
        self.constants = Constants

        # Graceful shutdown setup
        self._stop_event = threading.Event()
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _validate_config(self, config: ScraperConfig):
        """Validate scraper configuration."""
        if not os.path.exists(config.log_directory):
            os.makedirs(config.log_directory)

        if not os.path.exists(config.data_directory):
            os.makedirs(config.data_directory)

    def _create_safe_driver(self):
        """Create a safely managed webdriver with error handling."""
        try:
            driver = get_webdriver()
            # Set implicit wait and page load timeout
            # driver.implicitly_wait(10)
            # driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            self.logger.error(f"Webdriver initialization failed: {e}")
            # sentry_sdk.capture_exception(e)
            raise ScraperConfigError("Could not initialize webdriver")

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown of scraping process."""
        self.logger.info(f"Received signal {signum}. Initiating graceful shutdown.")
        self._stop_event.set()
        self._cleanup_drivers()

    def _cleanup_drivers(self):
        """Close all webdriver instances safely."""
        for name, driver in self._drivers.items():
            try:
                driver.quit()
                self.logger.info(f"Closed {name} driver successfully")
            except Exception as e:
                self.logger.error(f"Error closing {name} driver: {e}")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def scrape_channel_info(self, channel_name: str) -> Optional[ChannelInfo]:
        """
        Scrape channel information with robust error handling.

        Args:
            channel_name (str): Name of the YouTube channel

        Returns:
            Optional[ChannelInfo]: Parsed channel information
        """
        if self._stop_event.is_set():
            return None

        try:
            channel_info = get_channel_info(
                self._drivers["channel_info"], channel_name, self.constants, self.logger
            )

            if not channel_info:
                self.logger.warning(f"No information found for channel: {channel_name}")
                return None

            channel_info_obj = ChannelInfo.parse_obj(channel_info)
            filename = channel_name

            output_path = os.path.join(
                self.config.data_directory, f"{filename}_channel_info.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(channel_info_obj.json(), f)

            return channel_info_obj

        except Exception as e:
            self.logger.error(f"Error scraping channel info for {channel_name}: {e}")
            # sentry_sdk.capture_exception(e)
            return None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def scrape_channel_videos(self, channel_name: str) -> List[VideoInfo]:
        """
        Scrape videos from a given channel with error handling.

        Args:
            channel_name (str): Name of the YouTube channel

        Returns:
            List[VideoInfo]: List of scraped video information
        """
        if self._stop_event.is_set():
            return []

        try:
            videos = get_video_info(
                self._drivers["video_details"],
                channel_name,
                self.constants,
                self.logger,
            )

            if not videos:
                self.logger.warning(f"No videos found for channel: {channel_name}")
                return []

            # Save videos to JSON
            output_path = os.path.join(
                self.config.data_directory, f"{channel_name}_videos.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(video) for video in videos], f, ensure_ascii=False, indent=2
                )

            return videos

        except Exception as e:
            self.logger.error(f"Error scraping videos for {channel_name}: {e}")
            # sentry_sdk.capture_exception(e)
            return []

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def scrape_channel_shorts(self, channel_name: str) -> List[ShortInfo]:
        """
        Scrape shorts from a given channel with error handling.

        Args:
            channel_name (str): Name of the YouTube channel

        Returns:
            List[ShortInfo]: List of scraped short video information
        """
        if self._stop_event.is_set():
            return []

        try:
            shorts = get_shorts(
                channel_name,
                self._drivers["shorts_info"],
                self._drivers["shorts_details"],
                self.constants,
                self.logger,
            )

            if not shorts:
                self.logger.warning(f"No shorts found for channel: {channel_name}")
                return []

            # Save shorts to JSON
            output_path = os.path.join(
                self.config.data_directory, f"{channel_name}_shorts.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(short) for short in shorts], f, ensure_ascii=False, indent=2
                )

            return shorts

        except Exception as e:
            self.logger.error(f"Error scraping shorts for {channel_name}: {e}")
            # sentry_sdk.capture_exception(e)
            return []

    def scrape_community_posts(self, channel_name: str) -> List[Dict[str, Any]]:
        """
        Scrape community posts from a given channel.

        Args:
            channel_name (str): Name of the YouTube channel

        Returns:
            List[Dict[str, Any]]: List of community posts
        """
        if self._stop_event.is_set():
            return []

        try:
            # Placeholder for community posts scraping
            # Implement actual scraping logic based on YouTube's structure
            community_posts = []  # Replace with actual scraping method

            if not community_posts:
                self.logger.warning(
                    f"No community posts found for channel: {channel_name}"
                )
                return []

            output_path = os.path.join(
                self.config.data_directory, f"{channel_name}_community_posts.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(community_posts, f, ensure_ascii=False, indent=2)

            return community_posts

        except Exception as e:
            self.logger.error(f"Error scraping community posts for {channel_name}: {e}")
            # sentry_sdk.capture_exception(e)
            return []

    def scrape_trending_shorts_and_videos(self) -> Dict[str, List[Any]]:
        """
        Scrape trending shorts and videos across YouTube.

        Returns:
            Dict[str, List[Any]]: Dictionary containing trending shorts and videos
        """
        if self._stop_event.is_set():
            return {}

        try:
            # Placeholder for trending content scraping
            trending_shorts = []  # Replace with actual trending shorts scraping
            trending_videos = []  # Replace with actual trending videos scraping

            trending_content = {"shorts": trending_shorts, "videos": trending_videos}

            output_path = os.path.join(
                self.config.data_directory, "trending_content.json"
            )

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(trending_content, f, ensure_ascii=False, indent=2)

            return trending_content

        except Exception as e:
            self.logger.error(f"Error scraping trending content: {e}")
            # sentry_sdk.capture_exception(e)
            return {}

    def scrape_multiple_channels(self, channels: List[str]):
        """
        Scrape information for multiple channels with threading.

        Args:
            channels (List[str]): List of channel names to scrape
        """

        def worker(channel):
            try:
                self.scrape_channel_info(channel)
                self.scrape_channel_videos(channel)
                self.scrape_channel_shorts(channel)
            except Exception as e:
                self.logger.error(f"Error processing channel {channel}: {e}")

        threads = []
        for channel in channels:
            if self._stop_event.is_set():
                break
            thread = threading.Thread(target=worker, args=(channel,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    # Other methods remain similar with added error handling and logging

    def run(self, channels: List[str], ignore_list: Optional[List[str]] = None):
        """
        Main execution method for the scraper.

        Args:
            channels (List[str]): Channels to scrape
            ignore_list (Optional[List[str]]): Channels to skip
        """
        ignore_list = ignore_list or []

        # Filter out ignored channels
        channels_to_scrape = [
            channel for channel in channels if channel not in ignore_list
        ]

        try:
            self.scrape_multiple_channels(channels_to_scrape)
        except Exception as e:
            self.logger.critical(f"Scraping process failed: {e}")
            # sentry_sdk.capture_exception(e)
        finally:
            self._cleanup_drivers()


def load_scraper_config(config_path: str = "scraper_config.yaml") -> ScraperConfig:
    """
    Load scraper configuration from a YAML file.

    Args:
        config_path (str): Path to configuration file

    Returns:
        ScraperConfig: Configured scraper settings
    """
    try:
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)
        return ScraperConfig(**config_dict)
    except FileNotFoundError:
        return ScraperConfig()  # Default configuration
    except Exception as e:
        raise ScraperConfigError(f"Invalid configuration: {e}")


# Example usage
if __name__ == "__main__":
    try:
        config = load_scraper_config()
        scraper = YtScraper(config)
        scraper.run(channels=["@MrBeast", "@PewDiePie"], ignore_list=["channel3"])
    except Exception as e:
        print(f"Scraper failed: {e}")
