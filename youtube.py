import os
import json
import time
import logging
from tqdm import tqdm
from datetime import datetime

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)
from webdriver_manager.chrome import ChromeDriverManager

# Logging
log_formatter = logging.Formatter("%(asctime)s %(levelname)s  %(message)s")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

fileHandler = logging.FileHandler(f"logs/run_{datetime.now()}.log")
fileHandler.setFormatter(log_formatter)
logger.addHandler(fileHandler)

# consoleHandler = logging.StreamHandler()
# consoleHandler.setFormatter(log_formatter)
# logger.addHandler(consoleHandler)

# Initial Data
channels = [
    "@MrBeast",
    "@PewDiePie",
    "@TSeries",
    "@Cocomelon",
    "@SETIndia",
    "@5MinuteCrafts",
    "@DudePerfect",
    "@VladandNiki",
    "@LikeNastya",
    "@Markiplier",
    "@JamesCharles",
    "@EmmaChamberlain",
    "@casey",
    "@Kurzgesagt",
    "@HowToBasic",
    "@MKBHD",
    "@LinusTechTips",
    "@TheEllenShow",
    "@Shane",
    "@Smosh",
    "@Nigahiga",
    "@JennaMarbles",
    "@LillySingh",
    "@Zoella",
    "@DavidDobrik",
    "@JakePaul",
    "@LoganPaul",
    "@RhettandLink",
    "@TheTryGuys",
    "@PhilipDeFranco",
    "@FitnessBlender",
    "@MichellePhan",
    "@Vsauce",
    "@Veritasium",
    "@CGPGrey",
    "@TEDxTalks",
    "@Numberphile",
    "@MinutePhysics",
    "@CrashCourse",
    "@ScienceChannel",
    "@AsapSCIENCE",
    "@NationalGeographic",
    "@DiscoveryChannel",
    "@BraveWilderness",
    "@BrightSide",
    "@TechLinked",
    "@UnboxTherapy",
    "@DaveLee",
    "@AustinEvans",
    "@LinusTechTips",
    "@JerryRigEverything",
    "@SuperSaf",
    "@TheVerge",
    "@TheLateShow",
    "@JimmyKimmelLive",
    "@TheTonightShow",
    "@LateNightSeth",
    "@Netflix",
    "@HBO",
    "@PrimeVideo",
    "@GameTheory",
    "@MatPatGT",
    "@FilmTheory",
    "@ScreenJunkies",
    "@CinemaSins",
    "@PitchMeeting",
    "@ScreenRant",
    "@WatchMojo",
    "@Top10s",
    "@EpicMealTime",
    "@BingingWithBabish",
    "@SortedFood",
    "@Tasty",
    "@BonAppetit",
    "@GordonRamsay",
    "@JoshuaWeissman",
    "@AlmazanKitchen",
    "@RosannaPansino",
    "@JamieOliver",
    "@BuzzFeed",
    "@Cut",
    "@Jubilee",
    "@YesTheory",
    "@BeastReacts",
    "@MrBeastGaming",
    "@Dream",
    "@GeorgeNotFound",
    "@Sapnap",
    "@Technoblade",
    "@TommyInnit",
    "@WilburSoot",
    "@Tubbo",
    "@Ranboo",
    "@Stampylonghead",
    "@DanTDM",
    "@PopularMMOs",
    "@Jacksepticeye",
    "@Ninja",
    "@Shroud",
    "@Pokimane",
]

delay = 10
# directory = "data"
# directory = "temp_data"
directory = "new_data"


def get_webdriver():
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


driver = get_webdriver()


def retry_scrape(channel_name, retries=2):
    global driver
    for attempt in range(retries):
        try:
            logging.info(
                f"Starting scrape for channel: {channel_name} (Attempt {attempt + 1})"
            )
            driver = get_webdriver()
            scrape_channel(channel_name)
            logging.info(f"Successfully scraped channel: {channel_name}")
            return
        except WebDriverException as e:
            attempt += 1
            logging.warning(f"Error scraping {channel_name}: {e}. Retrying...")
            time.sleep(2**attempt)  # Exponential backoff
        finally:
            if "driver" in locals() and driver:
                driver.quit()
    logging.error(f"Failed to scrape channel after {retries} attempts: {channel_name}")


def unzip_large_nums(num: str) -> int:
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


