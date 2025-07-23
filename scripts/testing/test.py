from pymycobot.mycobot import MyCobot
import time

# Replace '/dev/ttyACM0' with your actual device path
try:
    mc = MyCobot('/dev/ttyACM0', 115200)  # Default baud rate
    print("Connected to myCobot!")
    
    # Test basic communication
    angles = mc.get_angles()
    print(f"Current angles: {angles}")
    
    # Test movement (small safe movement)
    mc.send_angle(1, 10, 20)  # Move joint 1 to 10 degrees at speed 20
    time.sleep(2)
    mc.send_angle(1, 0, 20)   # Return to 0 degrees
    
    print("Connection test successful!")
    
except Exception as e:
    print(f"Connection failed: {e}")
    print("Try checking:")
    print("- Cable connection")
    print("- Device permissions: sudo chmod 666 /dev/ttyUSB0")
    print("- Different baud rates: 9600, 57600, 115200")

