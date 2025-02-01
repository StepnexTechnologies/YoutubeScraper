import json
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, List, Any

from lib.utils import serialize_value


def get_connection_string() -> str:
    return f"dbname={os.getenv('DATABASE__DB')} user={os.getenv('DATABASE__USERNAME')} password={os.getenv('DATABASE__PASSWORD')} host={os.getenv('DATABASE__HOST')} port={os.getenv('DATABASE__PORT')}"


@contextmanager
def get_db():
    conn = psycopg2.connect(get_connection_string())
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            # Channels table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_channel (
                    id SERIAL PRIMARY KEY,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP WITH TIME ZONE DEFAULT null,
                    channel_code VARCHAR UNIQUE,
                    name VARCHAR,
                    is_verified BOOLEAN,
                    about TEXT,
                    display_picture_url TEXT,
                    banner_url TEXT,
                    subscribers INTEGER,
                    content_count INTEGER,
                    num_videos INTEGER,
                    num_shorts INTEGER,
                    views_count BIGINT,
                    joined_date TIMESTAMP WITH TIME ZONE,
                    location VARCHAR,
                    links JSONB,  -- Array of {title, url}
                    affiliated_channels JSONB,  -- Array of {name, url, code, subscribers}
                    channel_info_scraped BOOLEAN DEFAULT FALSE,
                    shorts_info_scraped BOOLEAN DEFAULT FALSE,
                    shorts_details_scraped BOOLEAN DEFAULT FALSE,
                    videos_info_scraped BOOLEAN DEFAULT FALSE,
                    videos_details_scraped BOOLEAN DEFAULT FALSE,
                    community_posts_basic_info_scraped BOOLEAN DEFAULT FALSE,
                    community_posts_details_scraped BOOLEAN DEFAULT FALSE
                );
                """
            )

            # Videos table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_videos (
                    id SERIAL PRIMARY KEY,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP WITH TIME ZONE DEFAULT null,
                    video_code VARCHAR UNIQUE,
                    channel_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    title VARCHAR,
                    description TEXT,
                    url TEXT,
                    thumbnail_url TEXT,
                    duration FLOAT,
                    embed_code TEXT,
                    uploaded_date TIMESTAMP WITH TIME ZONE,
                    views INTEGER,
                    likes INTEGER,
                    comments_count INTEGER,
                    comments_turned_off BOOLEAN DEFAULT FALSE,
                    fetched_timestamp TIMESTAMP WITH TIME ZONE,
                    hashtags JSONB,  -- Array of hashtag strings
                    transcript JSONB,  -- Array of {timestamp, text}
                    related_videos JSONB  -- Array of {code, url, thumbnail_url, title, channel_name, is_channel_verified, posted_date, duration, views}
                );
                """
            )

            # Shorts table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_shorts (
                    id SERIAL PRIMARY KEY,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP WITH TIME ZONE DEFAULT null,
                    short_code VARCHAR UNIQUE,
                    channel_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    url TEXT,
                    description TEXT,
                    secondary_description TEXT,
                    suggested_search_phrase VARCHAR,
                    thumbnail_url TEXT,
                    posted_date TIMESTAMP WITH TIME ZONE,
                    views INTEGER,
                    likes INTEGER,
                    comments_count INTEGER,
                    fetched_timestamp TIMESTAMP WITH TIME ZONE,
                    hashtags JSONB,  -- Array of hashtag strings
                    music JSONB,  -- {name, channel_name, music_url, channel_url, used_in_shorts: [{code, url, views}]}
                    effect JSONB,  -- {name, shorts_count}
                    related_shorts JSONB  -- Array of {code, url, views}
                );
                """
            )

            # Community posts table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_community_posts (
                    id SERIAL PRIMARY KEY,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP WITH TIME ZONE DEFAULT null,
                    post_code VARCHAR UNIQUE,
                    channel_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    url TEXT,
                    description TEXT,
                    post_type VARCHAR,
                    post_content JSONB,  -- Can store different types of content including polls
                    views INTEGER,
                    likes INTEGER,
                    comments_count INTEGER,
                    posted_date TIMESTAMP WITH TIME ZONE,
                    fetched_timestamp TIMESTAMP WITH TIME ZONE
                );
                """
            )

            # Comments table (unified for videos, shorts, and community posts)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_comments (
                    id SERIAL PRIMARY KEY,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP WITH TIME ZONE DEFAULT null,
                    content_type VARCHAR,  -- 'video', 'short', or 'community_post'
                    content_id INTEGER,  -- References the respective content table
                    comment TEXT,
                    commenter_channel_name VARCHAR,
                    commenter_display_picture_url TEXT,
                    likes INTEGER DEFAULT 0,
                    comment_date TIMESTAMP WITH TIME ZONE,
                    replies_count INTEGER DEFAULT 0,
                    liked_by_creator BOOLEAN DEFAULT FALSE,
                    is_pinned BOOLEAN DEFAULT FALSE
                );
                """
            )

            # Channel changes table for tracking history
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_changes (
                    id SERIAL PRIMARY KEY,
                    channel_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    field_name VARCHAR,
                    old_value TEXT,
                    new_value TEXT,
                    change_type VARCHAR,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Related Channels
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS related_profiles (
                    channel_1_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    channel_2_id INTEGER REFERENCES youtube_channel(id) ON DELETE CASCADE,
                    create_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel_1_id, channel_2_id)
                )
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE FUNCTION update_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.update_time = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE TRIGGER update_youtube_channel_timestamp
                    BEFORE UPDATE ON youtube_channel
                    FOR EACH ROW
                    EXECUTE FUNCTION update_timestamp();
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE TRIGGER update_post_timestamp
                    BEFORE UPDATE ON youtube_videos
                    FOR EACH ROW
                    EXECUTE FUNCTION update_timestamp();
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE TRIGGER update_post_timestamp
                    BEFORE UPDATE ON youtube_shorts
                    FOR EACH ROW
                    EXECUTE FUNCTION update_timestamp();
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE TRIGGER youtube_community_posts
                    BEFORE UPDATE ON youtube_videos
                    FOR EACH ROW
                    EXECUTE FUNCTION update_timestamp();
            """
            )

            cur.execute(
                """
                CREATE OR REPLACE TRIGGER youtube_comments
                    BEFORE UPDATE ON youtube_videos
                    FOR EACH ROW
                    EXECUTE FUNCTION update_timestamp();
            """
            )

            conn.commit()


