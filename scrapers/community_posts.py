from datetime import datetime
from typing import List

from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from lib.constants import Constants
from lib.structures import (
    CommunityPost,
    CommunityPostType,
    PollTypePost,
    VideoTypePost,
    PollOption,
    Comment,
)
from lib.utils import (
    unzip_large_nums,
    scroll,
    save_to_json,
    video_duration_parser,
    get_webdriver,
    get_logger,
    extract_hashtags,
)


def get_community_posts(
    channel_name, comments_driver, community_posts_driver, constants, logger
):
    try:
        logger.info(f"Getting Community Posts for {channel_name}")
        community_posts_driver.get(
            constants.COMMUNITY_POSTS_PAGE_LINK.format(channel_name)
        )
        community_posts_driver.maximize_window()

        def get_posts():
            main_content = WebDriverWait(
                community_posts_driver, constants.MAX_DELAY
            ).until(EC.presence_of_element_located((By.ID, "content")))

            posts_container = (
                WebDriverWait(main_content, constants.MAX_DELAY)
                .until(EC.presence_of_element_located((By.ID, "page-manager")))
                .find_element(By.ID, "primary")
                .find_element(By.TAG_NAME, "ytd-section-list-renderer")
                .find_element(By.ID, "contents")
                .find_element(By.ID, "contents")
            )

            p = posts_container.find_elements(
                By.TAG_NAME, "ytd-backstage-post-thread-renderer"
            )
            return p

        current_posts_count = len(get_posts())
        while current_posts_count < constants.COMMUNITY_POSTS_COUNT:
            scroll(
                community_posts_driver,
                2,
                1,
                constants.MAX_DELAY,
            )
            new_posts_count = len(get_posts())
            if new_posts_count == current_posts_count:
                break
            current_posts_count = new_posts_count

        posts = get_posts()

        for i, post_element in enumerate(posts):
            if i == constants.COMMUNITY_POSTS_COUNT:
                break

            main_area = (
                post_element.find_element(By.ID, "post")
                .find_element(By.ID, "body")
                .find_element(By.ID, "main")
            )

            header_element = (
                main_area.find_element(By.ID, "header")
                .find_element(By.ID, "video-time-text")
                .find_element(By.TAG_NAME, "a")
            )

            # Post URL
            url = header_element.get_attribute("href")

            posted_date_element = main_area.find_element(By.ID, "header").find_element(
                By.TAG_NAME, "yt-formatted-string"
            )

            # Post Date
            posted_date = posted_date_element.text

            # Post Code
            code = header_element.get_attribute("href").split("/")[-1]

            content_expander = main_area.find_element(By.ID, "contentTextExpander")

            # Description
            description = (
                content_expander.find_element(By.ID, "content")
                .find_element(By.ID, "content-text")
                .text
            )

            toolbar = main_area.find_element(By.ID, "toolbar")

            # Likes
            likes_content = toolbar.find_element(By.ID, "vote-count-middle").text
            if likes_content == "":
                likes = 0
            else:
                likes = unzip_large_nums(likes_content)

            # Post Type
            post_type = get_post_type(main_area)

            # Post Content
            post_content = get_post_content(main_area, post_type, logger, url)

            # Post Comments
            comments_count, comments = get_comments(
                comments_driver, code, constants, logger
            )

            # Final Step
            post = CommunityPost(
                code=code,
                url=url,
                description=description,
                hashtags=extract_hashtags(description),
                post_type=post_type,
                post_content=post_content,
                likes=likes,
                comments_count=comments_count,
                comments=comments,
                posted_date=posted_date,
                fetched_timestamp=str(datetime.now()),
            )

            save_to_json(
                f"{constants.DATA_DIRECTORY}/{channel_name}/{constants.COMMUNITY_POSTS_DIRECTORY}/{code}.json",
                post.model_dump_json(indent=4),
            )

    except TimeoutError as te:
        logger.error(f"Timeout error: {te}")

    except ValueError as ve:
        logger.error(f"Value error: {ve}")

    except NoSuchElementException as nse:
        logger.error(f"No such element: {nse}")

    except WebDriverException as wde:
        logger.error(f"Webdriver Exception: {wde}")