def scroll(driver, pause_time, scroll_count):
    for _ in range(scroll_count):
        for _ in range(3):
            WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            ).send_keys(Keys.PAGE_DOWN)

        time.sleep(pause_time)
    driver.execute_script("window.scrollTo(0, 0);")


def get_channel_info():
    info = {
        "name": "",
        "is_verified": False,
        "about": "",
        "links": [],
        "channel_details": {
            "subscribers": -1,
            "videos_count": -1,
            "views_count": -1,
            "joined_date": "",
            "location": "",  # Some have, some don't
        },
    }

    try:
        # Name and Verification Status
        try:
            logging.info("Fetching channel name and verification status.")
            name_container = (
                WebDriverWait(driver, delay)
                .until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "dynamic-text-view-model-wiz__h1")
                    )
                )
                .find_element(By.TAG_NAME, "span")
            )
            info["name"] = name_container.text

            try:
                if name_container.find_element(By.TAG_NAME, "span"):
                    info["is_verified"] = True
            except NoSuchElementException:
                info["is_verified"] = False
                logging.info("Verification status: Not verified.")
        except TimeoutException:
            logging.error("Failed to fetch channel name and verification status.")

        # More button to get about information
        try:
            logging.info("Clicking 'More' button to fetch about info.")
            more_btn = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "truncated-text-wiz__absolute-button")
                )
            )
            more_btn.click()

            about = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-engagement-panel-section-list"
                        "-renderer/div[2]/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div["
                        "3]/ytd-about-channel-renderer/div/yt-attributed-string/span",
                    )
                )
            )
            info["about"] = about.text
        except TimeoutException:
            logging.error("Failed to fetch about info.")

        # Channels Links
        try:
            logging.info("Fetching channel links.")
            links_section = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.ID, "link-list-container"))
            )
            link_containers = links_section.find_elements(
                By.TAG_NAME, "yt-channel-external-link-view-model"
            )
            for link_container in link_containers:
                container = link_container.find_elements(By.TAG_NAME, "span")
                info["links"].append(
                    {"title": container[0].text, "url": container[1].text}
                )
        except TimeoutException:
            logging.error("Failed to fetch channel links.")

        # Channel Details Section
        try:
            logging.info(
                "Fetching channel details (subscribers, videos, views, joined date)."
            )
            channel_details_section = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-engagement-panel-section-list"
                        "-renderer/div[2]/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div["
                        "3]/ytd-about-channel-renderer/div/div[5]/table",
                    )
                )
            )
            rows = channel_details_section.find_elements(By.TAG_NAME, "tr")

            try:
                info["channel_details"]["subscribers"] = unzip_large_nums(
                    rows[3].find_elements(By.TAG_NAME, "td")[1].text.split(" ")[0]
                )
            except (IndexError, ValueError):
                logging.error("Failed to fetch subscribers count.")

            try:
                info["channel_details"]["videos_count"] = int(
                    rows[4]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.split(" ")[0]
                    .replace(",", "")
                )
            except (IndexError, ValueError):
                logging.error("Failed to fetch videos count.")

            try:
                info["channel_details"]["views_count"] = int(
                    rows[5]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.split(" ")[0]
                    .replace(",", "")
                )
            except (IndexError, ValueError):
                logging.error("Failed to fetch views count.")

            try:
                info["channel_details"]["joined_date"] = (
                    rows[6]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.replace("Joined ", "")
                )
            except (IndexError, AttributeError):
                logging.error("Failed to fetch joined date.")
        except TimeoutException:
            logging.error("Failed to fetch channel details section.")

        # Close details button
        try:
            logging.info("Closing channel details popup.")
            close_details_btn = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-engagement-panel-section-list"
                        "-renderer/div[1]/ytd-engagement-panel-title-header-renderer/div[3]/div["
                        "6]/ytd-button-renderer/yt-button-shape/button",
                    )
                )
            )
            close_details_btn.click()
        except TimeoutException:
            logging.error("Failed to close channel details popup.")

        return info

    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return None


