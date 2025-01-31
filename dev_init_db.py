from db import delete_db, init_db, YtChannelDB

if __name__ == "__main__":
    delete_db()
    init_db()

    channel_db = YtChannelDB()

    # with open("channel_names.txt", "r") as file:
    with open("example_channel_names.txt", "r") as file:
        for channel_name in file.readlines():
            channel_db.create(channel_name.strip())
            print(channel_name.strip())
