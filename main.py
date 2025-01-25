from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from scraper import YtScraper
from constants import Constants
from structures import YtScraperConfig
from utils import get_webdriver


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
        log_directory="logs",
        data_directory="temp_data",
        print_logs_to_console=True,
    )

    driver_pool = Queue(maxsize=Constants.MAX_WORKERS + 2)
    for _ in range(Constants.MAX_WORKERS + 2):
        driver_pool.put(get_webdriver())

    channel_queue = Queue()
    for channel in channels:
        channel_queue.put(channel)

    max_threads = Constants.MAX_WORKERS

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(scrape_channel) for _ in range(max_threads)]

    print("Gracefully stopping...")
    while not driver_pool.empty():
        driver = driver_pool.get()
        driver.quit()

    print("Done!")
