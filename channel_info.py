from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from Yt.structures import ChannelInfo, Link
from utils import unzip_large_nums


def get_channel_info(driver, channel_name, constants, logger):
    info = {}

    try:
        driver.get(constants.VIDEOS_PAGE_LINK.format(channel_name))

        name = ""
        is_verified = False
        about = ""
        subscribers = 0
        videos_count = 0
        views_count = 0
        joined_date = ""
        location = ""
        links = []

        # Name and Verification Status
        try:
            logger.info("Fetching channel name and verification status.")
            name_container = (
                WebDriverWait(driver, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "dynamic-text-view-model-wiz__h1")
                    )
                )
                .find_element(By.TAG_NAME, "span")
            )
            name = name_container.text

            try:
                if name_container.find_element(By.TAG_NAME, "span"):
                    is_verified = True
            except NoSuchElementException:
                logger.info("Verification status: Not verified.")
        except TimeoutException:
            logger.error("Failed to fetch channel name and verification status.")

        # More button to get about information
        try:
            logger.info("Clicking 'More' button to fetch about info.")
            more_btn = WebDriverWait(driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "truncated-text-wiz__absolute-button")
                )
            )
            more_btn.click()

            about = WebDriverWait(driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-engagement-panel-section-list"
                        "-renderer/div[2]/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div["
                        "3]/ytd-about-channel-renderer/div/yt-attributed-string/span",
                    )
                )
            )
            about = about.text
        except TimeoutException:
            logger.error("Failed to fetch about info.")

        # Channels Links
        try:
            logger.info("Fetching channel links.")
            links_section = WebDriverWait(driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located((By.ID, "link-list-container"))
            )
            link_containers = links_section.find_elements(
                By.TAG_NAME, "yt-channel-external-link-view-model"
            )
            for link_container in link_containers:
                container = link_container.find_elements(By.TAG_NAME, "span")
                links.append(
                    Link(title=container[0].text, url=container[1].text),
                )
        except TimeoutException:
            logger.error("Failed to fetch channel links.")

        # Channel Details Section
        try:
            logger.info(
                "Fetching channel details (subscribers, videos, views, joined date)."
            )
            channel_details_section = WebDriverWait(driver, constants.MAX_DELAY).until(
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
                subscribers = unzip_large_nums(
                    rows[3].find_elements(By.TAG_NAME, "td")[1].text.split(" ")[0]
                )
            except (IndexError, ValueError):
                logger.error("Failed to fetch subscribers count.")
                subscribers = 0

            try:
                videos_count = int(
                    rows[4]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.split(" ")[0]
                    .replace(",", "")
                )
            except (IndexError, ValueError):
                logger.error("Failed to fetch videos count.")
                videos_count = 0

            try:
                views_count = int(
                    rows[5]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.split(" ")[0]
                    .replace(",", "")
                )
            except (IndexError, ValueError):
                logger.error("Failed to fetch views count.")
                views_count = 0

            try:
                joined_date = (
                    rows[6]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.replace("Joined ", "")
                )
            except (IndexError, AttributeError):
                logger.error("Failed to fetch joined date.")
                joined_date = ""

        except TimeoutException:
            logger.error("Failed to fetch channel details section.")

        # Close details button
        try:
            logger.info("Closing channel details popup.")
            close_details_btn = WebDriverWait(driver, constants.MAX_DELAY).until(
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
            logger.error("Failed to close channel details popup.")

        info = ChannelInfo(
            name=name,
            is_verified=is_verified,
            about=about,
            links=links,
            subscribers=subscribers,
            videos_count=videos_count,
            views_count=views_count,
            joined_date=joined_date,
            location=location,
        )

        return info

    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")

    except ValueError as e:
        logger.error(f"Value error: {e}")

    except NoSuchElementException as e:
        logger.error(f"No such element: {e}")

    except WebDriverException as e:
        logger.error(f"Webdriver Exception: {e}")

    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        return None

    finally:
        return info
