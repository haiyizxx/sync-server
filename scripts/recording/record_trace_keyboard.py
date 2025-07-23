#!/usr/bin/env python3
"""
myCobot 280 Joint Movement Recording Script - Keyboard Controlled
Records joint movements and gripper data at specified frequency
Press 'p' to start a new trace (automatically saves current trace if recording)
"""

from pymycobot.mycobot import MyCobot
import time
import sys
import json
import threading
import requests
from datetime import datetime
import os
from pathlib import Path
import select
import termios
import tty

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200
RECORDING_FREQUENCY = 5  # Hz (5 times per second)
RECORDING_INTERVAL = 0.2  # Seconds between recordings (0.2 seconds = 200ms)

# Sync server configuration
SYNC_SERVER_URL = "http://localhost:5512"  # Change to your server IP
ENABLE_SYNC = True  # Set to False to disable sync

# Global variables
recording = False
current_gripper_value = 0  # Default gripper value
current_trace = []
current_start_time = None
recording_thread = None
mc = None

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

def generate_task_name():
    """Generate a task name with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return timestamp

def save_current_trace():
    """Save the current trace to file"""
    global current_trace, current_start_time
    
    if not current_trace:
        print("No trace data to save.")
        return
    
    # Generate task name with timestamp
    task_name = generate_task_name()
    
    # Create traces directory if it doesn't exist
    base_dir = Path(__file__).parent.parent.parent
    traces_dir = base_dir / "data" / "raw" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    filename = str(traces_dir / f"{task_name}.json")
    
    # Generate metadata timestamps
    end_time = time.time()
    duration_seconds = end_time - current_start_time if current_start_time else 0
    start_timestamp_clean = int(round(current_start_time * 1000)) if current_start_time else None
    end_timestamp_clean = int(round(end_time * 1000))
    
    # Create trace data structure
    trace_data = {
        "metadata": {
            "recording_frequency_hz": RECORDING_FREQUENCY,
            "total_points": len(current_trace),
            "duration_seconds": duration_seconds,
            "start_timestamp_ms": start_timestamp_clean,
            "end_timestamp_ms": end_timestamp_clean,
            "task_name": task_name,
            "description": f"Automatically recorded task {task_name}",
            "objects_involved": ["robot_arm"],
            "robot_model": "myCobot 280",
            "task_success": True,  # Default to True, can be modified later
            "recording_mode": "keyboard_controlled"
        },
        "trace": current_trace
    }
    
    # Save to file
    try:
        with open(filename, "w") as f:
            json.dump(trace_data, f, indent=2)
        print(f"✓ Trace saved to {filename} ({len(current_trace)} data points)")
        
        # Send end command to sync server
        send_sync_command("end", task_name)
        
    except Exception as e:
        print(f"✗ Error saving trace: {e}")

def continuous_recording():
    """
    Continuously record joint angles and gripper value at the specified frequency.
    This runs in a separate thread.
    """
    global recording, current_gripper_value, current_trace, current_start_time, mc
    
    recording_count = 0
    print(f"✓ Recording started at {RECORDING_FREQUENCY}Hz...")
    
    while recording:
        try:
            # Get current joint angles
            angles = mc.get_angles()
            coords = mc.get_coords()  # End-effector coordinates [x, y, z, rx, ry, rz]

            if angles is not None:
                # Unix timestamp with millisecond precision (consistent with image timestamps)
                current_time = time.time()
                unix_timestamp_ms = round(current_time * 1000) / 1000  # Round to millisecond precision
                clean_timestamp_ms = int(round(current_time * 1000))  # Remove decimal point
                relative_timestamp = current_time - current_start_time

                # Use the current gripper value (set by user)
                gripper_value = current_gripper_value

                # Get additional robot state information
                robot_state = {
                    "timestamp_ms": clean_timestamp_ms,
                    "relative_timestamp": relative_timestamp,
                    "angles": angles,
                    "coords": coords,
                    "gripper_value": gripper_value,
                    "is_moving": mc.is_moving() if hasattr(mc, 'is_moving') else False,
                    "is_powered_on": mc.is_powered_on() if hasattr(mc, 'is_powered_on') else True,
                    "image": None  # Placeholder for linking with captured images
                }

                # Add to trace
                current_trace.append(robot_state)
                recording_count += 1

                # Print progress every 50 recordings with gripper info
                if recording_count % 50 == 0:
                    print(f"Recording... {recording_count} points (gripper: {gripper_value})")

            # Wait for next recording interval
            time.sleep(RECORDING_INTERVAL)

        except Exception as e:
            print(f"Recording error: {e}")
            break

    print(f"Recording stopped. Total recorded: {recording_count}")

def start_new_trace():
    """Start a new trace recording"""
    global recording, current_trace, current_start_time, recording_thread
    
    # If already recording, save current trace first
    if recording:
        print("Saving current trace...")
        recording = False
        if recording_thread and recording_thread.is_alive():
            recording_thread.join(timeout=2.0)  # Wait for thread to finish
        save_current_trace()
    
    # Clear previous trace and start new recording
    current_trace = []
    current_start_time = time.time()
    recording = True
    
    # Generate task name for sync
    task_name = generate_task_name()
    
    # Send start command to sync server
    send_sync_command("start", task_name)
    
    # Start recording in a separate thread
    recording_thread = threading.Thread(target=continuous_recording)
    recording_thread.daemon = True
    recording_thread.start()

def stop_recording_and_save():
    """Stop current recording and save trace"""
    global recording, recording_thread
    
    if not recording:
        print("Not currently recording!")
        return
    
    print("Stopping recording...")
    recording = False
    
    # Wait for recording thread to finish
    if recording_thread and recording_thread.is_alive():
        recording_thread.join(timeout=2.0)
    
    # Save the trace
    save_current_trace()

def get_char():
    """Get a single character from stdin without pressing enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        char = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return char

