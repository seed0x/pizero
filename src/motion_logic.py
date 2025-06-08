from gpiozero import MotionSensor
import time
from config import PIR_PIN_BCM

def check_for_motion(cam_manager):
    """
    Monitors the PIR sensor for motion using gpiozero and triggers video recording.
    Args:
    camera\_manager\_instance: An instance of the CameraManager class.
    """
    if PIR_PIN_BCM is None:
        print("Error: PIR\_PIN\_BCM not defined in config.py. Motion detection disabled.")
        return

    try:
        # Initialize the PIR sensor using gpiozero with the BCM pin number
        pir = MotionSensor(PIR_PIN_BCM)
        print(f"Motion detection started on GPIO (BCM) pin {PIR_PIN_BCM}...")
        print("Allowing sensor to settle for 30 seconds...")
        time.sleep(30) # Allow PIR sensor to settle
        print("Sensor settled. Monitoring for motion.")

        while True:
            # The pir.when_motion event handler is a great way to do this,
            # but a simple loop is also fine to start.
            if pir.motion_detected:
                print(f"Motion detected by PIR sensor at {time.strftime('%Y-%m-%d %H:%M:%S')}!")
                # Call the record_motion_video method of the passed CameraManager instance
                cam_manager.record_motion_video()
        
                print("Motion event processed. Cooldown period starting (e.g., 60 seconds).")
                # Wait for motion to stop before starting the next check cycle
                pir.wait_for_no_motion()
                print("Motion has stopped. Applying additional cooldown.")
                time.sleep(30) # Additional 30s cooldown after motion stops
                print("Cooldown finished. Resuming motion monitoring.")
    
            # Short sleep to prevent the loop from using 100% CPU if you remove the blocking waits
            time.sleep(0.1)
    except Exception as e:
        print(f"Error in motion detection loop: {e}")
    