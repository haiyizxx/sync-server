#!/usr/bin/env python3
"""
Debug script to test gripper functions in recording context
"""

from pymycobot.mycobot import MyCobot
import time
import threading

# Configuration
DEVICE_PORT = '/dev/ttyACM0'
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

def test_gripper_in_context(mc):
    """Test gripper functions in the same context as recording"""
    print("\n=== Testing Gripper in Recording Context ===")
    
    # Test 1: Direct gripper check
    print("1. Testing hasattr(mc, 'get_gripper_value'):")
    has_gripper = hasattr(mc, 'get_gripper_value')
    print(f"   Result: {has_gripper}")
    
    # Test 2: List all methods containing 'gripper'
    print("\n2. All methods containing 'gripper':")
    gripper_methods = [method for method in dir(mc) if 'gripper' in method.lower()]
    for method in gripper_methods:
        print(f"   - {method}")
    
    # Test 3: Try to get gripper value
    print("\n3. Testing get_gripper_value():")
    if has_gripper:
        try:
            value = mc.get_gripper_value()
            print(f"   Success! Value: {value}")
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("   Method not available")
    
    # Test 4: Test in a loop (like recording)
    print("\n4. Testing gripper in a loop (10 times):")
    for i in range(10):
        try:
            if has_gripper:
                value = mc.get_gripper_value()
                print(f"   Loop {i+1}: {value}")
            else:
                print(f"   Loop {i+1}: Method not available")
        except Exception as e:
            print(f"   Loop {i+1}: Error - {e}")
        time.sleep(0.1)
    
    # Test 5: Test with release_all_servos (like recording script)
    print("\n5. Testing after release_all_servos():")
    try:
        mc.release_all_servos()
        print("   ✓ release_all_servos() successful")
    except Exception as e:
        print(f"   ✗ release_all_servos() failed: {e}")
    
    # Test gripper again after release
    if has_gripper:
        try:
            value = mc.get_gripper_value()
            print(f"   Gripper value after release: {value}")
        except Exception as e:
            print(f"   Gripper error after release: {e}")
    
    # Test 6: Test in a thread (like recording)
    print("\n6. Testing gripper in a thread:")
    gripper_values = []
    
    def gripper_thread():
        for i in range(10):
            try:
                if has_gripper:
                    value = mc.get_gripper_value()
                    gripper_values.append(value)
                    print(f"   Thread {i+1}: {value}")
                else:
                    print(f"   Thread {i+1}: Method not available")
            except Exception as e:
                print(f"   Thread {i+1}: Error - {e}")
            time.sleep(0.1)
    
    thread = threading.Thread(target=gripper_thread)
    thread.daemon = True
    thread.start()
    thread.join()
    
    print(f"   Thread results: {gripper_values}")

def main():
    mc = connect_robot()
    if mc is None:
        return
    
    test_gripper_in_context(mc)
    
    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    main() 