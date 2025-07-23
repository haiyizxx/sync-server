#!/usr/bin/env python3
"""
myCobot 280 Gripper Test Script
Test gripper open, close, set value, and get value functions.
"""

from pymycobot.mycobot import MyCobot
import time
import sys

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200
GRIPPER_OPEN = 100  # Adjust as needed (max open value)
GRIPPER_CLOSE = 0  # Adjust as needed (fully closed value)
GRIPPER_SPEED = 50  # Speed for gripper movement (1-100)

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

def gripper_menu(mc):
    print("\n=== Gripper Test Menu ===")
    print("Commands:")
    print("  open         - Open the gripper")
    print("  close        - Close the gripper")
    print("  set <value>  - Set gripper to value (0-100)")
    print("  get          - Get current gripper value")
    print("  quit         - Exit")

    while True:
        try:
            cmd = input("Enter command: ").strip().lower()
            if cmd == "open":
                if hasattr(mc, 'set_gripper_value'):
                    mc.set_gripper_value(GRIPPER_OPEN, GRIPPER_SPEED)
                    print(f"Gripper opening to {GRIPPER_OPEN}...")
                else:
                    print("This robot does not support set_gripper_value().")
            elif cmd == "close":
                if hasattr(mc, 'set_gripper_value'):
                    mc.set_gripper_value(GRIPPER_CLOSE, GRIPPER_SPEED)
                    print(f"Gripper closing to {GRIPPER_CLOSE}...")
                else:
                    print("This robot does not support set_gripper_value().")
            elif cmd.startswith("set "):
                if hasattr(mc, 'set_gripper_value'):
                    try:
                        value = int(cmd.split()[1])
                        if 0 <= value <= 100:
                            mc.set_gripper_value(value, GRIPPER_SPEED)
                            print(f"Gripper set to {value}.")
                        else:
                            print("Value must be between 0 and 100.")
                    except Exception as e:
                        print(f"Invalid value: {e}")
                else:
                    print("This robot does not support set_gripper_value().")
            elif cmd == "get":
                if hasattr(mc, 'get_gripper_value'):
                    value = mc.get_gripper_value()
                    print(f"Current gripper value: {value}")
                else:
                    print("This robot does not support get_gripper_value().")
            elif cmd == "quit":
                print("Exiting gripper test.")
                break
            else:
                print("Unknown command. Use: open, close, set <value>, get, quit")
        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    mc = connect_robot()
    if mc is None:
        return
    # Optionally, set robot to free mode
    try:
        mc.release_all_servos()
        print("✓ Robot set to free mode (if supported)")
    except Exception as e:
        print(f"✗ Failed to set free mode: {e}")
    gripper_menu(mc)

if __name__ == "__main__":
    main() 