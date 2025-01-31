import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
from urllib3.exceptions import NewConnectionError

from db import YtVideoDB
from lib.errors import ScraperRuntimeError
from lib.structures import Comment, RelatedVideo, TranscriptItem
from lib.utils import (
    unzip_large_nums,
    scroll,
    video_duration_parser,
)


def get_video_info(
    driver,
    channel_name,
    channel_id,
    constants,
    logger,
    videos_db: YtVideoDB,
):
    num_videos = 0
    try:
        driver.get(constants.VIDEOS_PAGE_LINK.format(channel_name))
        driver.maximize_window()
        logger.info(f"Fetching video information for channel: {channel_name}")
        contents = WebDriverWait(driver, constants.MAX_DELAY).until(
            EC.presence_of_element_located((By.ID, "contents"))
        )

        # Scrolling logic
        try:
            logger.info("Scrolling through the page to load all videos.")

            last_height = driver.execute_script(
                "return document.documentElement.scrollHeight"
            )

            num_videos = len(contents.find_elements(By.ID, "content"))

            while num_videos < constants.VIDEOS_COUNT_BASIC_INFO:
                num_videos = len(contents.find_elements(By.ID, "content"))

                driver.execute_script(
                    "window.scrollTo(0, document.documentElement.scrollHeight);"
                )
                time.sleep(constants.SCROLL_WAIT_TIME)

                new_height = driver.execute_script(
                    "return document.documentElement.scrollHeight"
                )

                if new_height == last_height:
                    break

                last_height = new_height

            driver.execute_script("window.scrollTo(0, 0);")

        except Exception as e:
            logger.error(f"Scrolling failed: {e}")

        videos = []
        for count, content in enumerate(contents.find_elements(By.ID, "content")):
            try:
                # logger.info("Extracting video details.")
                video_url = content.find_element(By.TAG_NAME, "a").get_attribute("href")

                code = video_url.split("=")[-1]

                thumbnail_url = content.find_element(By.TAG_NAME, "img").get_attribute(
                    "src"
                )

                title = content.find_element(By.ID, "video-title").text

                videos.append(
                    (
                        title,
                        code,
                        video_url,
                        thumbnail_url,
                        channel_id,
                    )
                )

            except Exception as e:
                logger.error(f"Failed to extract details for a video: {e}")

        try:
            logger.info(f"Storing all videos basic info for channel: {channel_name}")

            videos_db.create_many(values=videos, channel_id=channel_id)
            videos_db.update_video_and_shorts_count(channel_id, num_videos)

        except Exception as e:
            logger.error(
                f"Failed to store all videos basic info for channel: {channel_name}: {e}"
            )

        return 1

    except NewConnectionError as e:
        logger.error(
            f"Connection Error, session expired, youtube invalidated this session."
        )
        raise ScraperRuntimeError(
            message="Connection Error, session expired, youtube invalidated this session",
            channel=channel_name,
        )

    except TimeoutException:
        logger.error("Unexpected Error - Timeout Exception while fetching videos.")
        return 0


