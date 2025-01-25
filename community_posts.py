import time
from datetime import date
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constants import Constants
from structures import (
    CommunityPost,
    CommunityInfo,
    CommunityPostType,
    VoteTypePost,
    QuizTypePost,
    Comment,
)
from utils import scroll_to_bottom, get_webdriver, unzip_large_nums


def get_community_posts(channel_name, driver, constants):
    pass
