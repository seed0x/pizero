import os
import time
import threading
import io
import subprocess # For calling ffmpeg
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from libcamera import controls, Transform # Import Transform if you use it for flipping
from telegram_handler import notiManager
from myEventDataBase import record_new_video_event
from config import (
    CAMERA_MAIN_RESOLUTION,
    CAMERA_LORES_RESOLUTION,
    EVENTS_STORAGE_DIR,       # e.g., "/home/seedx/Zeroapp/data/events"
    THUMBNAILS_SUBDIR_NAME,   # e.g., "thumbnails"
    VIDEOS_SUBDIR_NAME   
)

# --- Ensure base directories exist ---
VIDEO_FILES_DIR = os.path.join(EVENTS_STORAGE_DIR, VIDEOS_SUBDIR_NAME)
THUMBNAIL_FILES_DIR = os.path.join(EVENTS_STORAGE_DIR, THUMBNAILS_SUBDIR_NAME)
# ---

def generate_thumbnail(mp4_filepath, output_dir=THUMBNAIL_FILES_DIR, seek_time="00:00:01", width=320):
    
    #Generates a thumbnail from an MP4 video file using ffmpeg.    
    if not os.path.exists(mp4_filepath):
        print(f"Error generating thumbnail: Video file not found at {mp4_filepath}")
        return None

    base_filename = os.path.basename(mp4_filepath)
    thumbnail_filename = os.path.splitext(base_filename)[0] + "_thumb.jpg"
    thumbnail_fullpath = os.path.join(output_dir, thumbnail_filename)

    os.makedirs(output_dir, exist_ok=True)

    command = [
        'ffmpeg', '-y', # Overwrite output files without asking
        '-i', mp4_filepath,
        '-ss', seek_time,
        '-vframes', '1',
        '-vf', f'scale={width}:-1', # Scale to width, maintain aspect ratio
        thumbnail_fullpath
    ]
    try:
        print(f"Generating thumbnail: {' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode == 0:
            print(f"Thumbnail generated successfully: {thumbnail_fullpath}")
            return thumbnail_fullpath
        else:
            print(f"Error generating thumbnail for {mp4_filepath}.")
            print(f"FFmpeg stdout: {result.stdout.decode(errors='ignore')}")
            print(f"FFmpeg stderr: {result.stderr.decode(errors='ignore')}")
            return None   
    except Exception as e:
        print(f"An unexpected error occurred during thumbnail generation: {e}")
        return None


class CameraManager:
    def __init__(self):
        self.picam2 = None
        self.camera_lock = threading.Lock()        
        self.stream_active = False
        self.stream_event = threading.Event()
        self.noti = notiManager() # Initialize your notification manager
        #self.jpeg_quality = 90  # Default JPEG quality for streams/snapshots from lores                                     

    def setup_camera(self):
        with self.camera_lock:
            if self.picam2 is None:
                print("Initializing camera...")
                self.picam2 = Picamera2()               

                # Configuration for main (recording) and lores (MJPEG stream)
                video_config = self.picam2.create_video_configuration(
                    main={"size": CAMERA_MAIN_RESOLUTION, "format": "XRGB8888"}, # XRGB8888 for H.264 encoder
                    lores={"size": CAMERA_LORES_RESOLUTION, "format": "YUV420"}  # YUV420 is good for MJPEG
                )
                self.picam2.configure(video_config)                
                self.picam2.start() # Start the camera
                print("Picamera2 started.")

                # Attempt autofocus for IMX708
                try:       
                    self.picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfTrigger": controls.AfTriggerEnum.Start})
                    
                    # Allow some time for continuous AF to settle, or after triggering Auto.
                    time.sleep(2) 
                    print("Autofocus mode set/triggered.")
                except Exception as af_e:
                    print(f"Could not set autofocus (ensure camera supports it & libcamera is up to date): {af_e}")

                print("Camera initialized and setup complete.")
            else:
                print("Camera already initialized.")
        return self.picam2

    def record_motion_video(self):
        if self.picam2 is None:
            print("Camera not set up. Attempting setup...")
            if self.setup_camera() is None:
                print("Failed to setup camera for recording.")
                return None
        
        current_time_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S") # More sortable format       
        h264_filename = f"event_{current_time_for_filename}.h264"
        h264_full_path = os.path.join(VIDEO_FILES_DIR, h264_filename)
        mp4_full_path = None
        generated_thumbnail_path = None
        
        # Ensure the target directory exists
        os.makedirs(VIDEO_FILES_DIR, exist_ok=True)
        
        #print(f"Motion detected! Recording video to {h264_full_path}...")
        
        with self.camera_lock: # Ensure exclusive camera access for recording configuration
            try:
                
                encoder = H264Encoder()
                output = FileOutput(h264_full_path)
                self.picam2.start_encoder(encoder, output)
                print(f"Recording started: {h264_full_path}")
                time.sleep(10) # Record for the specified duration
                self.picam2.stop_encoder()
                print(f"Recording stopped: {h264_full_path}")
            except Exception as e:
                print(f"Recording stopped: {h264_full_path}")

        # --- Post-recording processing ---
        self.noti.send_telegram_message(f"Motion! Video recorded: {h264_filename}")
        
        # Convert to MP4
        mp4_full_path = self.noti.convert_video_to_mp4(h264_full_path) # This should return the full path of the MP4
        
        if mp4_full_path and os.path.exists(mp4_full_path):
            self.noti.send_telegram_video(mp4_full_path)

            # Generate Thumbnail
            generated_thumbnail_path = generate_thumbnail(mp4_full_path)

            # Record event to database
            try:                      
                record_new_video_event(
                    event_type="Motion Detected",
                    h264_path=h264_full_path, # Store full path
                    mp4_path=mp4_full_path,   # Store full path
                    thumbnail_path=generated_thumbnail_path, # Store full path                    
                    notes_str=f"Motion at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as db_e:
                print(f"Error recording event to database: {db_e}")
        else:
            print(f"MP4 conversion failed or file not found for {h264_full_path}.")           

    def generate_mjpeg_stream(self):
        if self.picam2 is None:
            print("MJPEG Stream: Camera not ready. Attempting setup.")
            if self.setup_camera() is None:
                error_message = b"Error: Camera could not be initialized for MJPEG stream."
                yield (b'--frame\r\nContent-Type: text/plain\r\nContent-Length: ' + 
                       f"{len(error_message)}".encode() + b'\r\n\r\n' + error_message + b'\r\n')
                return

        # If start_stream wasn't explicitly called via API, ensure stream state is active
        if not self.stream_active:
            self.stream_active = True
            self.stream_event.clear()

        print("MJPEG stream generation started (using lores stream).")
        #frames_sent = 0
        try:
            while self.stream_active and not self.stream_event.is_set():
                stream_buffer = io.BytesIO()
                with self.camera_lock: # Lock for capturing the frame
                    # Capture from the 'lores' stream, which is YUV420.
                    # capture_file will convert it to JPEG.                   
                    self.picam2.capture_file(stream_buffer, format="jpeg")
                
                frame = stream_buffer.getvalue()
                #stream_buffer.close()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
                       b'\r\n' + frame + b'\r\n')
                 
                #frames_sent += 1
                time.sleep(0.05) # ~20 FPS target
        except Exception as e:
            print(f"MJPEG stream generation stopped.")
        finally:
            print(f"MJPEG stream generation stopped. Total frames sent: {frames_sent}")
            self.stream_active = False # Ensure stream is marked inactive
            self.stream_event.set()    # Ensure event is set to stop any waiting loops

    def start_stream(self):
        if self.stream_active:
            print("Stream is already active.")
            return True
        
        if self.picam2 is None:
            if self.setup_camera() is None:
                print("Error: Camera could not be initialized for starting stream.")
                return False
        
        self.stream_active = True
        self.stream_event.clear() # Clear event for the new stream session
        print("Stream marked as active. MJPEG frames will be generated on request.")
        self.noti.send_telegram_message("Camera live stream started.")
        return True

    def stop_stream(self):
        if self.stream_active:
            self.stream_active = False
            self.stream_event.set()  # Signal generate_mjpeg_stream to stop
            print("Stream stopped. MJPEG generation will cease.")
            self.noti.send_telegram_message("Camera live stream stopped.")
            return True
        print("Stream was not active to stop.")
        return False