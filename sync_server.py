#!/usr/bin/env python3
"""
Simple HTTP Server for Jetson-iPhone Synchronization
Receives commands from Jetson and serves them to iPhone
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import time
import threading
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for iPhone app

# Directory to store images
BASE_IMAGE_DIR = "images"
os.makedirs(BASE_IMAGE_DIR, exist_ok=True)

# Global state
current_command = None
current_task_name = None
command_timestamp = None
command_id = 0

# Thread lock for thread safety
lock = threading.Lock()

@app.route('/command', methods=['POST'])
def post_command():
    """Receive commands from Jetson (record_trace.py)"""
    global current_command, current_task_name, command_timestamp, command_id
    
    try:
        data = request.get_json()
        command = data.get('command')
        task_name = data.get('task_name', '')
        
        with lock:
            current_command = command
            current_task_name = task_name
            command_timestamp = time.time()
            command_id += 1
            
        print(f"[{datetime.now()}] Received command: {command}, task: {task_name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Command {command} received',
            'command_id': command_id
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """
    iPhone uploads an image with metadata (timestamp, command_id)
    """
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image part'}), 400
    image = request.files['image']
    timestamp = request.form.get('timestamp')
    command_id = request.form.get('command_id')
    task_name = request.form.get('task_name', '')
    if not image or not timestamp or not command_id:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    # Create task-specific subdirectory
    task_dir = os.path.join(BASE_IMAGE_DIR, task_name) if task_name else BASE_IMAGE_DIR
    os.makedirs(task_dir, exist_ok=True)

    # Save image with a unique filename (remove periods from timestamp)
    clean_timestamp = timestamp.replace('.', '')
    filename = f"{clean_timestamp}.jpg"
    filepath = os.path.join(task_dir, filename)
    image.save(filepath)

    # Also save as latest.jpg in the main images folder
    latest_filepath = os.path.join(BASE_IMAGE_DIR, "latest.jpg")
    image.seek(0)  # Reset file pointer to beginning
    image.save(latest_filepath)

    # Save metadata
    meta = {
        'filename': filename,
        'timestamp': timestamp,
        'command_id': command_id,
        'task_name': task_name,
        'task_dir': task_dir
    }
    with open(os.path.join(task_dir, filename + ".json"), "w") as f:
        json.dump(meta, f)

    # Also save latest metadata
    with open(os.path.join(BASE_IMAGE_DIR, "latest.jpg.json"), "w") as f:
        json.dump(meta, f)

    return jsonify({'status': 'success', 'filename': filename, 'task_dir': task_dir})

@app.route('/images', methods=['GET'])
def list_images():
    """
    List all uploaded images and their metadata
    """
    images = []
    # Walk through all subdirectories in the base image directory
    for root, dirs, files in os.walk(BASE_IMAGE_DIR):
        for f in files:
            if f.endswith('.jpg'):
                full_path = os.path.join(root, f)
                relative_path = os.path.relpath(full_path, BASE_IMAGE_DIR)
                meta_file = os.path.join(root, f + ".json")
                if os.path.exists(meta_file):
                    with open(meta_file) as mf:
                        meta = json.load(mf)
                else:
                    meta = {}
                images.append({'filename': f, 'relative_path': relative_path, **meta})
    return jsonify({'images': images})

@app.route('/images/<task_name>', methods=['GET'])
def list_task_images(task_name):
    """
    List all images for a specific task
    """
    task_dir = os.path.join(BASE_IMAGE_DIR, task_name)
    if not os.path.exists(task_dir):
        return jsonify({'status': 'error', 'message': f'Task {task_name} not found'}), 404
    
    images = []
    files = [f for f in os.listdir(task_dir) if f.endswith('.jpg')]
    for f in files:
        meta_file = os.path.join(task_dir, f + ".json")
        if os.path.exists(meta_file):
            with open(meta_file) as mf:
                meta = json.load(mf)
        else:
            meta = {}
        images.append({'filename': f, 'task_name': task_name, **meta})
    
    return jsonify({'task_name': task_name, 'images': images})

@app.route('/tasks', methods=['GET'])
def list_tasks():
    """
    List all available tasks (subdirectories in images folder)
    """
    tasks = []
    if os.path.exists(BASE_IMAGE_DIR):
        for item in os.listdir(BASE_IMAGE_DIR):
            item_path = os.path.join(BASE_IMAGE_DIR, item)
            if os.path.isdir(item_path):
                # Count images in this task directory
                image_count = len([f for f in os.listdir(item_path) if f.endswith('.jpg')])
                tasks.append({'task_name': item, 'image_count': image_count})
    
    return jsonify({'tasks': tasks})

@app.route('/image/<path:filepath>', methods=['GET'])
def get_image(filepath):
    """
    Download an image by filepath (can include task subdirectory)
    Examples: /image/task1/123_456.jpg or /image/123_456.jpg
    """
    # If no directory separator, search all task folders for the file
    if '/' not in filepath:
        filename = filepath
        for root, dirs, files in os.walk(BASE_IMAGE_DIR):
            if filename in files:
                return send_from_directory(root, filename)
        return jsonify({'status': 'error', 'message': 'Image not found'}), 404
    else:
        # Direct path provided
        directory, filename = os.path.split(filepath)
        full_directory = os.path.join(BASE_IMAGE_DIR, directory)
        if os.path.exists(os.path.join(full_directory, filename)):
            return send_from_directory(full_directory, filename)
        return jsonify({'status': 'error', 'message': 'Image not found'}), 404

@app.route('/latest_image', methods=['GET'])
def get_latest_image():
    """
    Get the most recently uploaded image
    """
    try:
        # Check if we have a latest.jpg file
        latest_filepath = os.path.join(BASE_IMAGE_DIR, "latest.jpg")
        latest_meta_filepath = os.path.join(BASE_IMAGE_DIR, "latest.jpg.json")
        
        if not os.path.exists(latest_filepath):
            return jsonify({'status': 'error', 'message': 'No latest image found'}), 404
        
        metadata = {}
        if os.path.exists(latest_meta_filepath):
            with open(latest_meta_filepath) as mf:
                metadata = json.load(mf)
        
        return jsonify({
            'status': 'success',
            'filename': 'latest.jpg',
            'relative_path': 'latest.jpg',
            'metadata': metadata
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/latest_image_file', methods=['GET'])
def get_latest_image_file():
    """
    Download the most recently uploaded image file
    """
    try:
        # Check if we have a latest.jpg file
        latest_filepath = os.path.join(BASE_IMAGE_DIR, "latest.jpg")
        
        if not os.path.exists(latest_filepath):
            return jsonify({'status': 'error', 'message': 'No latest image found'}), 404
            
        return send_from_directory(BASE_IMAGE_DIR, "latest.jpg")
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get current status for iPhone app"""
    global current_command, current_task_name, command_timestamp, command_id
    
    with lock:
        return jsonify({
            'command': current_command,
            'task_name': current_task_name,
            'timestamp': command_timestamp,
            'command_id': command_id,
            'server_time': time.time()
        })

