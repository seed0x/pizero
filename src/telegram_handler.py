import requests
import subprocess
import os
from config import CHAT_ID, BOT_TOKEN

class notiManager:
    
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.chat_id = CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    
    # Function to send message on Telegram
    def send_telegram_message(self, message):
        
        if not self.bot_token or not self.chat_id:
            print("Telegram not configured. Cannot send message.")
            return
        print(f"Sending Telegram message: {message}")
        url = f"{self.base_url}/sendMessage"    
        data = {"chat_id": self.chat_id, "text": message}
        try:
            response = requests.post(url, data=data, timeout=10)            
        except requests.exceptions.RequestException as e:
            print(f"Error sending Telegram message: {e}")

    # Function to send video on Telegram
    def send_telegram_video(self, video_path):
        
        if not self.bot_token or not self.chat_id:
            print("Telegram not configured. Cannot send message.")
            return
       
        print(f"Sending video to Telegram: {video_path}")
        url = f"{self.base_url}/sendVideo" 
        try:
            with open(video_path, "rb") as video_file:
                data = {"chat_id": self.chat_id}
                files = {"video": video_file}
                requests.post(url, data=data, files=files)
        except Exception:
            print(f"Error sending Telegram video:")

    # Convert h264 to mp4 for telegram
    def convert_video_to_mp4(self, video_path):
        print(f"Converting video to MP4: {video_path}")
        
        mp4_file = video_path.replace(".h264", ".mp4")
        command = ["ffmpeg", "-i", video_path, "-c:v", "copy", mp4_file]
        try:
            subprocess.run(command, check=True)
            return mp4_file
        except FileNotFoundError:
            print("Error: 'ffmpeg' command not found. Please ensure it is installed.")
            return None    