def handle_key_input(char):
    """Handle key input from terminal"""
    global current_gripper_value
    
    if char == 'p':
        print("\n'p' pressed - Starting new trace...")
        start_new_trace()
    elif char == 's':
        print("\n's' pressed - Stopping and saving current trace...")
        stop_recording_and_save()
    elif char == 'q' or char == '\x1b':  # 'q' or ESC
        print("\nExiting...")
        if recording:
            stop_recording_and_save()
        return False  # Exit
    elif char.isdigit():
        # Set gripper value with number keys (0-9 maps to 0-90)
        gripper_value = int(char) * 10
        if gripper_value <= 100:
            try:
                mc.set_gripper_value(gripper_value, 50)
                current_gripper_value = gripper_value
                print(f"\nGripper set to {gripper_value}")
            except Exception as e:
                print(f"\nError setting gripper: {e}")
    elif char == '\x03':  # Ctrl+C
        print("\nCtrl+C pressed - Exiting...")
        if recording:
            stop_recording_and_save()
        return False
    return True

def main():
    global mc
    
    print("=== myCobot 280 Keyboard-Controlled Trace Recording ===")
    print("Commands:")
    print("  'p' - Start new trace (auto-saves current trace if recording)")
    print("  's' - Stop and save current trace")
    print("  'q' - Quit (auto-saves current trace)")
    print("  '0'-'9' - Set gripper value (0=0%, 1=10%, ..., 9=90%)")
    print("  ESC or Ctrl+C - Quit")
    print()
    
    # Connect to robot
    mc = connect_robot()
    if mc is None:
        return

    # Set robot to free mode
    try:
        mc.release_all_servos()
        print("✓ Robot set to free mode")
    except Exception as e:
        print(f"✗ Failed to set free mode: {e}")
        return

    print("\nReady! Press 'p' to start recording...")
    print("Press any key (no need to press Enter):")
    
    # Terminal input loop
    try:
        while True:
            char = get_char()
            if not handle_key_input(char):
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        if recording:
            stop_recording_and_save()
    except Exception as e:
        print(f"Error with input handling: {e}")
    
    # Final cleanup - save any ongoing recording
    if recording:
        print("Saving final trace...")
        stop_recording_and_save()
    
    print("Exiting...")

if __name__ == "__main__":
    main() 