def delete_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS youtube_channel CASCADE")
            cur.execute("DROP TABLE IF EXISTS youtube_videos CASCADE")
            cur.execute("DROP TABLE IF EXISTS youtube_shorts CASCADE")
            cur.execute("DROP TABLE IF EXISTS youtube_community_posts CASCADE")
            cur.execute("DROP TABLE IF EXISTS youtube_comments CASCADE")
            cur.execute("DROP TABLE IF EXISTS channel_changes CASCADE")

    print("Deleted DB")


class ChannelChangeTracker:
    @staticmethod
    def _serialize_value(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    @staticmethod
    def compare_values(old_data: Dict, new_data: Dict) -> List[Dict]:
        changes = []

        for field, new_value in new_data.items():
            old_value = old_data.get(field)
            if field in old_data:
                if old_value != new_value:
                    changes.append(
                        {
                            "field_name": field,
                            "old_value": ChannelChangeTracker._serialize_value(
                                old_value
                            ),
                            "new_value": ChannelChangeTracker._serialize_value(
                                new_value
                            ),
                            "change_type": "modified",
                        }
                    )
            else:
                changes.append(
                    {
                        "field_name": field,
                        "old_value": None,
                        "new_value": ChannelChangeTracker._serialize_value(new_value),
                        "change_type": "added",
                    }
                )

        for field in old_data:
            if field not in new_data:
                changes.append(
                    {
                        "field_name": field,
                        "old_value": ChannelChangeTracker._serialize_value(
                            old_data[field]
                        ),
                        "new_value": None,
                        "change_type": "deleted",
                    }
                )

        return changes


class YtChannelDB:
    @staticmethod
    def create(username: str) -> int:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM youtube_channel WHERE channel_code = %s",
                    (username,),
                )
                result = cur.fetchone()

                if result:
                    return result[0]
                cur.execute(
                    "INSERT INTO youtube_channel (channel_code) VALUES (%s) RETURNING id",
                    [username],
                )
                channel_id = cur.fetchone()[0]
                conn.commit()
                return channel_id

    @staticmethod
    def update(channel_code: str, update_data: Dict) -> tuple[bool, int]:
        if not update_data:
            return False, -1

        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, {} FROM youtube_channel WHERE channel_code = %s".format(
                        ", ".join(update_data.keys())  # Fetch only needed columns
                    ),
                    (channel_code,),
                )
                current_data = cur.fetchone()

                if not current_data:
                    return False, -1

                channel_id = current_data.pop("id")

                # Record changes
                changes = ChannelChangeTracker.compare_values(current_data, update_data)

                if changes:
                    change_records = [
                        (
                            channel_id,
                            c["field_name"],
                            c["old_value"],
                            c["new_value"],
                            c["change_type"],
                        )
                        for c in changes
                    ]
                    cur.executemany(
                        """
                        INSERT INTO channel_changes 
                        (channel_id, field_name, old_value, new_value, change_type)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        change_records,
                    )

                values = [serialize_value(update_data[k]) for k in update_data.keys()]
                values.append(channel_id)

                set_clause = ", ".join(f"{k} = %s" for k in update_data.keys())
                cur.execute(
                    f"UPDATE youtube_channel SET {set_clause} WHERE id = %s", values
                )

                # update channel_info_scraped in ca se of a real change
                if changes:
                    cur.execute(
                        "UPDATE youtube_channel SET channel_info_scraped = %s WHERE id = %s",
                        [True, channel_id],
                    )

                conn.commit()
                return True, channel_id

    @staticmethod
    def get_unscraped_channels(limit: int = 100) -> List[str]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, channel_code 
                    FROM youtube_channel 
                    WHERE channel_info_scraped = %s
                    AND update_time IS NULL 
                        OR update_time < NOW() - INTERVAL '24 hours'
                    ORDER BY update_time NULLS FIRST
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (False, limit),
                )
                channels = cur.fetchall()

                return [channel["channel_code"] for channel in channels]

    @staticmethod
    def get_channels() -> list:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * 
                    FROM youtube_channel 
                    """,
                )
                channels = cur.fetchall()

                return channels

    @staticmethod
    def get_channel_stats(channel_code: str) -> list:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * 
                    FROM youtube_channel 
                    WHERE channel_code = %s
                    """,
                    (channel_code,),
                )
                channel_stats = cur.fetchone()

                return channel_stats


class YtShortDB:
    @staticmethod
    def create(short_code: str, channel_id: int) -> int:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM youtube_shorts WHERE short_code = %s",
                    (short_code,),
                )
                result = cur.fetchone()

                if result:
                    return result[0]

                cur.execute(
                    "INSERT INTO youtube_shorts (short_code, channel_id) VALUES (%s, %s) RETURNING id",
                    [short_code, channel_id],
                )
                short_id = cur.fetchone()[0]
                conn.commit()
                return short_id

    @staticmethod
    def update(short_id: int, update_data: Dict) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
                values = list(update_data.values()) + [short_id]
                query = f"UPDATE youtube_shorts SET {set_clause} WHERE id = %s"
                cur.execute(query, values)
                conn.commit()
                return True

    @staticmethod
    def get_by_channel(channel_id: int) -> List[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_shorts WHERE channel_id = %s ORDER BY posted_date DESC",
                    (channel_id,),
                )
                return cur.fetchall()

    @staticmethod
    def get_by_code(short_code: str) -> Optional[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_shorts WHERE short_code = %s", (short_code,)
                )
                return cur.fetchone()


class YtVideoDB:
    @staticmethod
    def create(
        title: str, video_code: str, url: str, thumbnail_url: str, channel_id: int
    ) -> int:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM youtube_videos WHERE video_code = %s",
                    (video_code,),
                )
                result = cur.fetchone()

                if result:
                    return result[0]

                cur.execute(
                    "INSERT INTO youtube_videos (title, video_code, url, thumbnail_url, channel_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    [
                        title,
                        video_code,
                        url,
                        thumbnail_url,
                        channel_id,
                    ],
                )
                video_id = cur.fetchone()[0]
                conn.commit()
                return video_id

    @staticmethod
    def create_many(values: list[tuple], channel_id: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO youtube_videos 
                    (title, video_code, url, thumbnail_url, channel_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """,
                    values,
                )
                cur.execute(
                    f"UPDATE youtube_channel SET videos_info_scraped = %s WHERE id = %s",
                    [True, channel_id],
                )
                conn.commit()
                return True

    @staticmethod
    def update(video_id: int, update_data: Dict) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
                values = list(update_data.values()) + [video_id]
                query = f"UPDATE youtube_videos SET {set_clause} WHERE id = %s"
                cur.execute(query, values)
                conn.commit()
                return True

    @staticmethod
    def update_video_and_shorts_count(channel_id: int, num_videos: int) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE youtube_channel 
                    SET num_videos = %s
                    WHERE id = %s
                    RETURNING content_count
                """
                cur.execute(query, (num_videos, channel_id))
                content_count = cur.fetchone()[0]
                num_shorts = content_count - num_videos

                query = """
                    UPDATE youtube_channel 
                    SET num_shorts = %s
                    WHERE id = %s
                """
                cur.execute(query, (num_shorts, channel_id))

                conn.commit()
                return True

    @staticmethod
    def get_by_channel(channel_id: int) -> List[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_videos WHERE channel_id = %s ORDER BY uploaded_date DESC",
                    (channel_id,),
                )
                return cur.fetchall()

    @staticmethod
    def get_by_code(video_code: str) -> Optional[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_videos WHERE video_code = %s", (video_code,)
                )
                return cur.fetchone()


class YtCommunityPostDB:
    @staticmethod
    def create(post_code: str, channel_id: int) -> int:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM youtube_community_posts WHERE post_code = %s",
                    (post_code,),
                )
                result = cur.fetchone()

                if result:
                    return result[0]

                cur.execute(
                    "INSERT INTO youtube_community_posts (post_code, channel_id) VALUES (%s, %s) RETURNING id",
                    [post_code, channel_id],
                )
                post_id = cur.fetchone()[0]
                conn.commit()
                return post_id

    @staticmethod
    def update(post_id: int, update_data: Dict) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
                values = list(update_data.values()) + [post_id]
                query = f"UPDATE youtube_community_posts SET {set_clause} WHERE id = %s"
                cur.execute(query, values)
                conn.commit()
                return True

    @staticmethod
    def get_by_channel(channel_id: int) -> List[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_community_posts WHERE channel_id = %s ORDER BY posted_date DESC",
                    (channel_id,),
                )
                return cur.fetchall()

    @staticmethod
    def get_by_code(post_code: str) -> Optional[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM youtube_community_posts WHERE post_code = %s",
                    (post_code,),
                )
                return cur.fetchone()


class YtCommentsDB:
    @staticmethod
    def create_many(content_type: str, content_id: int, comments: List[Dict]) -> bool:
        with get_db() as conn:
            with conn.cursor() as cur:
                values = [
                    (
                        content_type,
                        content_id,
                        comment.get("comment"),
                        comment.get("commenter_channel_name"),
                        comment.get("commenter_display_picture_url"),
                        comment.get("likes", 0),
                        comment.get("comment_date"),
                        comment.get("replies_count", 0),
                        comment.get("liked_by_creator", False),
                        comment.get("is_pinned", False),
                    )
                    for comment in comments
                ]

                cur.executemany(
                    """
                    INSERT INTO youtube_comments 
                    (content_type, content_id, comment, commenter_channel_name, 
                     commenter_display_picture_url, likes, comment_date, 
                     replies_count, liked_by_creator, is_pinned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """,
                    values,
                )
                conn.commit()
                return True

    @staticmethod
    def get_by_content(content_type: str, content_id: int) -> List[Dict]:
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM youtube_comments 
                       WHERE content_type = %s AND content_id = %s
                       ORDER BY comment_date DESC""",
                    (content_type, content_id),
                )
                return cur.fetchall()


if __name__ == "__main__":
    init_db()