def get_video_info(channel_name):
    stages = [
        "Starting",
        "Scrolling to find more videos",
        "Going to Video Link - {}",
        "Extracting for Video {}",
        "Getting Basic Information (Views, Likes, Uploaded Date)",
    ]
    with tqdm(total=3, desc=f"Video Info Extraction", colour="yellow") as video_pbar:
        try:
            video_pbar.set_postfix({"Process": stages[0]})
            logging.info(f"Fetching video information for channel: {channel_name}")
            contents = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.ID, "contents"))
            )
            video_pbar.update(1)

            # Scrolling logic
            video_pbar.set_postfix({"Process": stages[1]})
            try:
                logging.info("Scrolling through the page to load all videos.")
                scroll_to_bottom(driver=driver, pause_time=3, scroll_count=5)
            except Exception as e:
                logging.error(f"Scrolling failed: {e}")
            video_pbar.update(1)

            for count, content in enumerate(contents.find_elements(By.ID, "content")):
                if count == 100:
                    break
                try:
                    logging.info("Extracting video details.")
                    video_url = content.find_element(By.TAG_NAME, "a").get_attribute(
                        "href"
                    )
                    code = video_url.split("=")[-1]

                    video_pbar.set_postfix({"Process": stages[2].format(video_url)})
                    video_pbar.update(1)

                    thumbnail_url = content.find_element(
                        By.TAG_NAME, "img"
                    ).get_attribute("src")
                    title = content.find_element(By.ID, "video-title").text

                    video_pbar.set_postfix({"Process": stages[3].format(title)})
                    video_pbar.update(1)

                    video_pbar.set_postfix({"Process": stages[4]})
                    video_pbar.update(1)

                    try:
                        metadata_container = content.find_element(
                            By.ID, "metadata-line"
                        ).find_elements(By.TAG_NAME, "span")
                        views = unzip_large_nums(
                            metadata_container[0].text.split(" ")[0]
                        )
                    except NoSuchElementException:
                        logging.error(
                            "Metadata container or views information not found."
                        )
                        views = -1

                    info = {
                        "code": code,
                        "title": title,
                        "url": video_url,
                        "thumbnail_url": thumbnail_url,
                        "views": views,  # TODO Consider getting more accurate view count in video details
                    }

                    try:
                        logging.info(f"Fetching additional details for video: {code}")

                        other_info = get_video_details(code)
                        info = info | other_info
                    except Exception as e:
                        logging.error(
                            f"Failed to fetch additional video details for {code}: {e}"
                        )

                    try:
                        file_path = f"{directory}/{channel_name}/videos/{code}.json"
                        logging.info(f"Saving video info to {file_path}")
                        with open(file_path, "w") as file:
                            file.write(json.dumps(info))
                    except Exception as e:
                        logging.error(
                            f"Failed to save video information for {code}: {e}"
                        )

                except Exception as e:
                    logging.error(f"Failed to extract details for a video: {e}")

        except TimeoutException:
            logging.error("Unexpected Error - Timeout Exception while fetching videos.")


