import os
import threading
from camera_manager import CameraManager
from flask import Flask, render_template, Response, jsonify, request, session,redirect,url_for, send_from_directory
from telegram_handler import notiManager
from motion_logic import check_for_motion
from config import PASSWORD, USER_NAME, THUMBNAILS_SUBDIR_NAME, VIDEOS_SUBDIR_NAME, EVENTS_STORAGE_DIR
from myEventDataBase import init_db, get_video_events

# Make the Flask app
app = Flask(__name__)
app.secret_key = 'mysecret'

# Global variables
cam_manager = CameraManager()

def load_jpeg_image(filename="placeholder.jpg"):
    """Loads a JPEG image from the static folder and returns its binary content."""
    image_path = os.path.join(app.static_folder, filename)
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        return image_bytes
    except FileNotFoundError:
        print(f"Error: Placeholder image '{filename}' not found in '{app.static_folder}'.")
        return None
    except Exception as e:
        print(f"Error loading placeholder image '{filename}': {e}")
        return None

@app.route('/media/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    if 'user' not in session: # Protect thumbnails
        return "Access Denied", 403
    try:
        print(f"Attempting to serve thumbnail: {filename} from {THUMBNAIL_FILES_DIR}")
        return send_from_directory(THUMBNAIL_FILES_DIR, filename, as_attachment=False)
    except FileNotFoundError:
        return "Thumbnail not found", 404
    except Exception as e:
        return "Error serving thumbnail", 500

@app.route('/media/videos/<path:filename>')
def serve_video(filename):
    if 'user' not in session: # Protect videos
        return "Access Denied: Please login.", 403
    try:
        # VIDEO_FILES_DIR is the absolute path to MP4 video files
        print(f"Attempting to serve video: {filename} from {EVENTS_STORAGE_DIR}")
        # send_from_directory handles range requests for video streaming
        return send_from_directory(EVENTS_STORAGE_DIR, filename, as_attachment=False, mimetype='video/mp4')
    except FileNotFoundError:
        return "Video not found", 404
    except Exception as e:
    return "Error serving video", 500

#Login Page
@app.route('/', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        submitted_username = request.form.get('username')
        submitted_password = request.form.get('password')
        
        if submitted_username == USER_NAME and submitted_password == PASSWORD:
            session['user'] = submitted_username
            return redirect(url_for('dashboard'))
    else:
        error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

# Web page route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int) # Get page number for events, default to 1
    per_page = 5 # Show fewer events per page on the dashboard
    offset = (page - 1) * per_page
    events_on_dashboard = get_video_events(limit=per_page, offset=offset)
    
    return render_template(
        'index.html',
        user=session['user'],
        events=events_on_dashboard, # Pass the events to index.html
        current_page=page # Pass current page for pagination
        )

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None) # Remove the user from the session
    return redirect(url_for('login'))

@app.route('/events')
def events_page():
    if 'user' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int) # Get page number from query param, default to 1
    per_page = 10 # Number of events per page
    offset = (page - 1) * per_page
    all_events = get_video_events(limit=per_page, offset=offset)
    return render_template('events.html', events=all_events, current_page=page)

# Video feed route
@app.route('/video_feed')
def video_feed():
    if cam_manager.stream_active:
        return Response(
            cam_manager.generate_mjpeg_stream(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    else:
        placeholder_bytes = load_jpeg_image("placeholder.jpg")
        if placeholder_bytes:
            return Response(placeholder_bytes, mimetype='image/jpeg')
        else:
            # Fallback if placeholder couldn't be loaded
            return "Stream inactive and placeholder image is unavailable.", 404

# Route to start stream
@app.route('/start_stream', methods=['POST'])
def start_stream_route():
    if cam_manager.start_stream():
        return jsonify({"status": "success", "message": "Stream started"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to start stream"}), 500

# Route to stop stream
@app.route('/stop_stream', methods=['POST'])
def stop_stream_route():
    if cam_manager.stop_stream():
        return jsonify({"status": "success", "message": "Stream stopped"}), 200
    else:
        return jsonify({"status": "error", "message": "Stream was not running"}), 400

# Route to check stream status
@app.route('/stream_status')
def stream_status():
    return jsonify({"active": cam_manager.stream_active})

# Create templates directory
def create_templates_dir():
    os.makedirs("templates", exist_ok=True)
    os.makedirs("/home/seedx/pizero/events", exist_ok=True)
    #os.makedirs(THUMBNAILS_STORAGE_DIR, exist_ok=True)

# Main program starts here
if __name__ == '__main__':
    print("Starting security camera app...")

    init_db()

    # Create directories
    create_templates_dir()

    cam_manager.noti.send_telegram_message("Security camera system is starting...")

    # Start the motion detection in a background thread
    motion_thread = threading.Thread(target=check_for_motion,args=(cam_manager,),daemon=True)
    motion_thread.start()

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)

