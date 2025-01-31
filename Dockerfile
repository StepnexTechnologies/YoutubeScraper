FROM --platform=linux/amd64 python:3.11

# Install required dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libvulkan1 \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg --add-architecture amd64 \
    && apt-get update \
    && apt install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROME_BIN=/usr/bin/google-chrome
ENV DISPLAY=:99
ENV DATABASE__DB=youtube_scraper
ENV DATABASE__USERNAME=naad
ENV DATABASE__PASSWORD=naad@dantale123A
ENV DATABASE__HOST=postgres
ENV DATABASE__PORT=5432

CMD ["python", "db.py"]
CMD ["python", "app.py"]
