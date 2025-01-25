import os
import json
import time
import logging
from tqdm import tqdm
from datetime import date

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

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()

channels = [
    # "@MrBeast",
    # "@PewDiePie",
    # "@TSeries",
    # "@Cocomelon",
    # "@SETIndia",
    # "@5MinuteCrafts",
    "@DudePerfect",
    "@VladandNiki",
    "@LikeNastya",
    "@Markiplier",
    # "@JamesCharles",
    # "@EmmaChamberlain",
    # "@casey",
    # "@Kurzgesagt",
    # "@HowToBasic",
    # "@MKBHD",
    # "@LinusTechTips",
    # "@TheEllenShow",
    # "@Shane",
    # "@Smosh",
    # "@Nigahiga",
    # "@JennaMarbles",
    # "@LillySingh",
    # "@Zoella",
    # "@DavidDobrik",
    # "@JakePaul",
    # "@LoganPaul",
    # "@RhettandLink",
    # "@TheTryGuys",
    # "@PhilipDeFranco",
    # "@FitnessBlender",
    # "@MichellePhan",
    # "@Vsauce",
    # "@Veritasium",
    # "@CGPGrey",
    # "@TEDxTalks",
    # "@Numberphile",
    # "@MinutePhysics",
    # "@CrashCourse",
    # "@ScienceChannel",
    # "@AsapSCIENCE",
    # "@NationalGeographic",
    # "@DiscoveryChannel",
    # "@BraveWilderness",
    # "@BrightSide",
    # "@TechLinked",
    # "@UnboxTherapy",
    # "@DaveLee",
    # "@AustinEvans",
    # "@LinusTechTips",
    # "@JerryRigEverything",
    # "@SuperSaf",
    # "@TheVerge",
    # "@TheLateShow",
    # "@JimmyKimmelLive",
    # "@TheTonightShow",
    # "@LateNightSeth",
    # "@Netflix",
    # "@HBO",
    # "@PrimeVideo",
    # "@GameTheory",
    # "@MatPatGT",
    # "@FilmTheory",
    # "@ScreenJunkies",
    # "@CinemaSins",
    # "@PitchMeeting",
    # "@ScreenRant",
    # "@WatchMojo",
    # "@Top10s",
    # "@EpicMealTime",
    # "@BingingWithBabish",
    # "@SortedFood",
    # "@Tasty",
    # "@BonAppetit",
    # "@GordonRamsay",
    # "@JoshuaWeissman",
    # "@AlmazanKitchen",
    # "@RosannaPansino",
    # "@JamieOliver",
    # "@BuzzFeed",
    # "@Cut",
    # "@Jubilee",
    # "@YesTheory",
    # "@BeastReacts",
    # "@MrBeastGaming",
    # "@Dream",
    # "@GeorgeNotFound",
    # "@Sapnap",
    # "@Technoblade",
    # "@TommyInnit",
    # "@WilburSoot",
    # "@Tubbo",
    # "@Ranboo",
    # "@Stampylonghead",
    # "@DanTDM",
    # "@PopularMMOs",
    # "@Jacksepticeye",
    # "@Ninja",
    # "@Shroud",
    # "@Pokimane",
]

delay = 10
# directory = "data"
directory = "temp_data"


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


def retry_scrape(channel_name, retries=3):
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


def scroll_to_bottom(
    pause_time, scroll_count
):  # TODO: Fix(Remove Scroll count since this is scroll to bottom)
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


def scroll(pause_time, scroll_count):
    for _ in range(scroll_count):
        for _ in range(2):
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
            "location": "",  # Some have some don't # TODO: Not implemented yet
        },
    }

    try:
        # Name and Verification Status
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

        # More button to get about information
        more_btn = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "truncated-text-wiz__absolute-button")
            )
        )
        more_btn.click()

        # About Info
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

        # Channels Links
        links_section = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.ID, "link-list-container"))
        )
        link_containers = links_section.find_elements(
            By.TAG_NAME, "yt-channel-external-link-view-model"
        )
        for link_container in link_containers:
            container = link_container.find_elements(By.TAG_NAME, "span")
            info["links"].append({"title": container[0].text, "url": container[1].text})

        # Channel Details Section
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
        info["channel_details"]["subscribers"] = unzip_large_nums(
            rows[3].find_elements(By.TAG_NAME, "td")[1].text.split(" ")[0]
        )
        info["channel_details"]["videos_count"] = int(
            (rows[4].find_elements(By.TAG_NAME, "td")[1])
            .text.split(" ")[0]
            .replace(",", "")
        )
        info["channel_details"]["views_count"] = int(
            (rows[5].find_elements(By.TAG_NAME, "td")[1])
            .text.split(" ")[0]
            .replace(",", "")
        )
        info["channel_details"]["joined_date"] = (
            rows[6].find_elements(By.TAG_NAME, "td")[1].text.replace("Joined ", "")
        )

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

        return info

    except TimeoutException:
        print("Unexpected Error - Timeout Exception!")
        return None


