class Constants:
    MAX_DELAY = 8
    MAX_WORKERS = 2

    DATA_DIRECTORY = "data"
    VIDEOS_DIRECTORY = "videos"
    SHORTS_DIRECTORY = "shorts"

    # VIDEOS_COUNT = 100
    # VIDEO_COMMENTS_COUNT = 100
    # SHORTS_COMMENTS_COUNT = 20
    # SHORTS_COUNT = 100

    VIDEOS_COUNT = 10
    VIDEO_COMMENTS_COUNT = 10
    SHORTS_COMMENTS_COUNT = 20
    SHORTS_COUNT = 10

    MAX_RETRY_COUNT = 2

    # Links
    VIDEOS_PAGE_LINK = "https://www.youtube.com/{}/videos"
    VIDEO_PAGE_LINK = "https://www.youtube.com/watch?v={}"
    SHORTS_PAGE_LINK = "https://www.youtube.com/shorts/{}"
    COMMUNITY_POSTS_PAGE_LINK = "https://www.youtube.com/{}/community"
    LIVE_STREAMS_PAGE_LINK = "https://www.youtube.com/{}/streams"
    EMBED_LINK = "https://www.youtube.com/embed/{}"

    # Important Log Messages

    # INFO
    STARTING_SCRAPE_FOR_CHANNEL = "Starting scrape for channel: {}"
    SUCCESSFULLY_SCRAPED_CHANNEL = "Successfully scraped channel: {}"

    # WARNING
    ERROR_SCRAPING_CHANNEL = "Error scraping {0}: {1}. Retrying..."

    # ERROR
    FAILED_TO_SCRAPE_CHANNEL = "Failed to scrape channel after {0} attempts: {1}"