def get_video_details(video_details_driver, code, constants, logger):
    other_info = {
        "description": "",
        "likes": 0,
        "duration": 0,
        "uploaded_date": "",
        "comments_count": 0,
        "transcript": [],
        "comments": [],
        "related": [],
        "sponsor_info": [],
    }

    try:
        video_details_driver.get(constants.VIDEO_PAGE_LINK.format(code))
        video_details_driver.maximize_window()

        # Expand button
        try:
            logger.info("Clicking expand button to reveal more video details.")
            expand_btn = WebDriverWait(video_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located((By.ID, "expand"))
            )
            expand_btn.click()
        except TimeoutException:
            logger.error("Failed to find or click the expand button.")

        # Description
        try:
            logger.info("Fetching Description")
            description = (
                WebDriverWait(video_details_driver, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-text-inline-expander/yt-attributed-string",
                        )
                    )
                )
                .text
            )
        except Exception:
            description = ""
        other_info["description"] = description

        try:
            WebDriverWait(video_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-text-inline-expander/div[2]/ytd-structured-description-content-renderer/div/ytd-video-description-transcript-section-renderer/div[3]/div/ytd-button-renderer/yt-button-shape/button",
                    )
                )
            ).click()
        except Exception as e:
            logger.error(
                f"Transcript Button not found, this video might not have a transcript{e}"
            )

        # Likes
        try:
            logger.info("Fetching likes count.")
            likes = WebDriverWait(video_details_driver, constants.MAX_DELAY).until(
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
            logger.error("Failed to fetch likes count.")

        # Uploaded Date
        try:
            logger.info("Fetching uploaded date.")
            uploaded_date = WebDriverWait(
                video_details_driver, constants.MAX_DELAY
            ).until(
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
            logger.error("Failed to fetch uploaded date.")

        # Transcript
        try:

            transcript_segments = WebDriverWait(
                video_details_driver, constants.MAX_DELAY
            ).until(
                EC.presence_of_all_elements_located(
                    (By.TAG_NAME, "ytd-transcript-segment-renderer")
                )
            )

            for transcript_segment in transcript_segments:
                timestamp = video_duration_parser(
                    transcript_segment.find_element(By.TAG_NAME, "div")
                    .find_element(By.TAG_NAME, "div")
                    .find_element(By.TAG_NAME, "div")
                    .text
                )
                content = (
                    transcript_segment.find_element(By.TAG_NAME, "div")
                    .find_element(By.TAG_NAME, "yt-formatted-string")
                    .text
                )
                other_info["transcript"].append(
                    TranscriptItem(timestamp=timestamp, text=content)
                )

        except TimeoutException:
            logger.error("Failed to fetch transcript")

        scroll(video_details_driver, constants.PAUSE_TIME, 8, constants.MAX_DELAY)
        # scroll(video_details_driver, constants.PAUSE_TIME, 2, constants.MAX_DELAY)

        # Comments Info
        try:
            logger.info("Fetching comments count and details.")
            comments_container = WebDriverWait(
                video_details_driver, constants.MAX_DELAY
            ).until(EC.presence_of_element_located((By.ID, "comments")))

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
                logger.error("Failed to fetch comments count.")

            comments_container_ = comments_container.find_element(By.ID, "contents")
            comments = comments_container_.find_elements(
                By.TAG_NAME, "ytd-comment-thread-renderer"
            )

            for i, comment in enumerate(comments):
                if i == constants.VIDEO_COMMENTS_COUNT:
                    break

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
                        replies_count = (
                            comment.find_element(By.ID, "replies")
                            .find_element(By.TAG_NAME, "ytd-comment-replies-renderer")
                            .find_element(By.ID, "expander")
                            .find_element(By.ID, "more-replies")
                            .find_element(By.TAG_NAME, "button")
                            .get_attribute("aria-label")
                            .split(" ")[0]
                        )
                    except Exception:
                        logger.error(
                            f"Could not find post comment replies for video {code}"
                        )
                        replies_count = 0

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
                        Comment(
                            comment=text,
                            commenter_channel_name=commenter_channel_name,
                            commenter_display_picture_url="",
                            likes=likes,
                            date=comment_date,
                            fetched_timestamp=str(datetime.now()),
                            replies_count=replies_count,
                            liked_by_creator=liked_by_creator,
                        )
                    )

                except Exception as e:
                    logger.error(f"Failed to fetch comment details: {e}")
        except TimeoutException:
            logger.error("Failed to fetch comments section.")

        # Related Videos -
        try:
            logger.info("Extracting Related Videos")

            related_videos_containers = (
                WebDriverWait(video_details_driver, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "related",
                        )
                    )
                )
                .find_elements(By.TAG_NAME, "ytd-compact-video-renderer")
            )

            print(len(list(set(related_videos_containers))))

            for video in related_videos_containers:
                video_container = video.find_element(By.ID, "dismissible")

                thumbnail_container = video_container.find_element(
                    By.TAG_NAME, "ytd-thumbnail"
                )

                a_container = thumbnail_container.find_element(By.TAG_NAME, "a")

                v_url = a_container.get_attribute("href")

                v_thumbnail_url = (
                    a_container.find_element(By.TAG_NAME, "yt-image")
                    .find_element(By.TAG_NAME, "img")
                    .get_attribute("src")
                )
                if not v_thumbnail_url:
                    v_thumbnail_url = ""

                duration_content = (
                    a_container.find_element(By.ID, "overlays")
                    .find_element(
                        By.XPATH,
                        '//*[@id="overlays"]/ytd-thumbnail-overlay-time-status-renderer/div[1]/badge-shape/div',
                    )
                    .text
                )
                v_duration = video_duration_parser(duration_content)

                if v_url != "":
                    v_code = v_url.split("=")[-1]
                else:
                    v_code = ""

                # video_info = video_container.find_element(
                #     By.TAG_NAME, "div"
                # ).find_element(By.TAG_NAME, "div")
                # meta_element = video_info.find_element(By.TAG_NAME, "a")

                video_info = video_container.find_element(
                    By.XPATH, '//*[@id="dismissible"]/div/div[1]/a'
                )

                v_title = video_info.find_element(By.TAG_NAME, "h3").text

                metadata = (
                    video_info.find_element(By.TAG_NAME, "div")
                    .find_element(By.TAG_NAME, "ytd-video-meta-block")
                    .find_element(By.ID, "metadata")
                )

                name_and_verification_element = metadata.find_element(
                    By.ID, "byline-container"
                ).find_element(By.ID, "channel-name")

                name_and_verification = (
                    name_and_verification_element.find_element(By.ID, "container")
                    .find_element(By.ID, "text-container")
                    .find_element(By.ID, "text")
                )

                v_channel_name = name_and_verification.text

                v_is_channel_verified = False
                try:
                    name_and_verification_element.find_element(
                        By.TAG_NAME, "ytd-badge-supported-renderer"
                    )
                    v_is_channel_verified = True
                except NoSuchElementException:
                    pass

                metadata_line = metadata.find_element(By.ID, "metadata-line")

                views_text = metadata_line.find_element(
                    By.XPATH, '//*[@id="metadata-line"]/span[1]'
                ).text
                if views_text == "":
                    v_views = 0
                else:
                    v_views = unzip_large_nums(views_text.split(" ")[0])

                posted_date = metadata_line.find_element(
                    By.XPATH, '//*[@id="metadata-line"]/span[2]'
                ).text

                other_info["related"].append(
                    RelatedVideo(
                        code=code,
                        url=v_url,
                        thumbnail_url=v_thumbnail_url,
                        title=v_title,
                        channel_name=v_channel_name,
                        is_channel_verified=v_is_channel_verified,
                        views=v_views,
                        posted_date=posted_date,
                        duration=v_duration,
                    )
                )
        except Exception as e:
            logger.error(f"Error while getting Related Videos Information: {e}")

        # Duration - TODO: Take duration from the videos page in every thumbnail area of a video
        try:
            logger.info("Fetching video duration.")
            duration_element = WebDriverWait(
                video_details_driver, constants.MAX_DELAY
            ).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ytp-time-duration"))
            )
            other_info["duration"] = video_duration_parser(duration_element.text)
        except TimeoutException:
            logger.error("Failed to fetch video duration.")

        return other_info

    except NewConnectionError as e:
        logger.error(
            f"Connection Error, session expired, youtube invalidated this session."
        )
        raise ScraperRuntimeError(
            message=f"Connection Error, session expired, youtube invalidated this session for "
            f"video details, link: {constants.VIDEO_PAGE_LINK.format(code)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        return other_info


# if __name__ == "__main__":
#     get_video_info(
#         get_webdriver(headless=False),
#         get_webdriver(headless=False),
#         "@tanmaybhat",
#         Constants,
#         get_logger("logs", print_to_console=True),
#     )