@app.route('/poll', methods=['GET'])
def poll_command():
    """Poll for new commands (iPhone app calls this repeatedly)"""
    global current_command, current_task_name, command_timestamp, command_id
    
    # Get the last command ID the client has seen
    last_seen_id = request.args.get('last_id', 0, type=int)
    
    with lock:
        if command_id > last_seen_id:
            # New command available
            return jsonify({
                'new_command': True,
                'command': current_command,
                'task_name': current_task_name,
                'timestamp': command_timestamp,
                'command_id': command_id,
                'server_time': time.time()
            })
        else:
            # No new command
            return jsonify({
                'new_command': False,
                'command_id': command_id,
                'server_time': time.time()
            })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'server_time': time.time(),
        'uptime': time.time() - start_time
    })

if __name__ == '__main__':
    start_time = time.time()
    print("Starting sync server...")
    print("Endpoints:")
    print("  POST /command - Jetson sends commands")
    print("  GET  /status  - Get current status")
    print("  GET  /poll    - Poll for new commands")
    print("  GET  /health  - Health check")
    print("  POST /upload_image - iPhone uploads images")
    print("  GET  /tasks - List all available tasks")
    print("  GET  /images - List all images")
    print("  GET  /images/<task_name> - List images for specific task")
    print("  GET  /image/<filepath> - Download image (supports task subdirectories)")
    print("  GET  /latest_image - Get latest image metadata")
    print("  GET  /latest_image_file - Download latest image file")
    
    # Run on all interfaces, port 5512
    app.run(host='0.0.0.0', port=5512, debug=False, threaded=True) 
