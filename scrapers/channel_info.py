from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from lib.structures import ChannelInfo, Link, AffiliatedChannel
from lib.utils import unzip_large_nums, save_img_from_url


def get_channel_info(driver, channel_name, constants, logger, channel_db):
    stored = False
    channel_id = -1

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
        banner_url = ""
        dp_url = ""
        affiliated_channels = []

        # Banner and DP URL
        try:
            logger.info("Fetching banner url")
            banner_url = (
                WebDriverWait(driver, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located((By.ID, "page-header-banner-sizer"))
                )
                .find_element(By.TAG_NAME, "yt-image-banner-view-model")
                .find_element(By.TAG_NAME, "img")
                .get_attribute("src")
            )
        except Exception as e:
            logger.error(f"Failed to fetch banner url: {e}")

        try:
            logger.info("Fetching dp url")
            dp_url = (
                WebDriverWait(driver, constants.MAX_DELAY)
                .until(EC.presence_of_element_located((By.ID, "page-header")))
                .find_element(By.TAG_NAME, "yt-page-header-renderer")
                .find_element(By.TAG_NAME, "yt-page-header-view-model")
                .find_element(By.TAG_NAME, "yt-avatar-shape")
                .find_element(By.TAG_NAME, "img")
                .get_attribute("src")
            )
        except Exception as e:
            logger.error(f"Failed to fetch dp url: {e}")

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
                try:
                    container = link_container.find_elements(By.TAG_NAME, "span")
                    links.append(
                        Link(title=container[0].text, url=container[1].text),
                    )
                except Exception as e:
                    logger.error(
                        f"Problem with fetching one particular link for channel: {channel_name}: {str(e)}"
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

            for row in rows:
                try:
                    row.find_element(By.ID, "view-email-button-container")
                    continue
                except:
                    text = row.find_elements(By.TAG_NAME, "td")[1].text
                    if "subscribers" in text:
                        try:
                            subscribers = unzip_large_nums(text.split(" ")[0])
                        except Exception as e:
                            logger.error(f"Failed to fetch subscribers: {e}")
                    elif "videos" in text:
                        try:
                            videos_count = int(text.split(" ")[0].replace(",", ""))
                        except Exception as e:
                            logger.error(f"Failed to fetch videos count: {e}")
                    elif "views" in text:
                        try:
                            views_count = int(text.split(" ")[0].replace(",", ""))
                        except Exception as e:
                            logger.error(f"Failed to fetch views count: {e}")
                    elif "Joined" in text:
                        try:
                            joined_date = text.replace("Joined", "")
                        except Exception as e:
                            logger.error(f"Failed to fetch joined date: {e}")
                    elif "Phone verified" in text:
                        continue
                    else:
                        try:
                            location = text
                        except Exception as e:
                            logger.error(f"Failed to fetch location: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch channel details: {e}")

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
        except Exception as e:
            logger.error(f"Failed to close channel details popup: {e}")

        # # Affiliated Channels
        # try:
        #     try:
        #         items_container = (
        #             WebDriverWait(driver, constants.MAX_DELAY)
        #             .until(
        #                 EC.presence_of_element_located(
        #                     (
        #                         By.TAG_NAME,
        #                         "ytd-apps",
        #                     )
        #                 )
        #             )
        #             .find_element(By.ID, "content")
        #             .find_element(By.TAG_NAME, "page-manager")
        #             .find_element(By.TAG_NAME, "ytd-browse")
        #             .find_element(By.TAG_NAME, "ytd-two-column-browse-results-renderer")
        #             .find_element(By.ID, "primary")
        #             .find_element(By.TAG_NAME, "ytd-section-list-renderer")
        #             .find_element(By.ID, "contents")
        #             .find_elements(By.TAG_NAME, "ytd-item-section-renderer")[-1]
        #             .find_element(By.ID, "contents")
        #             .find_element(By.ID, "dismissible")
        #             .find_element(By.ID, "contents")
        #             .find_element(By.TAG_NAME, "yt-horizontal-list-renderer")
        #             .find_element(By.ID, "scroll-outer-container")
        #             .find_element(By.ID, "scroll-container")
        #             .find_element(By.ID, "items")
        #         )
        #     except Exception as e:
        #         logger.error(f"Failed to find the items_container: {e}")
        #
        #     affiliated_channels_containers = items_container.find_elements(
        #         By.TAG_NAME, "ytd-grid-channel-renderer"
        #     )
        #
        #     affiliated_channels = []
        #     for container in affiliated_channels_containers:
        #         try:
        #             channel = container.find_element(By.ID, "channel").find_element(
        #                 By.ID, "channel_info"
        #             )
        #             channel_url = channel.get_attribute("href")
        #             channel_code = channel_url.split("/")[-1]
        #
        #             title = channel.find_element(By.XPATH, '//*[@id="title"]')
        #             channel_subscribers = unzip_large_nums(
        #                 channel.find_element(
        #                     By.XPATH, '//*[@id="thumbnail-attribution"]'
        #                 ).text.split(" ")[0]
        #             )
        #             affiliated_channels.append(
        #                 AffiliatedChannel(
        #                     name=title,
        #                     url=channel_url,
        #                     code=channel_code,
        #                     subscribers=channel_subscribers,
        #                 )
        #             )
        #         except Exception as e:
        #             logger.error(
        #                 f"Failed to find the affiliated channels container: {e}"
        #             )
        #
        # except Exception as e:
        #     logger.error(f"Failed to fetch affiliated channels: {e}")

        info = ChannelInfo(
            channel_code=channel_name,
            name=name,
            is_verified=is_verified,
            about=about,
            links=links,
            display_picture_url=dp_url,
            banner_url=banner_url,
            affiliated_channels=affiliated_channels,
            subscribers=subscribers,
            content_count=videos_count,
            num_videos=0,
            num_shorts=0,
            views_count=views_count,
            joined_date=joined_date,
            location=location,
        )

        stored, channel_id = channel_db.update(channel_name, info.dict())

        save_img_from_url(constants.BANNER_PATH.format(channel_id), banner_url, logger)
        save_img_from_url(constants.DP_PATH.format(channel_id), dp_url, logger)

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

    finally:
        return stored, channel_id
