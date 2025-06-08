import sqlite3
import os
from datetime import datetime

DB_FILE = 'security_camera_events.db'

def init_db():
    create_video_events_table()

def create_video_events_table():
    query = """
    CREATE TABLE IF NOT EXISTS video_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_timestamp TEXT NOT NULL, -- Storing your custom formatted string
        event_type TEXT DEFAULT 'motion_detected',
        h264_filepath TEXT UNIQUE,
        mp4_filepath TEXT UNIQUE,    
        thumbnail_path TEXT UNIQUE,
        notes TEXT, 
        is_archived INTEGER DEFAULT 0,
        db_record_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            print(f"Table 'video_events' (simplified) ensured to exist in '{DB_FILE}'.")
    except sqlite3.Error as e:
        print(f"Error creating 'video_events' table: {e}")

def record_new_video_event(event_type, h264_path, mp4_path, thumbnail_path, notes_str):
    """Inserts a new video event into the database with a custom formatted timestamp."""
    query = """
    INSERT INTO video_events 
        (event_type, h264_filepath, mp4_filepath, thumbnail_path, notes, event_timestamp)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    # Using your custom format for event_timestamp
    current_event_time_str = datetime.now().strftime("%m-%d-%Y_%H:%M")
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                event_type,
                h264_path,
                mp4_path,
                thumbnail_path,
                notes_str,
                current_event_time_str # Storing the custom formatted string
            ))
            conn.commit()
            new_id = cursor.lastrowid
            print(f"New video event recorded in DB. ID: {new_id}, MP4: {mp4_path}")
            return new_id
    except sqlite3.Error as e:
        print(f"Error inserting video event for '{mp4_path}': {e}")
        if "UNIQUE constraint failed" in str(e):
            print("This might be due to attempting to insert a duplicate filepath.")
        return None

def get_video_events(limit=20, offset=0, sort_by="event_timestamp", sort_order="DESC"):
    """Fetches video events from the database (simplified columns)."""
    allowed_sort_columns = ["id", "event_timestamp", "event_type", "db_record_created_at"]
    if sort_by not in allowed_sort_columns:
        sort_by = "event_timestamp" 
    
    if sort_order.upper() not in ["ASC", "DESC"]:
        sort_order = "DESC"

    query = f"""
    SELECT id, event_timestamp, event_type, h264_filepath, mp4_filepath, thumbnail_path, notes, is_archived
    FROM video_events
    ORDER BY {sort_by} {sort_order}
    LIMIT ? OFFSET ?;
    """
    events = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (limit, offset))
            results = cursor.fetchall()
            for row in results:
                event_dict = dict(row)
                # You can add pre-formatted display strings here if needed,
                # or handle formatting directly in Jinja.
                # For example, to get just the time part from "MM-DD-YYYY_HH:MM":
                if event_dict.get('event_timestamp'):
                    try:
                        event_dict['display_time_only'] = event_dict['event_timestamp'].split('_')[1]
                    except IndexError:
                        event_dict['display_time_only'] = event_dict['event_timestamp'] # fallback
                else:
                    event_dict['display_time_only'] = 'N/A'
                events.append(event_dict)
        print(f"Fetched {len(events)} events. Limit: {limit}, Offset: {offset}, Sort: {sort_by} {sort_order}")
    except sqlite3.Error as e:
        print(f"Error fetching video events: {e}")
    return events

