#!/usr/bin/env python3
"""
myCobot 280 Joint Test Script
Tests all 6 joints individually with safe movements
and saves the joint angles to a file
"""

from pymycobot.mycobot import MyCobot
import time
import sys
import json
import threading
from datetime import datetime

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200
MOVEMENT_SPEED = 30  # Speed for movements (1-100)
TEST_ANGLE = 15      # Test angle in degrees (safe small movement)
DELAY_BETWEEN_MOVES = 2  # Seconds to wait between movements
RECORDING_FREQUENCY = 10  # Hz (10 times per second)
RECORDING_INTERVAL = 1.0 / RECORDING_FREQUENCY  # Seconds between recordings

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

def get_current_status(mc):
    """Get and display current robot status"""
    try:
        angles = mc.get_angles()
        coords = mc.get_coords()
        print(f"Current joint angles: {angles}")
        print(f"Current coordinates: {coords}")
        return True
    except Exception as e:
        print(f"✗ Failed to get status: {e}")
        return False

def test_individual_joints(mc):
    """
    Test each joint individually by moving it to a safe position and back.
    """
    joint_names = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
    for i, joint_name in enumerate(joint_names):
        print(f"\nTesting {joint_name}...")
        # Move to a safe position (e.g., 0 degrees)
        print(f"Moving {joint_name} to 0 degrees...")
        mc.set_servo_angle(i + 1, 0, MOVEMENT_SPEED)
        time.sleep(DELAY_BETWEEN_MOVES)

        # Move to a test angle (e.g., 15 degrees)
        print(f"Moving {joint_name} to {TEST_ANGLE} degrees...")
        mc.set_servo_angle(i + 1, TEST_ANGLE, MOVEMENT_SPEED)
        time.sleep(DELAY_BETWEEN_MOVES)

        # Move back to 0 degrees
        print(f"Moving {joint_name} back to 0 degrees...")
        mc.set_servo_angle(i + 1, 0, MOVEMENT_SPEED)
        time.sleep(DELAY_BETWEEN_MOVES)
        print(f"Finished testing {joint_name}.")

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

def record_movement_trace(mc):
    """
    Record joint movements at specified frequency with start/end commands.
    """
    print(f"Robot is now in free mode. Move the arm by hand.")
    print(f"Commands:")
    print(f"  <start> - Begin recording at {RECORDING_FREQUENCY}Hz")
    print(f"  <end>   - Stop recording and save trace")
    print(f"  <quit>  - Exit without saving")
    print(f"  <status> - Show current joint angles")
    
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
                print("Move the robot arm. Type 'end' to stop recording.")
                
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
                    if hasattr(mc, 'get_gripper_value'):
                        print(f"Gripper value: {mc.get_gripper_value()}")
                except Exception as e:
                    print(f"Failed to get status: {e}")
                    
            else:
                print("Unknown command. Use: start, end, quit, or status")
                
        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def continuous_recording(mc, trace, start_time):
    """
    Continuously record joint angles at the specified frequency.
    This runs in a separate thread.
    """
    global recording
    recording = True
    
    while recording:
        try:
            # Get current joint angles
            angles = mc.get_angles()
            coords = mc.get_coords()  # End-effector coordinates [x, y, z, rx, ry, rz]
            
            if angles is not None:
                # Calculate timestamp relative to start
                timestamp = time.time() - start_time
                
                # Get additional robot state information
                robot_state = {
                    "timestamp": timestamp,
                    "angles": angles,
                    "coords": coords,
                    "gripper_value": mc.get_gripper_value() if hasattr(mc, 'get_gripper_value') else None,
                    "is_moving": mc.is_moving() if hasattr(mc, 'is_moving') else False,
                    "is_powered_on": mc.is_powered_on() if hasattr(mc, 'is_powered_on') else True,
                }
                
                # Add to trace
                trace.append(robot_state)
                
                # Print progress every 50 recordings
                if len(trace) % 50 == 0:
                    print(f"Recorded {len(trace)} points...")
                    
            # Wait for next recording interval
            time.sleep(RECORDING_INTERVAL)
            
        except Exception as e:
            print(f"Recording error: {e}")
            break
    
    print("Recording thread stopped.")

def main():
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
    
    # Start recording interface
    record_movement_trace(mc)

if __name__ == "__main__":
    main()