def get_video_info(channel_name):
    try:
        contents = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.ID, "contents"))
        )

        # Scrolling logic
        scroll_to_bottom(pause_time=3, scroll_count=5)

        for content in contents.find_elements(By.ID, "content"):
            video_url = content.find_element(By.TAG_NAME, "a").get_attribute("href")
            code = video_url.split("=")[-1]
            thumbnail_url = content.find_element(By.TAG_NAME, "img").get_attribute(
                "src"
            )
            title = content.find_element(By.ID, "video-title").text

            metadata_container = content.find_element(
                By.ID, "metadata-line"
            ).find_elements(By.TAG_NAME, "span")
            views = unzip_large_nums(metadata_container[0].text.split(" ")[0])

            info = {
                "code": code,
                "title": title,
                "url": video_url,
                "thumbnail_url": thumbnail_url,
                "views": views,  # TODO Consider getting more accurate view count in video details
            }

            other_info = get_video_details(code)
            info = info | other_info

            with open(f"{directory}/{channel_name}/videos/{code}.json", "w") as file:
                file.write(json.dumps(info))

    except TimeoutException:
        print("Unexpected Error - Timeout Exception!")


def get_video_details(code):
    other_info = {
        "likes": -1,
        "duration": "",
        "embed_code": f"https://www.youtube.com/embed/{code}",
        "uploaded_date": "",
        "comments_count": -1,
        "comments": [],
        "related": [],  # TODO: Not implemented yet
        # video Link from which channel link can be extracted,
        # verification status,
        # views
    }

    try:
        driver.get(f"https://www.youtube.com/watch?v={code}")
        expand_btn = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.ID, "expand"))
        )
        expand_btn.click()

        # Likes
        likes = WebDriverWait(driver, delay).until(
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
        # print(likes.text.replace("\n", "").replace(" ", ""))
        other_info["likes"] = unzip_large_nums(
            likes.text.replace("\n", "").replace(" ", "")
        )

        # Uploaded Date
        uploaded_date = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div["
                    "2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-watch-info-text/div/yt-formatted-string/span[3]",
                )
            )
        )
        other_info["uploaded_date"] = uploaded_date.text

        # scroll logic
        scroll(2, 6)

        # Comments Info
        comments_container = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.ID, "comments"))
        )

        comments_count = (
            comments_container.find_element(By.ID, "header")
            .find_element(By.XPATH, '//*[@id="title"]')
            .find_element(By.XPATH, '//*[@id="count"]/yt-formatted-string/span[1]')
        )
        other_info["comments_count"] = int(comments_count.text.replace(",", ""))

        comments_container_ = comments_container.find_element(By.ID, "contents")

        comments = comments_container_.find_elements(
            By.TAG_NAME, "ytd-comment-thread-renderer"
        )

        for comment in comments:
            commenter_channel_name = (
                comment.find_element(By.TAG_NAME, "a")
                .get_attribute("href")
                .split("/")[-1]
            )

            comment_date = comment.find_element(By.ID, "published-time-text").text

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
                creator_heart = comment.find_element(By.ID, "creator-heart-button")
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
                    "fetched_date": date.today().isoformat(),
                    "replies_count": replies,
                    "liked_by_creator": liked_by_creator,
                }
            )
        # print(other_info["comments"])
        # print(len(other_info["comments"]))

        # Related Info and Channel Discovery

        # Check if advertisement still going on
        advertisement_container = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "video-ads ytp-ad-module"))
        )

        # Skip the Advertisement
        while True:
            if len(advertisement_container.find_elements(By.TAG_NAME, "div")) == 0:
                break
            print("Advertisement Detected!")

            while True:
                try:
                    skip_button = advertisement_container.find_element(
                        By.ID, "ytp-skip-ad-button"
                    )
                    skip_button.click()
                    print("Advertisement Skipped!")
                    break
                except Exception:
                    time.sleep(5)
        # TODO: Not sure if this will work for multiple ads

        # Duration
        duration = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ytp-time-duration"))
        )
        d = duration.text.split(":")
        d.reverse()
        total_duration = 0
        for i, num in enumerate(d):
            total_duration += int(num) * (60**i)

        other_info["duration"] = total_duration
        # pprint(other_info)

        return other_info

    except TimeoutException:
        print("Unexpected Error - Timeout Exception!")
        return other_info


def scrape_channel(channel_name):
    try:
        driver.get(f"https://www.youtube.com/{channel_name}/videos")
        driver.maximize_window()
        try:
            os.mkdir(f"{directory}/{channel_name}")
        except FileExistsError:
            # print(f"Directory {channel_name} already exists!")
            pass

        info = get_channel_info()
        # pprint(info)

        if info:
            with open(f"{directory}/{channel_name}/channel_info.json", "w") as file:
                file.write(json.dumps(info))
        else:
            print(f"Error while scraping channel info for channel - {channel_name}")

        try:
            os.mkdir(f"{directory}/{channel_name}/videos")
        except FileExistsError:
            # print(f"Directory {channel_name}/videos already exists!")
            pass

        get_video_info(channel_name)

    except Exception as e:
        print(f"Unknown error while scraping channel ({channel_name}) - {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    with tqdm(total=len(channels), desc="Processing channels") as pbar:
        for channel in channels:
            pbar.set_postfix({"Channel": channel})
            retry_scrape(channel)
            pbar.update(1)

    # get_video_details("0BjlBnfHcHM")
    # get_video_details("zzwRbKI2pn4")

# TODO: Check why thumbnail URLs are not getting fetched for some posts.
