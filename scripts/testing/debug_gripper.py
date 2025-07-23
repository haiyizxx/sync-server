#!/usr/bin/env python3
"""
myCobot 280 Gripper Debug Script
Check what gripper functions are available and test basic operations.
"""

from pymycobot.mycobot import MyCobot
import time

# Configuration
DEVICE_PORT = '/dev/ttyACM0'  # Change this to your device path
BAUD_RATE = 115200

def connect_robot():
    """Connect to the myCobot"""
    try:
        mc = MyCobot(DEVICE_PORT, BAUD_RATE)
        print(f"✓ Connected to myCobot on {DEVICE_PORT}")
        return mc
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return None

def check_gripper_functions(mc):
    """Check what gripper functions are available"""
    print("\n=== Checking Gripper Functions ===")
    
    # Check for common gripper methods
    gripper_methods = [
        'set_gripper_value',
        'get_gripper_value', 
        'set_gripper_calibration',
        'get_gripper_calibration',
        'set_gripper_range',
        'get_gripper_range',
        'set_gripper_mode',
        'get_gripper_mode',
        'set_gripper_derailleur',
        'get_gripper_derailleur'
    ]
    
    available_methods = []
    for method in gripper_methods:
        if hasattr(mc, method):
            available_methods.append(method)
            print(f"✓ {method} - Available")
        else:
            print(f"✗ {method} - Not available")
    
    print(f"\nTotal available gripper methods: {len(available_methods)}")
    return available_methods

def test_gripper_operations(mc, available_methods):
    """Test basic gripper operations"""
    print("\n=== Testing Gripper Operations ===")
    
    if 'get_gripper_value' in available_methods:
        try:
            value = mc.get_gripper_value()
            print(f"Current gripper value: {value}")
        except Exception as e:
            print(f"Error getting gripper value: {e}")
    
    if 'set_gripper_value' in available_methods:
        try:
            print("Testing gripper open (value 100)...")
            mc.set_gripper_value(100, 50)
            time.sleep(2)
            
            print("Testing gripper close (value 0)...")
            mc.set_gripper_value(0, 50)
            time.sleep(2)
            
            print("Gripper test completed")
        except Exception as e:
            print(f"Error setting gripper value: {e}")
    
    # Test other available methods
    for method in available_methods:
        if method.startswith('get_') and method != 'get_gripper_value':
            try:
                result = getattr(mc, method)()
                print(f"{method}(): {result}")
            except Exception as e:
                print(f"Error calling {method}(): {e}")

def main():
    mc = connect_robot()
    if mc is None:
        return
    
    available_methods = check_gripper_functions(mc)
    test_gripper_operations(mc, available_methods)
    
    print("\n=== Debug Complete ===")
    print("If no gripper methods are available, your myCobot might not have a gripper attached")
    print("or the gripper might use different method names.")

if __name__ == "__main__":
    main() 