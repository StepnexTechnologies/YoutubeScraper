from prometheus_client import Counter, Histogram, Gauge


class Constants:
    MAX_DELAY = 8

    MAX_WORKERS = 4

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

    # Criteria for a channel to be scrapable
    MIN_SUBS = 10000

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
    PAUSE_TIME = 2

    # Links
    VIDEOS_PAGE_LINK = "https://www.youtube.com/{}/videos"
    VIDEO_PAGE_LINK = "https://www.youtube.com/watch?v={}"
    SHORTS_PAGE_LINK = "https://www.youtube.com/{}/shorts"
    COMMUNITY_POSTS_PAGE_LINK = "https://www.youtube.com/{}/community"
    COMMUNITY_POST_PAGE_LINK = "https://www.youtube.com/post/{}"
    LIVE_STREAMS_PAGE_LINK = "https://www.youtube.com/{}/streams"
    EMBED_LINK = "https://www.youtube.com/embed/{}"

    METRICS_PORT = 5001

    CHANNEL_SCRAPES = Counter(
        "channel_scrapes_total",
        "Total number of channel scraping attempts",
        ["status", "type"],
    )

    SCRAPE_DURATION = Histogram(
        "scrape_duration_seconds",
        "Time spent scraping channels",
        buckets=[10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    )

    TOTAL_SCRAPE_DURATION = Counter(
        "total_scrape_duration",
        "Total time taken for scraping",
        ["status", "type"],
    )

    ACTIVE_SCRAPES = Gauge(
        "active_scrapes", "Number of currently active scraping operations"
    )

    JOBS_PROCESSED = Counter(
        "jobs_processed_total", "Total number of jobs processed", ["status"]
    )

    QUEUE_SIZE = Gauge("job_queue_size", "Current number of jobs in queue")

    # Trending Algo
    TRENDING_DAYS_THRESHOLD = 3
    TRENDING_VIEWS_THRESHOLD = 100000
    TRENDING_LIKES_THRESHOLD = 10000
    TRENDING_COMMENTS_THRESHOLD = 1000