def get_post_content(
    main_area: WebElement, post_type: CommunityPostType, logger, post_url
) -> str | List[str] | PollTypePost | VideoTypePost | None:
    try:
        content_attachment = main_area.find_element(By.ID, "content-attachment")
        if post_type == CommunityPostType.IMAGE:
            img_url = (
                content_attachment.find_element(
                    By.TAG_NAME, "ytd-backstage-image-renderer"
                )
                .find_element(By.TAG_NAME, "a")
                .find_element(By.ID, "image-container")
                .find_element(By.TAG_NAME, "yt-img-shadow")
                .find_element(By.TAG_NAME, "img")
                .get_attribute("src")
            )
            if img_url:
                return img_url

        elif post_type == CommunityPostType.IMAGE_CAROUSEL:
            carousel = (
                content_attachment.find_element(
                    By.TAG_NAME, "ytd-post-multi-image-renderer"
                )
                .find_element(By.ID, "shelf-container")
                .find_element(By.ID, "scroll-container")
                .find_element(By.ID, "items")
                .find_elements(By.TAG_NAME, "ytd-backstage-image-renderer")
            )

            img_urls = []
            for img in carousel:
                img_url = (
                    img.find_element(By.TAG_NAME, "a")
                    .find_element(By.ID, "image-container")
                    .find_element(By.TAG_NAME, "img")
                    .get_attribute("src")
                )
                if img_url:
                    img_urls.append(img_url)

            return img_urls

        elif post_type == CommunityPostType.VIDEO:
            video_container = content_attachment.find_element(
                By.TAG_NAME, "ytd-video-renderer"
            ).find_element(By.ID, "dismissible")

            thumbnail_container = video_container.find_element(
                By.TAG_NAME, "ytd-thumbnail"
            )

            a_container = thumbnail_container.find_element(By.TAG_NAME, "a")

            url = a_container.get_attribute("href")

            thumbnail_url = (
                a_container.find_element(By.TAG_NAME, "yt-image")
                .find_element(By.TAG_NAME, "img")
                .get_attribute("src")
            )
            if not thumbnail_url:
                thumbnail_url = ""

            duration_content = (
                a_container.find_element(By.ID, "overlays")
                .find_element(
                    By.XPATH,
                    '//*[@id="overlays"]/ytd-thumbnail-overlay-time-status-renderer/div[1]/badge-shape/div',
                )
                .text
            )
            duration = video_duration_parser(duration_content)

            if url != "":
                code = url.split("=")[-1]
            else:
                code = ""

            video_info = video_container.find_element(By.TAG_NAME, "div")
            meta_element = video_info.find_element(By.XPATH, '//*[@id="meta"]')
            title = (
                meta_element.find_element(By.ID, "title-wrapper")
                .find_element(By.TAG_NAME, "h3")
                .text
            )
            metadata = meta_element.find_element(
                By.TAG_NAME, "ytd-video-meta-block"
            ).find_element(By.ID, "metadata")

            name_and_verification_element = metadata.find_element(
                By.ID, "byline-container"
            ).find_element(By.ID, "channel-name")

            name_and_verification = (
                name_and_verification_element.find_element(By.ID, "container")
                .find_element(By.ID, "text-container")
                .find_element(By.ID, "text")
                .find_element(By.TAG_NAME, "a")
            )

            channel_name = name_and_verification.text
            channel_url = name_and_verification.get_attribute("href")

            try:
                name_and_verification_element.find_element(
                    By.TAG_NAME, "ytd-badge-supported-renderer"
                )
                is_channel_verified = True
            except NoSuchElementException:
                is_channel_verified = False

            metadata_line = metadata.find_element(By.ID, "metadata-line")

            views_text = metadata_line.find_element(
                By.XPATH, '//*[@id="metadata-line"]/span[1]'
            ).text
            if views_text == "":
                views = 0
            else:
                views = unzip_large_nums(views_text.split(" ")[0])

            posted_date = metadata_line.find_element(
                By.XPATH, '//*[@id="metadata-line"]/span[2]'
            ).text

            try:
                description = video_info.find_element(
                    By.TAG_NAME, "yt-formatted-string"
                ).text
            except NoSuchElementException:
                description = ""

            return VideoTypePost(
                title=title,
                url=url,
                thumbnail_url=thumbnail_url,
                channel_url=channel_url,
                channel_name=channel_name,
                is_channel_verified=is_channel_verified,
                code=code,
                description=description,
                views=views,
                posted_date=posted_date,
                fetched_timestamp=str(datetime.now()),
                duration=duration,
            )

        elif post_type == CommunityPostType.POLL:
            poll_content = main_area.find_element(
                By.TAG_NAME, "ytd-backstage-poll-renderer"
            )
            votes_count_element = poll_content.find_element(By.ID, "vote-info").text
            if votes_count_element == "":
                votes_count = 0
            else:
                votes_count = unzip_large_nums(votes_count_element)

            votes_options = poll_content.find_element(
                By.ID, "poll-votes"
            ).find_elements(By.ID, "sign-in")

            options = []
            for option_element in votes_options:
                try:
                    description = option_element.find_element(
                        By.XPATH,
                        '//*[@id="sign-in"]/tp-yt-paper-item/div/div[1]/yt-formatted-string[1]',
                    ).text
                except NoSuchElementException:
                    description = ""

                try:
                    img_url = option_element.find_element(
                        By.XPATH, '//*[@id="sign-in"]/tp-yt-paper-item/img'
                    ).get_attribute("src")
                except NoSuchElementException:
                    img_url = ""

                options.append(PollOption(description=description, img_url=img_url))

            return PollTypePost(votes_count=votes_count, options=options)

        else:
            return None

    except Exception as e:
        logger.error(f"Error While getting post content for post - {post_url}: {e}")
        return None


