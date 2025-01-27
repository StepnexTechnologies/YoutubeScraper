class Constants:
    MAX_DELAY = 8

    MAX_WORKERS = 1
    """
    Minimum Drivers required to run a step of scraping for each channel is 2
    (per worker so if MAX_WORKERS = 2, this number will be 4) so recommended
    number of workers is > 2 per worker, (optimum number is 4-5 depending upon system
    specs - headless mode requires lower overhead)
    """
    MAX_DRIVERS = MAX_WORKERS * 2 + 1  # + 1 just in case

    DATA_DIRECTORY = "data"
    LOGS_DIRECTORY = "logs"
    INFO_FILE_NAME = "channel_info.json"
    VIDEOS_DIRECTORY = "videos"
    SHORTS_DIRECTORY = "shorts"
    COMMUNITY_POSTS_DIRECTORY = "community_posts"
    LIVE_STREAMS_DIRECTORY = "live_streams"
    METADATA_FILE_NAME = "metadata.json"

    VIDEOS_COUNT = 100
    VIDEO_COMMENTS_COUNT = 100
    VIDEO_COMMENTS_PER_PAGE = 20
    SHORTS_COMMENTS_COUNT = 100
    SHORTS_COMMENTS_PER_PAGE = 20
    SHORTS_COUNT = 100
    COMMUNITY_POSTS_COUNT = 100
    COMMUNITY_POSTS_PER_PAGE = 10
    COMMUNITY_POSTS_COMMENTS_COUNT = 100
    COMMUNITY_POSTS_COMMENTS_PER_PAGE = 20

    # VIDEOS_COUNT = 10
    # VIDEO_COMMENTS_COUNT = 10
    # VIDEO_COMMENTS_PER_PAGE = 20
    # SHORTS_COMMENTS_COUNT = 20
    # SHORTS_COMMENTS_PER_PAGE = 20
    # SHORTS_COUNT = 10
    # COMMUNITY_POSTS_COUNT = 20
    # COMMUNITY_POSTS_PER_PAGE = 10
    # COMMUNITY_POSTS_COMMENTS_COUNT = 20
    # COMMUNITY_POSTS_COMMENTS_PER_PAGE = 20

    MAX_RETRY_COUNT = 2

    # Links
    VIDEOS_PAGE_LINK = "https://www.youtube.com/{}/videos"
    VIDEO_PAGE_LINK = "https://www.youtube.com/watch?v={}"
    SHORTS_PAGE_LINK = "https://www.youtube.com/{}/shorts"
    COMMUNITY_POSTS_PAGE_LINK = "https://www.youtube.com/{}/community"
    COMMUNITY_POST_PAGE_LINK = "https://www.youtube.com/post/{}"
    LIVE_STREAMS_PAGE_LINK = "https://www.youtube.com/{}/streams"
    EMBED_LINK = "https://www.youtube.com/embed/{}"

    # Trending Algo
    TRENDING_DAYS_THRESHOLD = 3
    TRENDING_VIEWS_THRESHOLD = 100000
    TRENDING_LIKES_THRESHOLD = 10000
    TRENDING_COMMENTS_THRESHOLD = 1000
