from lib.constants import Constants
from lib.errors import ScraperRuntimeError
from lib.structures import YtScraperConfig
from lib.utils import get_webdriver, get_logger
from scrapers.channel_info import get_channel_info
from scrapers.videos import get_video_info


class YtScraper:
    def __init__(self, constants: Constants, config: YtScraperConfig):
        self.constants = constants
        self.config = config
        self.logger = get_logger(
            self.constants.LOGS_DIRECTORY,
            print_to_console=self.config.print_logs_to_console,
        )

    def scrape_channel_info(self, channel_name) -> tuple[bool, int]:
        channel_info_driver = get_webdriver()
        channel_id = -1

        try:
            channel_info_scraped, channel_id = get_channel_info(
                channel_info_driver,
                channel_name,
                Constants,
                self.logger,
                self.config.channel_db,
            )

            if channel_info_scraped:
                return True, channel_id

            return False, channel_id

        except ScraperRuntimeError:
            return False, channel_id

        except Exception as e:
            self.logger.error(
                f"Error while scraping channel info for {channel_name}: {e}"
            )
            return False, channel_id

        finally:
            channel_info_driver.quit()

    def scrape_channel_videos_basic_info(self, channel_name, channel_id) -> bool:
        channel_videos_driver = get_webdriver()

        try:
            scrape_channel_videos_basic_info_scraped = get_video_info(
                channel_videos_driver,
                channel_name,
                channel_id,
                Constants,
                self.logger,
                self.config.video_db,
            )

            if scrape_channel_videos_basic_info_scraped:
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
            channel_videos_driver.quit()
