from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from scraper import YtScraper
from lib.constants import Constants
from lib.structures import YtScraperConfig
from lib.utils import get_webdriver


def scrape_channel():
    scraper = YtScraper(driver_pool, scraper_config)
    while not channel_queue.empty():
        channel_name = channel_queue.get()
        if channel_name:
            scraper.run(channel_name, store_run_metadata=True)
            channel_queue.task_done()


if __name__ == "__main__":
    with open("channel_names.txt", "r") as f:
        channels = [channel.strip() for channel in f.readlines()]

    scraper_config = YtScraperConfig(
        log_directory=Constants.LOGS_DIRECTORY,
        data_directory=Constants.DATA_DIRECTORY,
        print_logs_to_console=True,
    )

    driver_pool = Queue(maxsize=Constants.MAX_DRIVERS)
    while not driver_pool.full():
        driver_pool.put(get_webdriver(headless=True))

    channel_queue = Queue()
    for channel in channels:
        channel_queue.put(channel)

    max_threads = Constants.MAX_WORKERS

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(scrape_channel) for _ in range(max_threads)]

    channel_queue.join()

    print("Gracefully stopping...")
    while not driver_pool.empty():
        driver = driver_pool.get()
        driver.quit()

    print("Done!")
