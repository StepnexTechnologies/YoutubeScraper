from datetime import datetime


def is_short_trending(
    views: int, likes: int, comments: int, uploaded_date: datetime, constants
) -> bool:
    age = (datetime.now() - uploaded_date).days
    if (
        age <= constants.TRENDING_DAYS_THRESHOLD_SHORT
        and views >= constants.TRENDING_VIEWS_THRESHOLD_SHORT
        and likes >= constants.TRENDING_LIKES_THRESHOLD_SHORT
        and comments >= constants.TRENDING_COMMENTS_THRESHOLD_SHORT
    ):
        return True
    return False


def is_video_trending(
    views: int, likes: int, comments: int, uploaded_date: datetime, constants
) -> bool:
    age = (datetime.now() - uploaded_date).days
    if (
        age <= constants.TRENDING_DAYS_THRESHOLD_VIDEO
        and views >= constants.TRENDING_VIEWS_THRESHOLD_VIDEO
        and likes >= constants.TRENDING_LIKES_THRESHOLD_VIDEO
        and comments >= constants.TRENDING_COMMENTS_THRESHOLD_VIDEO
    ):
        return True
    return False


def is_community_post_trending(
    views: int, likes: int, comments: int, uploaded_date: str, constants
) -> bool:
    if "day" in uploaded_date:
        days = int(uploaded_date.split(" ")[0])
        if (
            days <= constants.TRENDING_DAYS_THRESHOLD
            and views >= constants.TRENDING_VIEWS_THRESHOLD
            and likes >= constants.TRENDING_LIKES_THRESHOLD
            and comments >= constants.TRENDING_COMMENTS_THRESHOLD
        ):
            return True
    return False
