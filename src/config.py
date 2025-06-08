DB_FILE_PATH = "/home/seedx/pizero/data/security_camera_events.db"

# Base directory for all recorded events
THUMBNAILS_SUBDIR_NAME = "thumbnails"
VIDEOS_SUBDIR_NAME = "videos"
EVENTS_STORAGE_DIR = "/home/seedx/pizero/events"

# Specific subdirectories for videos and thumbnails
VIDEO_STORAGE_DIR = f"{EVENTS_STORAGE_DIR}/{VIDEOS_SUBDIR_NAME}"
THUMBNAILS_STORAGE_DIR = f"{EVENTS_STORAGE_DIR}/{THUMBNAILS_SUBDIR_NAME}"

# \--- User Authentication ---
USER_NAME = "seedx"  # Replace with your desired username
PASSWORD = "seedx__" # Replace with your desired password

# \--- Camera Configuration ---
CAMERA_MAIN_RESOLUTION = (800, 600)  # for recordings
CAMERA_LORES_RESOLUTION = (640, 360)   # live MJPEG stream

# \--- Telegram Bot Configuration ---
BOT_TOKEN = "7387922932:AAFnRK-jwpjBstEk0o7Ly7oIaVF43Ms3XEU"

# The chat ID you want the bot to send messages and videos to
CHAT_ID = "6568247351"

# \--- Sensor Configuration ---
PIR_PIN_BCM = 23
