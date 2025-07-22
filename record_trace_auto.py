#!/usr/bin/env python3
"""
myCobot 280 Joint Movement Recording Script (Auto Mode)
Records joint movements and gripper data at specified frequency
Robot is NOT put in manual mode - can be controlled by other scripts
"""

from pymycobot.mycobot import MyCobot
import time
import sys
import json
import threading
import requests
from datetime import datetime

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200
RECORDING_FREQUENCY = 2  # Hz (2 times per second)
RECORDING_INTERVAL = 0.5  # Seconds between recordings (0.5 seconds)

# Sync server configuration
SYNC_SERVER_URL = "http://localhost:5512"  # Change to your server IP
ENABLE_SYNC = True  # Set to False to disable sync

# Global variables
recording = False
current_gripper_value = 0  # Default gripper value

def send_sync_command(command, task_name=""):
    """Send command to sync server"""
    if not ENABLE_SYNC:
        return

    try:
        data = {
            'command': command,
            'task_name': task_name
        }
        response = requests.post(f"{SYNC_SERVER_URL}/command",
                               json=data,
                               timeout=1.0)
        if response.status_code == 200:
            print(f"✓ Sync command '{command}' sent to server")
        else:
            print(f"✗ Failed to send sync command: {response.status_code}")
    except Exception as e:
        print(f"✗ Sync server error: {e}")

def connect_robot():
    """Connect to the myCobot"""
    try:
        mc = MyCobot(DEVICE_PORT, BAUD_RATE)
        print(f"✓ Connected to myCobot on {DEVICE_PORT}")
        return mc
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("- Check USB cable connection")
        print("- Verify device path with: ls /dev/ttyUSB* /dev/ttyACM*")
        print("- Set permissions: sudo chmod 666 /dev/ttyUSB0")
        print("- Try different baud rates: 9600, 57600, 115200")
        return None

def get_task_metadata():
    """
    Collect metadata about the task being performed.
    """
    print("\n=== Task Information ===")
    task_name = input("Task name (e.g., 'pick_and_place_red_block'): ").strip()
    description = input("Task description: ").strip()
    objects_involved = input("Objects involved (comma-separated): ").strip()
    expected_duration = input("Expected duration (seconds): ").strip()

    return {
        "task_name": task_name,
        "description": description,
        "objects_involved": [obj.strip() for obj in objects_involved.split(",") if obj.strip()],
        "expected_duration_seconds": float(expected_duration) if expected_duration else None,
        "robot_model": "myCobot 280",
        "recording_frequency_hz": RECORDING_FREQUENCY
    }

def continuous_recording(mc, trace, start_time):
    """
    Continuously record joint angles and gripper value at the specified frequency.
    This runs in a separate thread.
    """
    global recording, current_gripper_value
    recording = True

    recording_count = 0

    while recording:
        try:
            # Get current joint angles
            angles = mc.get_angles()
            coords = mc.get_coords()  # End-effector coordinates [x, y, z, rx, ry, rz]

            if angles is not None:
                # Calculate timestamp relative to start
                relative_timestamp = time.time() - start_time
                unix_timestamp = time.time()  # Unix timestamp with millisecond precision

                # Use the current gripper value (set by user)
                gripper_value = current_gripper_value

                # Get additional robot state information
                robot_state = {
                    "relative_timestamp": relative_timestamp,
                    "unix_timestamp": unix_timestamp,
                    "angles": angles,
                    "coords": coords,
                    "gripper_value": gripper_value,
                    "is_moving": mc.is_moving() if hasattr(mc, 'is_moving') else False,
                    "is_powered_on": mc.is_powered_on() if hasattr(mc, 'is_powered_on') else True,
                }

                # Add to trace
                trace.append(robot_state)
                recording_count += 1

                # Print progress every 50 recordings with gripper info
                if recording_count % 50 == 0:
                    print(f"Recorded {recording_count} points... gripper: {gripper_value}")

            # Wait for next recording interval
            time.sleep(RECORDING_INTERVAL)

        except Exception as e:
            print(f"Recording error: {e}")
            break

    print(f"Recording thread stopped. Total recorded: {recording_count}")

