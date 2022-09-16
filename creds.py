import os


class my:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    API_ID = int(os.environ["API_ID"])
    API_HASH = os.environ["API_HASH"]
    # Banned Unwanted Members..
    BANNED_USERS = set(int(x) for x in os.environ.get("BANNED_USERS","").split())
    UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "")
    LOG_GROUP = os.environ.get("LOG_GROUP", "")