def get_comments(comments_driver, code, constants, logger) -> (int, List[Comment]):
    comments = []
    comments_count = 0
    try:
        comments_driver.get(constants.COMMUNITY_POST_PAGE_LINK.format(code))

        scroll(
            comments_driver,
            2,
            constants.COMMUNITY_POSTS_COMMENTS_COUNT
            // constants.COMMUNITY_POSTS_COMMENTS_PER_PAGE
            + 1,
            constants.MAX_DELAY,
        )

        # Comments Count
        comments_count_element = (
            WebDriverWait(comments_driver, constants.MAX_DELAY)
            .until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer/div[1]/ytd-section-list-renderer/div[2]/ytd-comments/ytd-item-section-renderer/div[1]/ytd-comments-header-renderer/div[1]/div[1]/h2/yt-formatted-string",
                    )
                )
            )
            .text
        )

        if comments_count_element != "":
            comments_count = int(comments_count_element.split(" ")[0].replace(",", ""))

        # Comments
        comment_containers_element = WebDriverWait(
            comments_driver, comments_count
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-two-column-browse-results-renderer/div[1]/ytd-section-list-renderer/div[2]/ytd-comments/ytd-item-section-renderer/div[3]",
                )
            )
        )
        comment_containers = comment_containers_element.find_elements(
            By.TAG_NAME, "ytd-comment-thread-renderer"
        )

        for i, comment_container in enumerate(comment_containers):
            if i == constants.COMMUNITY_POSTS_COMMENTS_COUNT:
                break

            dp_element = (
                comment_container.find_element(By.ID, "body")
                .find_element(By.ID, "author-thumbnail")
                .find_element(By.TAG_NAME, "a")
                .find_element(By.TAG_NAME, "yt-img-shadow")
                .find_element(By.TAG_NAME, "img")
            )

            commenter_dp_url = dp_element.get_attribute("src")

            commenter_channel_name = (
                comment_container.find_element(By.TAG_NAME, "a")
                .get_attribute("href")
                .split("/")[-1]
            )
            comment_date = comment_container.find_element(
                By.ID, "published-time-text"
            ).text
            text = comment_container.find_element(By.ID, "content-text").text
            likes = unzip_large_nums(
                comment_container.find_element(By.ID, "vote-count-middle").text
            )

            try:
                replies_count = (
                    comment_container.find_element(By.ID, "replies")
                    .find_element(By.TAG_NAME, "ytd-comment-replies-renderer")
                    .find_element(By.ID, "expander")
                    .find_element(By.ID, "more-replies")
                    .find_element(By.TAG_NAME, "button")
                    .get_attribute("aria-label")
                    .split(" ")[0]
                )
            except Exception:
                logger.error(f"Could not find post comment replies for post {code}")
                replies_count = 0

            liked_by_creator = False
            try:
                creator_heart = comment_container.find_element(
                    By.ID, "creator-heart-button"
                )
                if creator_heart:
                    liked_by_creator = True
            except NoSuchElementException:
                pass

            comment = Comment(
                comment=text,
                commenter_channel_name=commenter_channel_name,
                commenter_display_picture_url=commenter_dp_url,
                likes=likes,
                date=comment_date,
                replies_count=replies_count,
                liked_by_creator=liked_by_creator,
            )

            comments.append(comment)

    except TimeoutError as te:
        logger.error(f"Timeout error while getting community post comments: {te}")

    except ValueError as ve:
        logger.error(f"Value error while getting community post comments: {ve}")

    except NoSuchElementException as nse:
        logger.error(f"No such element while getting community post comments: {nse}")

    except WebDriverException as wde:
        logger.error(
            f"Webdriver Exception while getting community post comments: {wde}"
        )

    except Exception as e:
        logger.error(f"Unknown Exception while getting community post comments: {e}")

    finally:
        return comments_count, comments


def get_post_type(main_area: WebElement) -> CommunityPostType:
    #     # Conditionally rendered if type is a video, an image or a carousel of images
    #     # ytd-post-multi-image-renderer ✅
    #     # ytd-backstage-image-renderer ✅
    #     # ytd-video-renderer ✅
    #
    #     # Already Present in the DOM
    #     # ytd-backstage-poll-renderer ✅
    #     # ytd-post-uploaded-video-renderer ❌

    content_attachment = main_area.find_element(By.ID, "content-attachment")

    if content_attachment:
        renderers = [
            ("ytd-post-multi-image-renderer", CommunityPostType.IMAGE_CAROUSEL),
            ("ytd-backstage-image-renderer", CommunityPostType.IMAGE),
            ("ytd-video-renderer", CommunityPostType.VIDEO),
        ]
        for renderer_id, post_type in renderers:
            try:
                if content_attachment.find_element(By.TAG_NAME, renderer_id):
                    return post_type
            except NoSuchElementException:
                continue

    try:
        poll_element_content = main_area.find_element(
            By.TAG_NAME, "ytd-backstage-poll-renderer"
        ).find_elements(By.XPATH, "./*")
        if len(poll_element_content) > 0:
            return CommunityPostType.POLL
    except NoSuchElementException:
        pass

    return CommunityPostType.OTHER


if __name__ == "__main__":
    get_community_posts(
        "@tanmaybhat",
        get_webdriver(),
        get_webdriver(headless=False),
        Constants,
        get_logger("logs"),
    )
