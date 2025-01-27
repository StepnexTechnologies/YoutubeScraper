import re
import time
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from selenium import webdriver
from selenium.webdriver import Keys
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_webdriver(headless: bool = True, proxy_server_url: str | None = None):
    options = Options()

    options.add_argument("--no-sandbox")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

    if proxy_server_url:
        options.add_argument(f"--proxy-server={proxy_server_url}")

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    stealth(
        driver=driver,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=False,
        run_on_insecure_origins=False,
    )

    return driver


def unzip_large_nums(num: str) -> int:
    try:
        x = num[-1]

        if x not in ["B", "M", "K"]:
            return int(num)

        n = int(float(num[:-1]))

        if x == "B":
            n *= 1000000000
        elif x == "M":
            n *= 1000000
        elif x == "K":
            n *= 1000
        return n
    except (ValueError, IndexError) as e:
        return 0


def scroll_to_bottom(driver, pause_time, scroll_count):
    last_height = driver.execute_script("return document.documentElement.scrollHeight")

    for i in range(scroll_count):
        driver.execute_script(
            "window.scrollTo(0, document.documentElement.scrollHeight);"
        )
        time.sleep(pause_time)
        new_height = driver.execute_script(
            "return document.documentElement.scrollHeight"
        )
        if new_height != last_height:
            last_height = new_height
    driver.execute_script("window.scrollTo(0, 0);")


def scroll(driver, pause_time, scroll_count, delay):
    for _ in range(scroll_count):
        for _ in range(4):
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            ).send_keys(Keys.PAGE_DOWN)

        time.sleep(pause_time)
    driver.execute_script("window.scrollTo(0, 0);")


def scroll_until_element_found():
    pass


def get_logger(directory: str, print_to_console: bool = False):
    log_formatter = logging.Formatter(
        "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # file_handler = logging.FileHandler(f"{directory}/run_{datetime.now()}.log")
    file_handler = TimedRotatingFileHandler(
        f"{directory}/run_{datetime.now()}.log",
        when="midnight",
        interval=1,
        backupCount=7,
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    if print_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

    return logger


def save_to_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as json_file:
            json_file.write(data)
        print(f"Data successfully saved to {path}")
    except Exception as e:
        print(f"An error occurred while saving to JSON: {e}")


def video_duration_parser(str_duration: str) -> int:
    if str_duration == "":
        return 0

    d = str_duration.split(":")
    d.reverse()

    duration = sum(int(num) * (60**i) for i, num in enumerate(d))

    return duration


def extract_hashtags(text: str) -> list[str]:
    if text:
        return re.findall(r"#\w+", text)
    return []


if __name__ == "__main__":
    print(
        extract_hashtags(
            "Loving the #awesome weather and feeling #grateful for everything! #Python #coding"
        )
    )
