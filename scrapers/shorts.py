import time
from datetime import date

from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from lib.constants import Constants
from lib.structures import ShortInfo, Comment, ShortMusic, Link, ShortEffect
from lib.utils import scroll_to_bottom, get_webdriver, unzip_large_nums, get_logger, save_to_json


def get_shorts(
    channel_name, shorts_info_driver, shorts_details_driver, constants, logger
):
    try:
        shorts_info_driver.get(f"{constants.SHORTS_PAGE_LINK.format(channel_name)}")
        shorts_info_driver.maximize_window()

        scroll_to_bottom(shorts_info_driver, pause_time=1.5, scroll_count=5)

        shorts_containers = (
            WebDriverWait(shorts_info_driver, constants.MAX_DELAY)
            .until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer"
                        "/div[1]",
                    )
                )
            )
            .find_element(By.ID, "contents")
            .find_elements(By.TAG_NAME, "ytd-rich-item-renderer")
        )

        for i, container in enumerate(shorts_containers):

            if i == constants.SHORTS_COUNT:
                break

            # Thumbnail Url
            thumbnail_url = (
                WebDriverWait(container, constants.MAX_DELAY)
                .until(EC.presence_of_element_located((By.TAG_NAME, "img")))
                .get_attribute("src")
            )

            if not thumbnail_url:
                logger.warning("Thumbnail not found, setting None")
                thumbnail_url = ""

            # Code
            code = (
                container.find_element(By.TAG_NAME, "a")
                .get_attribute("href")
                .split("/")[-1]
            )

            # Short URL
            url = f"https://www.youtube.com/shorts/{code}"

            shorts_details_driver.get(url)
            shorts_details_driver.maximize_window()
            time.sleep(1)

            # Pause Video to control network usage
            WebDriverWait(shorts_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located((By.ID, "short-video-container"))
            ).click()

            # Navigate to Shorts Description
            WebDriverWait(shorts_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located((By.ID, "menu-button"))
            ).find_element(By.TAG_NAME, "ytd-menu-renderer").find_element(
                By.ID, "button-shape"
            ).find_element(
                By.TAG_NAME, "button"
            ).click()

            WebDriverWait(shorts_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/ytd-popup-container/tp-yt-iron-dropdown/div/ytd-menu-popup-renderer/tp-yt"
                        "-paper-listbox/ytd-menu-service-item-renderer[1]/tp-yt-paper-item",
                    )
                )
            ).click()

            modal_items = WebDriverWait(
                shorts_details_driver, constants.MAX_DELAY
            ).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="anchored-panel"]//*[@id="items"]')
                )
            )

            description = (
                WebDriverWait(modal_items, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (By.XPATH, './/*[@id="title"]//yt-formatted-string')
                    )
                )
                .text
            )

            likes_element = WebDriverWait(modal_items, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="factoids"]/factoid-renderer[1]/div/span[1]')
                )
            )

            likes = unzip_large_nums(likes_element.text)

            try:
                views = int(
                    WebDriverWait(modal_items, constants.MAX_DELAY)
                    .until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                '//*[@id="factoids"]/view-count-factoid-renderer/factoid-renderer/div/span[1]',
                            )
                        )
                    )
                    .text.replace(",", "")
                )
            except ValueError:
                logger.warning("Couldn't find views count: Setting Views to 0")
                views = 0

            posted_date = (
                WebDriverWait(modal_items, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            '//*[@id="factoids"]/factoid-renderer[2]/div/span[1]',
                        )
                    )
                )
                .text
            )

            # Open comments
            WebDriverWait(shorts_details_driver, constants.MAX_DELAY).until(
                EC.presence_of_element_located((By.ID, "comments-button"))
            ).find_element(By.TAG_NAME, "ytd-button-renderer").find_element(
                By.TAG_NAME, "yt-button-shape"
            ).find_element(
                By.TAG_NAME, "button"
            ).click()

            comments_modal = WebDriverWait(
                shorts_details_driver, constants.MAX_DELAY
            ).until(EC.presence_of_element_located((By.ID, "anchored-panel")))

            contents = WebDriverWait(comments_modal, constants.MAX_DELAY).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="content"]//*[@id="contents"]')
                )
            )

            comments_count = unzip_large_nums(
                WebDriverWait(comments_modal, constants.MAX_DELAY)
                .until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="header"]//*[@id="contextual-info"]')
                    )
                )
                .text
            )

            # # Modified scrolling logic
            # comments_section = contents.find_element(By.TAG_NAME, "ytd-comments")

            # # Wait for comments to load
            # time.sleep(2)

            # counter = 0
            # last_comment_count = 0
            # no_new_comments_count = 0
            # comments = []

            # while counter < 100 and no_new_comments_count < 3:
            #     # Scroll using JavaScript
            #     shorts_details_driver.execute_script(
            #         "arguments[0].scrollTop = arguments[0].scrollHeight", comments_section
            #     )
            #
            #     # Wait for potential new comments to load
            #     time.sleep(2)
            #
            #     # Get current comments
            #     comments = contents.find_elements(
            #         By.TAG_NAME, "ytd-comment-thread-renderer"
            #     )
            #     counter = len(comments)
            #
            #     # Check if we're still loading new comments
            #     if counter == last_comment_count:
            #         no_new_comments_count += 1
            #     else:
            #         no_new_comments_count = 0
            #         last_comment_count = counter
            #
            #     print(f"Current comment count: {counter}")

            comments = WebDriverWait(contents, constants.MAX_DELAY).until(
                EC.presence_of_all_elements_located(
                    (By.TAG_NAME, "ytd-comment-thread-renderer")
                )
            )

            comments_list = []
            for j, comment in enumerate(comments):
                if j == constants.SHORTS_COMMENTS_COUNT:
                    break

                comment_body = comment.find_element(By.ID, "comment").find_element(
                    By.ID, "body"
                )
                comment_main = comment_body.find_element(By.ID, "main")

                commenter_channel_name = (
                    comment_main.find_element(By.ID, "header")
                    .find_element(By.ID, "header-author")
                    .find_element(By.TAG_NAME, "h3")
                    .text
                )

                d = (
                    comment_main.find_element(By.ID, "header")
                    .find_element(By.ID, "header-author")
                    .find_element(By.ID, "published-time-text")
                    .find_element(By.TAG_NAME, "a")
                )
                # short_video_code = d.get_attribute("href")
                # print("hello")
                # print(short_video_code)

                comment_date = d.text

                fetched_date = str(date.today())

                description = (
                    comment_main.find_element(By.ID, "expander")
                    .find_element(By.ID, "content")
                    .find_element(By.ID, "content-text")
                    .text
                )

                try:
                    likes_element = (
                        comment_main.find_element(By.ID, "action-buttons")
                        .find_element(By.ID, "toolbar")
                        .find_element(By.ID, "vote-count-middle")
                    )
                    likes = unzip_large_nums(likes_element.text)
                except (NoSuchElementException, IndexError):
                    likes = 0

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
                except NoSuchElementException:
                    replies_count = 0

                comments_list.append(
                    Comment(
                        commenter_channel_name=commenter_channel_name,
                        comment=description,
                        likes=likes,
                        date=comment_date,
                        fetched_date=fetched_date,
                        replies_count=replies_count,
                        liked_by_creator=False,  # TODO: Not Implemented yet
                    )
                )
            s = ShortInfo(
                code=code,
                url=url,
                thumbnail_url=thumbnail_url,
                description=description,
                secondary_description="",  # TODO: Not Implemented yet
                hashtags=[],  # TODO: Not Implemented yet
                music=ShortMusic(
                    name="",
                    channel_name="",
                    music_url="",
                    channel_url="",
                    used_in_shorts=[],
                ),  # TODO: Not Implemented yet
                effect=ShortEffect(
                    name="", shorts_count=0
                ),  # TODO: Not Implemented yet
                related_shorts=[],  # TODO: Not Implemented yet
                suggested_search_phrase="",  # TODO: Not Implemented yet
                link=Link(title="", url=""),  # TODO: Not Implemented yet
                likes=likes,
                views=views,
                posted_date=posted_date,
                comments_count=comments_count,
                pinned_comments=[],
                comments=comments_list,
            )
            save_to_json(f"{constants.DATA_DIRECTORY}/{channel_name}/{constants.SHORTS_DIRECTORY}/{code}.json", s.model_dump_json())

    except TimeoutError as te:
        logger.error(f"Timeout error: {te}")

    except ValueError as ve:
        logger.error(f"Value error: {ve}")

    except NoSuchElementException as nse:
        logger.error(f"No such element: {nse}")

    except WebDriverException as wde:
        logger.error(f"Webdriver Exception: {wde}")


if __name__ == "__main__":
    channel = "@MrBeast"
    get_shorts(
        channel,
        get_webdriver(),
        get_webdriver(),
        Constants(),
        get_logger("logs/test_runs"),
    )
