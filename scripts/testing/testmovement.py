#!/usr/bin/env python3
"""
myCobot 280 Joint Test Script
Tests all 6 joints individually with safe movements
"""

from pymycobot.mycobot import MyCobot
import time
import sys

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200
MOVEMENT_SPEED = 30  # Speed for movements (1-100)
TEST_ANGLE = 15      # Test angle in degrees (safe small movement)
DELAY_BETWEEN_MOVES = 2  # Seconds to wait between movements

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
    """Test each joint individually"""
    print("\n" + "="*50)
    print("TESTING INDIVIDUAL JOINTS")
    print("="*50)
    
    # Joint names for reference
    joint_names = [
        "Joint 1 (Base rotation)",
        "Joint 2 (Shoulder)",
        "Joint 3 (Elbow)",
        "Joint 4 (Wrist 1)",
        "Joint 5 (Wrist 2)",
        "Joint 6 (Wrist 3)"
    ]
    
    for joint_num in range(1, 7):
        print(f"\n--- Testing {joint_names[joint_num-1]} ---")
        
        try:
            # Get current angle
            current_angles = mc.get_angles()
            if current_angles:
                current_angle = current_angles[joint_num-1]
                print(f"Current angle: {current_angle}°")
            else:
                current_angle = 0
                print("Could not read current angle, assuming 0°")
            
            # Test positive movement
            print(f"Moving to +{TEST_ANGLE}°...")
            mc.send_angle(joint_num, TEST_ANGLE, MOVEMENT_SPEED)
            time.sleep(DELAY_BETWEEN_MOVES)
            
            # Test negative movement
            print(f"Moving to -{TEST_ANGLE}°...")
            mc.send_angle(joint_num, -TEST_ANGLE, MOVEMENT_SPEED)
            time.sleep(DELAY_BETWEEN_MOVES)
            
            # Return to original position
            print(f"Returning to original position ({current_angle}°)...")
            mc.send_angle(joint_num, current_angle, MOVEMENT_SPEED)
            time.sleep(DELAY_BETWEEN_MOVES)
            
            print(f"✓ Joint {joint_num} test completed")
            
        except Exception as e:
            print(f"✗ Joint {joint_num} test failed: {e}")
        
        # Ask user if they want to continue
        if joint_num < 6:
            response = input(f"\nContinue to next joint? (y/n): ").lower()
            if response != 'y':
                break

def test_all_joints_sequence(mc):
    """Test all joints in a coordinated sequence"""
    print("\n" + "="*50)
    print("TESTING ALL JOINTS SEQUENCE")
    print("="*50)
    
    try:
        # Get starting position
        start_angles = mc.get_angles()
        if not start_angles:
            start_angles = [0, 0, 0, 0, 0, 0]
        print(f"Starting position: {start_angles}")
        
        # Define test sequences
        test_sequences = [
            [10, 0, 0, 0, 0, 0],    # Base rotation
            [0, 15, 0, 0, 0, 0],    # Shoulder
            [0, 0, 20, 0, 0, 0],    # Elbow
            [0, 0, 0, 15, 0, 0],    # Wrist 1
            [0, 0, 0, 0, 15, 0],    # Wrist 2
            [0, 0, 0, 0, 0, 30],    # Wrist 3
            start_angles             # Return home
        ]
        
        for i, angles in enumerate(test_sequences):
            if i < len(test_sequences) - 1:
                print(f"Moving to test position {i+1}: {angles}")
            else:
                print(f"Returning to start position: {angles}")
            
            mc.send_angles(angles, MOVEMENT_SPEED)
            time.sleep(3)  # Longer delay for multi-joint moves
            
            # Verify position
            current = mc.get_angles()
            if current:
                print(f"Actual position: {current}")
        
        print("✓ All joints sequence test completed")
        
    except Exception as e:
        print(f"✗ All joints sequence test failed: {e}")

def main():
    """Main test function"""
    print("myCobot 280 Joint Test Script")
    print("=" * 40)
    
    # Connect to robot
    mc = connect_robot()
    if not mc:
        sys.exit(1)
    
    # Get initial status
    print("\n--- Initial Status ---")
    if not get_current_status(mc):
        print("Warning: Could not read robot status")
    
    # Safety warning
    print("\n⚠️  SAFETY WARNING:")
    print("- Ensure robot has clear movement space")
    print("- Keep emergency stop accessible")
    print("- Movements will be small but verify safety first")
    
    response = input("\nProceed with joint tests? (y/n): ").lower()
    if response != 'y':
        print("Test cancelled")
        return
    
    # Run tests
    try:
        # Test individual joints
        test_individual_joints(mc)
        
        # Ask about sequence test
        response = input("\nRun coordinated sequence test? (y/n): ").lower()
        if response == 'y':
            test_all_joints_sequence(mc)
        
        print("\n--- Final Status ---")
        get_current_status(mc)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        print("\nTest completed. Robot should be in safe position.")

if __name__ == "__main__":
    main()



