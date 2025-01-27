from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
from urllib3.exceptions import NewConnectionError

from lib.constants import Constants
from lib.errors import ScraperRuntimeError
from lib.structures import VideoInfo, Comment
from lib.utils import (
    scroll_to_bottom,
    unzip_large_nums,
    get_webdriver,
    scroll,
    get_logger,
    video_duration_parser,
)


def get_video_info(
    videos_info_driver, videos_details_driver, channel_name, constants, logger
):
    try:
        videos_info_driver.get(constants.VIDEOS_PAGE_LINK.format(channel_name))
        logger.info(f"Fetching video information for channel: {channel_name}")
        contents = WebDriverWait(videos_info_driver, constants.MAX_DELAY).until(
            EC.presence_of_element_located((By.ID, "contents"))
        )

        # Scrolling logic
        try:
            logger.info("Scrolling through the page to load all videos.")
            scroll_to_bottom(driver=videos_info_driver, pause_time=3, scroll_count=5)
        except Exception as e:
            logger.error(f"Scrolling failed: {e}")

        for count, content in enumerate(contents.find_elements(By.ID, "content")):
            if count == constants.VIDEOS_COUNT:
                break

            # video_info = {}
            code = ""
            url = ""
            title = ""
            thumbnail_url = ""
            views = 0

            try:
                logger.info("Extracting video details.")
                video_url = content.find_element(By.TAG_NAME, "a").get_attribute("href")

                code = video_url.split("=")[-1]

                thumbnail_url = content.find_element(By.TAG_NAME, "img").get_attribute(
                    "src"
                )

                title = content.find_element(By.ID, "video-title").text

                try:
                    metadata_container = content.find_element(
                        By.ID, "metadata-line"
                    ).find_elements(By.TAG_NAME, "span")
                    views = unzip_large_nums(metadata_container[0].text.split(" ")[0])
                except NoSuchElementException:
                    logger.error("Metadata container or views information not found.")

                # TODO Consider getting more accurate view count in video details

                try:
                    logger.info(f"Fetching additional details for video: {code}")

                    video_details = get_video_details(
                        videos_details_driver, code, constants, logger
                    )

                    video_info = VideoInfo(
                        code=code,
                        title=title,
                        url=url,
                        thumbnail_url=thumbnail_url,
                        views=views,
                        likes=video_details["likes"],
                        duration=video_details["duration"],
                        embed_code=video_details["embed_code"],
                        uploaded_date=video_details["uploaded_date"],
                        comments_count=video_details["comments_count"],
                        comments_turned_off=False,  # TODO: Not Implemented yet
                        comments=video_details["comments"],
                        related=[],  # TODO: Not Implemented yet
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to fetch additional video details for {code}: {e}"
                    )

                try:
                    file_path = f"{constants.DATA_DIRECTORY}/{channel_name}/{constants.VIDEOS_DIRECTORY}/{code}.json"
                    logger.info(f"Saving video info to {file_path}")
                    with open(file_path, "w") as file:
                        file.write(video_info.model_dump_json(indent=4))
                except Exception as e:
                    logger.error(f"Failed to save video information for {code}: {e}")

            except Exception as e:
                logger.error(f"Failed to extract details for a video: {e}")
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
        "likes": 0,
        "duration": "",
        "embed_code": f"https://www.youtube.com/embed/{code}",
        "uploaded_date": "",
        "comments_count": 0,
        "comments": [],
        "related": [],  # TODO: Implementation not done yet
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

        scroll(video_details_driver, 3, 8, constants.MAX_DELAY)

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


if __name__ == "__main__":
    get_video_info(
        get_webdriver(),
        get_webdriver(),
        "@MrBeast",
        Constants,
        get_logger("logs/videos_test_runs"),
    )