def get_video_details(code):
    video_driver = get_webdriver()

    other_info = {
        "likes": 0,
        "duration": "",
        "embed_code": f"https://www.youtube.com/embed/{code}",
        "uploaded_date": "",
        "comments_count": 0,
        "comments": [],
        "related": [],  # TODO: Implementation not done yet
        # video Link from which channel link can be extracted,
        # verification status,
        # views
    }

    try:
        video_driver.get(f"https://www.youtube.com/watch?v={code}")

        # Expand button
        try:
            logging.info("Clicking expand button to reveal more video details.")
            expand_btn = WebDriverWait(video_driver, delay).until(
                EC.presence_of_element_located((By.ID, "expand"))
            )
            expand_btn.click()
        except TimeoutException:
            logging.error("Failed to find or click the expand button.")

        # Likes
        try:
            logging.info("Fetching likes count.")
            likes = WebDriverWait(video_driver, delay).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div["
                        "2]/ytd-watch-metadata/div/div[2]/div[2]/div/div/ytd-menu-renderer/div["
                        "1]/segmented-like-dislike-button-view-model/yt-smartimation/div/div/like-button-view-model"
                        "/toggle-button-view-model/button-view-model/button/div[2]",
                    )
                )
            )
            other_info["likes"] = unzip_large_nums(
                likes.text.replace("\n", "").replace(" ", "")
            )
        except TimeoutException:
            logging.error("Failed to fetch likes count.")

        # Uploaded Date
        try:
            logging.info("Fetching uploaded date.")
            uploaded_date = WebDriverWait(video_driver, delay).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div["
                        "2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-watch-info-text/div/yt-formatted-"
                        "string/span[3]",
                    )
                )
            )
            other_info["uploaded_date"] = uploaded_date.text
        except TimeoutException:
            logging.error("Failed to fetch uploaded date.")

        scroll(video_driver, 3, 8)

        # Comments Info
        try:
            logging.info("Fetching comments count and details.")
            comments_container = WebDriverWait(video_driver, delay).until(
                EC.presence_of_element_located((By.ID, "comments"))
            )

            try:
                comments_count = (
                    comments_container.find_element(By.ID, "header")
                    .find_element(By.XPATH, '//*[@id="title"]')
                    .find_element(
                        By.XPATH, '//*[@id="count"]/yt-formatted-string/span[1]'
                    )
                )
                other_info["comments_count"] = int(comments_count.text.replace(",", ""))
            except NoSuchElementException:
                logging.error("Failed to fetch comments count.")

            comments_container_ = comments_container.find_element(By.ID, "contents")
            comments = comments_container_.find_elements(
                By.TAG_NAME, "ytd-comment-thread-renderer"
            )

            for comment in comments:
                try:
                    commenter_channel_name = (
                        comment.find_element(By.TAG_NAME, "a")
                        .get_attribute("href")
                        .split("/")[-1]
                    )
                    comment_date = comment.find_element(
                        By.ID, "published-time-text"
                    ).text
                    text = comment.find_element(By.ID, "content-text").text
                    likes = unzip_large_nums(
                        comment.find_element(By.ID, "vote-count-middle").text
                    )

                    try:
                        replies = (
                            comment.find_element(By.ID, "replies")
                            .find_element(By.TAG_NAME, "button")
                            .get_attribute("label")
                        )
                    except NoSuchElementException:
                        replies = 0

                    liked_by_creator = False
                    try:
                        creator_heart = comment.find_element(
                            By.ID, "creator-heart-button"
                        )
                        if creator_heart:
                            liked_by_creator = True
                    except NoSuchElementException:
                        pass

                    other_info["comments"].append(
                        {
                            "comment": text,
                            "commenter_channel_name": commenter_channel_name,
                            "likes": likes,
                            "date": comment_date,
                            "fetched_date": str(datetime.now()),
                            "replies_count": replies,
                            "liked_by_creator": liked_by_creator,
                        }
                    )
                except Exception as e:
                    logging.error(f"Failed to fetch comment details: {e}")
        except TimeoutException:
            logging.error("Failed to fetch comments section.")

        # Duration
        try:
            logging.info("Fetching video duration.")
            duration = WebDriverWait(video_driver, delay).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ytp-time-duration"))
            )
            d = duration.text.split(":")
            d.reverse()
            total_duration = sum(int(num) * (60**i) for i, num in enumerate(d))
            other_info["duration"] = total_duration
        except TimeoutException:
            logging.error("Failed to fetch video duration.")

        return other_info

    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return other_info

    finally:
        video_driver.quit()