def record_movement_trace(mc):
    """
    Record joint movements at specified frequency with start/end commands.
    """
    global current_gripper_value
    print(f"Robot is ready for recording. Control the robot with another script.")
    print(f"Commands:")
    print(f"  <start> - Begin recording at {RECORDING_FREQUENCY}Hz")
    print(f"  <end>   - Stop recording and save trace")
    print(f"  <quit>  - Exit without saving")
    print(f"  <status> - Show current joint angles and gripper value")
    print(f"  gripper <value> - Set gripper to value (0-100) and update the value for trace")

    trace = []
    recording = False
    start_time = None
    task_metadata = None

    while True:
        try:
            command = input("Enter command: ").strip().lower()

            if command == "start":
                if recording:
                    print("Already recording!")
                    continue

                # Get task metadata before starting
                if task_metadata is None:
                    task_metadata = get_task_metadata()

                recording = True
                start_time = time.time()
                print(f"Recording started at {RECORDING_FREQUENCY}Hz...")
                print("Control the robot with another script. Type 'end' to stop recording.")

                # Send start command to sync server
                send_sync_command("start", task_metadata.get("task_name", ""))

                # Start recording in a separate thread
                recording_thread = threading.Thread(
                    target=continuous_recording,
                    args=(mc, trace, start_time)
                )
                recording_thread.daemon = True
                recording_thread.start()

            elif command == "end":
                if not recording:
                    print("Not currently recording!")
                    continue

                recording = False
                print("Recording stopped.")
                print(f"Recorded {len(trace)} data points.")

                # Send end command to sync server
                send_sync_command("end", task_metadata.get("task_name", "") if task_metadata else "")

                # Ask for success evaluation
                success = input("Did the task complete successfully? (y/n): ").strip().lower()
                success_bool = success in ['y', 'yes', 'true', '1']

                # Save the trace
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"joint_trace_{timestamp}.json"

                trace_data = {
                    "metadata": {
                        "recording_frequency_hz": RECORDING_FREQUENCY,
                        "total_points": len(trace),
                        "duration_seconds": (time.time() - start_time) if start_time else 0,
                        "timestamp": timestamp,
                        "task_success": success_bool,
                        **task_metadata
                    },
                    "trace": trace
                }

                with open(filename, "w") as f:
                    json.dump(trace_data, f, indent=2)
                print(f"Trace saved to {filename}")

                # Clear trace for next recording
                trace.clear()
                task_metadata = None  # Reset for next task

            elif command == "quit":
                print("Exiting...")
                break

            elif command == "status":
                try:
                    angles = mc.get_angles()
                    coords = mc.get_coords()
                    print(f"Current joint angles: {angles}")
                    print(f"Current coordinates: {coords}")
                    print(f"Current gripper value (for trace): {current_gripper_value}")
                except Exception as e:
                    print(f"Failed to get status: {e}")

            elif command.startswith("gripper "):
                try:
                    value = int(command.split()[1])
                    if 0 <= value <= 100:
                        mc.set_gripper_value(value, 50)
                        current_gripper_value = value
                        print(f"Gripper set to {value} and will be recorded in trace.")
                    else:
                        print("Value must be between 0 and 100.")
                except Exception as e:
                    print(f"Error setting gripper value: {e}")

            else:
                print("Unknown command. Use: start, end, quit, status, or gripper <value>")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    # Connect to robot
    mc = connect_robot()
    if mc is None:
        return

    # Note: Robot is NOT put in free mode - it can be controlled by other scripts
    print("✓ Robot connected and ready for recording")
    print("⚠️  Robot is NOT in free mode - control it with another script")

    # Start recording interface
    record_movement_trace(mc)

if __name__ == "__main__":
    main()
