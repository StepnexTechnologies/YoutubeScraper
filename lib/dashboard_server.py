import os
import threading
from flask import Flask, render_template_string, send_from_directory
from logging import Logger

from db import YtChannelDB


class DashboardServer:
    def __init__(self, logger: Logger, port: int):
        self.port = port
        self.app = Flask(__name__)
        self.logger = logger
        self.server_thread = None
        self.running = False
        # self.banner_image_path = "content/banners"
        self.dp_image_path = "content/display_pictures"
        self.banner_image_path = os.path.join(os.getcwd(), "content", "banners")
        # self.dp_image_path = os.path.join(os.getcwd(), "content", "display_pictures")

        self.channels_db = YtChannelDB()

        # Define CSS styles
        self.styles = """
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Roboto', sans-serif;
                line-height: 1.6;
                background-color: #f9fafb;
            }

            .navbar {
                background-color: #1e2a47;
                color: white;
                padding: 1.2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: 0;
                z-index: 1000;
            }

            .nav-brand {
                font-size: 1.8rem;
                font-weight: 600;
            }

            .nav-link {
                color: white;
                text-decoration: none;
                font-size: 1.2rem;
                margin-left: 1.5rem;
            }

            .nav-link:hover {
                text-decoration: underline;
            }

            .container {
                max-width: 1200px;
                margin: 2rem auto;
                padding: 0 1rem;
            }

            .search-container {
                text-align: center;
                margin-bottom: 2rem;
            }

            .search-input {
                width: 100%;
                max-width: 500px;
                padding: 0.8rem 2rem 0.8rem 1rem;
                font-size: 1rem;
                border: 2px solid #ddd;
                border-radius: 25px;
                outline: none;
                transition: border-color 0.3s ease;
            }

            .search-input:focus {
                border-color: #007bff;
            }

            .channel-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 1.5rem;
            }

            .channel-card {
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                text-decoration: none;
                color: #333;
                transition: transform 0.2s ease, box-shadow 0.3s ease;
            }

            .channel-card:hover {
                transform: translateY(-10px);
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
            }

            .card-content h3 {
                margin-bottom: 1rem;
                color: #2c3e50;
                font-size: 1.6rem;
                font-weight: 500;
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }

            .stat-card {
                background-color: #fff;
                padding: 1.5rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s ease;
            }

            .stat-card:hover {
                transform: translateY(-5px);
            }

            .stat-value {
                font-size: 1.5rem;
                font-weight: bold;
                color: #2c3e50;
                margin-top: 0.5rem;
            }

            .about-section {
                background-color: #fff;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                margin-top: 2rem;
            }

            .links-section {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-top: 1rem;
            }

            .link-item {
                background-color: #f8f9fa;
                padding: 0.5rem 1rem;
                border-radius: 25px;
                text-decoration: none;
                color: #007bff;
                font-size: 1.2rem;
            }

            .link-item:hover {
                background-color: #e7efff;
            }
        """

        self.setup_endpoints()

    def get_home_template(self):
        return (
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Youtube Scraper Dashboard</title>
                <style>
                """
            + self.styles
            + """
                </style>
            </head>
            <body>
                <nav class="navbar">
                    <div class="nav-brand">Channel Dashboard</div>
                    <a href="/" class="nav-link">Home</a>
                </nav>
                <main class="container">
                    <div class="search-container">
                        <input type="text" id="channelSearch" placeholder="Search channels..." class="search-input">
                    </div>

                    <div class="channel-grid">
                        {% for channel in channels %}
                        <a href="/channel_stats/{{ channel.channel_code }}" class="channel-card">
                            <div class="card-content">
                                <h3>{{ channel.channel_code }}</h3>
                                <p>Subscribers: {{ channel.subscribers }}</p>
                                <p>Views: {{ channel.views_count }}</p>
                                <p>Content: {{ channel.content_count }}</p>
                            </div>
                        </a>
                        {% endfor %}
                    </div>
                </main>
            </body>
            </html>
        """
        )

    def get_channel_template(self):
        return (
            """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{{ stats.name }} - Channel Stats</title>
                    <style>
                    """
            + self.styles
            + """
                .channel-header {
                    display: flex;
                    align-items: center;
                    gap: 2rem;
                    margin-bottom: 2rem;
                }
                .channel-avatar {
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    object-fit: cover;
                }
                .channel-banner {
                    width: 100%;
                    height: 200px;
                    object-fit: cover;
                    border-radius: 8px;
                    margin-bottom: 2rem;
                }
                .channel-title {
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }
                .verified-badge {
                    color: #2196F3;
                    font-size: 1.2rem;
                }
                .meta-info {
                    color: #666;
                    font-size: 0.9rem;
                    margin-top: 0.5rem;
                }
                .about-section {
                    margin: 2rem 0;
                    padding: 1.5rem;
                    background: white;
                    border-radius: 8px;
                }
                .links-section {
                    display: flex;
                    gap: 1rem;
                    flex-wrap: wrap;
                    margin-top: 1rem;
                }
                .link-item {
                    background: #f0f0f0;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    text-decoration: none;
                    color: #333;
                }
                </style>
            </head>
            <body>
                <nav class="navbar">
                    <div class="nav-brand">Channel Dashboard</div>
                    <a href="/" class="nav-link">Home</a>
                </nav>
                <main class="container">
                    <img src="{{ url_for('get_banner_image', channel_id=stats.id) }}" alt="Channel Banner" class="channel-banner">

                    <div class="channel-header">
                        <img src="{{ url_for('get_dp_image', channel_id=stats.id) }}" alt="Channel Avatar" class="channel-avatar">
                        <div>
                            <div class="channel-title">
                                <h1>{{ stats.name }}</h1>
                                {% if stats.is_verified %}
                                <span class="verified-badge">✓</span>
                                {% endif %}
                            </div>
                            <div class="meta-info">
                                <p>Channel Code: {{ stats.channel_code }}</p>
                                {% if stats.location %}
                                <p>Location: {{ stats.location }}</p>
                                {% endif %}
                                <p>Joined: {{ stats.joined_date.strftime('%B %Y') if stats.joined_date else 'Unknown' }}</p>
                            </div>
                        </div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Subscribers</h3>
                            <p class="stat-value">{{ "{:,}".format(stats.subscribers) }}</p>
                        </div>
                        <div class="stat-card">
                            <h3>Total Views</h3>
                            <p class="stat-value">{{ "{:,}".format(stats.views_count) }}</p>
                        </div>
                        <div class="stat-card">
                            <h3>Videos</h3>
                            <p class="stat-value">{{ "{:,}".format(stats.num_videos) }}</p>
                        </div>
                        <div class="stat-card">
                            <h3>Shorts</h3>
                            <p class="stat-value">{{ "{:,}".format(stats.num_shorts) }}</p>
                        </div>
                        <div class="stat-card">
                            <h3>Total Content</h3>
                            <p class="stat-value">{{ "{:,}".format(stats.content_count) }}</p>
                        </div>
                    </div>

                    {% if stats.about %}
                    <div class="about-section">
                        <h2>About</h2>
                        <p>{{ stats.about }}</p>
                    </div>
                    {% endif %}

                    {% if stats.links %}
                    <div class="about-section">
                        <h2>Links</h2>
                        <div class="links-section">
                            {% for link in stats.links %}
                            <a href="{{ link.url }}" target="_blank" class="link-item">{{ link.title }}</a>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}

                    {% if stats.affiliated_channels %}
                    <div class="about-section">
                        <h2>Affiliated Channels</h2>
                        <div class="channel-grid">
                            {% for channel in stats.affiliated_channels %}
                            <a href="/channel_stats/{{ channel.code }}" class="channel-card">
                                <div class="card-content">
                                    <h3>{{ channel.name }}</h3>
                                    <p>Subscribers: {{ "{:,}".format(channel.subscribers) }}</p>
                                </div>
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                </main>
            </body>
            </html>
        """
        )

    def setup_endpoints(self):
        @self.app.route("/", methods=["GET"])
        def home():
            channels = self.channels_db.get_channels()
            template = self.get_home_template()
            return render_template_string(template, channels=channels)

        @self.app.route("/channel_stats/<channel_code>", methods=["GET"])
        def channel_stats(channel_code):
            stats = self.channels_db.get_channel_stats(channel_code)
            template = self.get_channel_template()
            return render_template_string(template, stats=stats)

        @self.app.route("/content/banners/<channel_id>.jpg")
        def get_banner_image(channel_id):
            return send_from_directory(self.banner_image_path, f"{channel_id}.jpg")

        @self.app.route("/content/display_pictures/<channel_id>.jpg")
        def get_dp_image(channel_id):
            return send_from_directory(self.dp_image_path, f"{channel_id}.jpg")

    def start(self):
        def run_dashboard_server():
            self.app.run(
                host="0.0.0.0", port=self.port, use_reloader=False, threaded=True
            )

        self.running = True
        self.server_thread = threading.Thread(
            target=run_dashboard_server, name="dashboard-server", daemon=True
        )
        self.server_thread.start()
        self.logger.info(f"Dashboard server started on port {self.port}")

    def stop(self):
        self.running = False
        if self.server_thread:
            self.server_thread.join()