def get_shorts(channel_name, s_driver=get_webdriver()):
    shorts = []

    s_driver.get(f"https://www.youtube.com/{channel_name}/shorts")

    scroll_to_bottom(s_driver, pause_time=2, scroll_count=5)

    shorts_driver = get_webdriver()
    shorts_containers = (
        WebDriverWait(driver, delay)
        .until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer/div[1]",
                )
            )
        )
        .find_element(By.ID, "contents")
        .find_elements(By.TAG_NAME, "ytd-rich-item-renderer")
    )

    for container in shorts_containers:
        short = {
            "code": "",
            "thumbnail_url": "",
            "url": "",
            "description": "",
            "likes": 0,
            "views": 0,
            "posted_date": "",
            "comments_count": 0,
            "comments": [],
        }

        thumbnail_url = container.find_element(By.TAG_NAME, "img").get_attribute("src")
        short["thumbnail_url"] = thumbnail_url
        print(thumbnail_url)

        code = (
            container.find_element(By.TAG_NAME, "a")
            .get_attribute("href")
            .split("/")[-1]
        )
        short["code"] = code
        print(code)

        url = f"https://www.youtube.com/shorts/{code}"
        short["url"] = url
        print(url)

        shorts_driver.get(url)
        WebDriverWait(shorts_driver, delay).until(
            EC.presence_of_element_located((By.ID, "short-video-container"))
        ).click()

        WebDriverWait(shorts_driver, delay).until(
            EC.presence_of_element_located((By.ID, "menu-button"))
        ).find_element(By.TAG_NAME, "button").click()

        WebDriverWait(shorts_driver, delay).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/ytd-app/ytd-popup-container/tp-yt-iron-dropdown["
                    "2]/div/ytd-menu-popup-renderer/tp-yt-paper-listbox/ytd-menu-"
                    "service-item-renderer",
                )
            )
        ).click()

        modal = WebDriverWait(shorts_driver, delay).until(
            EC.presence_of_element_located((By.ID, "anchored-panel"))
        )
        modal_items = modal.find_element(By.ID, "items")
        description = (
            modal_items.find_element(By.ID, "title")
            .find_element(By.TAG_NAME, "yt-formatted-string")
            .text
        )
        short["description"] = description

        likes = modal_items.find_element(
            By.XPATH, '//*[@id="factoids"]/factoid-renderer[1]/div/span[1]'
        )
        short["likes"] = likes

        views = modal_items.find_element(
            By.XPATH,
            '//*[@id="factoids"]/view-count-factoid-renderer/factoid-renderer/div/span[1]',
        )
        short["views"] = views

        posted_date = modal_items.find_element(
            By.XPATH, '//*[@id="factoids"]/factoid-renderer[2]/div/span[1]'
        )
        short["posted_date"] = posted_date

        modal.find_element(By.ID, "visibility-button").find_element(
            By.TAG_NAME, "button"
        ).click()

        comments_modal = WebDriverWait(shorts_driver, delay).until(
            EC.presence_of_element_located((By.ID, "anchored-panel"))
        )
        contents = comments_modal.find_element(By.ID, "content").find_element(
            By.ID, "contents"
        )

        comments_count = unzip_large_nums(contents.find_element(By.TAG_NAME, "h2").text)
        short["comments_count"] = comments_count

        counter = 0
        while counter <= 100:
            for _ in range(2):
                contents.send_keys(Keys.PAGE_DOWN)
            time.sleep(2)
            comments = contents.find_elements(
                By.TAG_NAME, "ytd-comment-thread-renderer"
            )
            counter = len(comments)
            print(counter)

        shorts_driver.quit()


def scrape_channel(channel_name):
    stages = [
        "Exploring URL",
        "Maximizing Window",
        "Setting up directories",
        "Extracting Channel Info",
        "Saving Channel Info",
        "Extracting Video Info",
        "Completed",
    ]
    with tqdm(total=3, desc=f"Channel Process", colour="green") as inner_pbar:
        try:
            inner_pbar.set_postfix({"Current Process": stages[0]})
            driver.get(f"https://www.youtube.com/{channel_name}/videos")
            inner_pbar.update(1)

            inner_pbar.set_postfix({"Current Process": stages[1]})
            driver.maximize_window()
            inner_pbar.update(1)

            inner_pbar.set_postfix({"Current Process": stages[2]})
            try:
                os.mkdir(f"{directory}/{channel_name}")
            except FileExistsError:
                logger.warning(f"Directory {channel_name} already exists!")
                pass
            inner_pbar.update(1)

            inner_pbar.set_postfix({"Current Process": stages[3]})
            info = get_channel_info()
            inner_pbar.update(1)

            inner_pbar.set_postfix({"Current Process": stages[4]})
            if info:
                with open(f"{directory}/{channel_name}/channel_info.json", "w") as file:
                    file.write(json.dumps(info))
            else:
                logger.critical(
                    f"Error while scraping channel info for channel - {channel_name}"
                )
            inner_pbar.update(1)

            try:
                os.mkdir(f"{directory}/{channel_name}/videos")
            except FileExistsError:
                logger.warning(f"Directory {channel_name}/videos already exists!")
                pass

            inner_pbar.set_postfix({"Current Process": stages[5]})
            get_video_info(channel_name)
            inner_pbar.update(1)

            inner_pbar.set_postfix({"Current Process": stages[6]})

        except Exception as e:
            logger.warning(
                f"Unknown error while scraping channel ({channel_name}) - {e}"
            )


if __name__ == "__main__":
    with tqdm(total=len(channels), desc="Processing channels") as pbar:
        for channel in channels:
            pbar.set_postfix({"Channel": channel})
            retry_scrape(channel)
            pbar.update(1)

    # get_shorts("@MrBeast")

# TODO: Check why thumbnail URLs are not getting fetched for some posts.
