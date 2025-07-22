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
IMAGE_DIR = "uploaded_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

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

    # Save image with a unique filename
    filename = f"{task_name}_{command_id}_{timestamp}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    image.save(filepath)

    # Save metadata
    meta = {
        'filename': filename,
        'timestamp': timestamp,
        'command_id': command_id,
        'task_name': task_name
    }
    with open(os.path.join(IMAGE_DIR, filename + ".json"), "w") as f:
        json.dump(meta, f)

    return jsonify({'status': 'success', 'filename': filename})

@app.route('/images', methods=['GET'])
def list_images():
    """
    List all uploaded images and their metadata
    """
    files = [f for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg')]
    images = []
    for f in files:
        meta_file = os.path.join(IMAGE_DIR, f + ".json")
        if os.path.exists(meta_file):
            with open(meta_file) as mf:
                meta = json.load(mf)
        else:
            meta = {}
        images.append({'filename': f, **meta})
    return jsonify({'images': images})

@app.route('/image/<filename>', methods=['GET'])
def get_image(filename):
    """
    Download an image by filename
    """
    return send_from_directory(IMAGE_DIR, filename)

@app.route('/latest_image', methods=['GET'])
def get_latest_image():
    """
    Get the most recently uploaded image
    """
    try:
        # Get all jpg files
        files = [f for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg')]
        
        if not files:
            return jsonify({'status': 'error', 'message': 'No images found'}), 404
        
        # Sort files by modification time (newest first)
        files_with_time = []
        for f in files:
            filepath = os.path.join(IMAGE_DIR, f)
            mod_time = os.path.getmtime(filepath)
            files_with_time.append((f, mod_time))
        
        # Get the most recent file
        latest_file = max(files_with_time, key=lambda x: x[1])[0]
        
        # Get metadata if available
        meta_file = os.path.join(IMAGE_DIR, latest_file + ".json")
        metadata = {}
        if os.path.exists(meta_file):
            with open(meta_file) as mf:
                metadata = json.load(mf)
        
        return jsonify({
            'status': 'success',
            'filename': latest_file,
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
        # Get all jpg files
        files = [f for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg')]
        
        if not files:
            return jsonify({'status': 'error', 'message': 'No images found'}), 404
        
        # Sort files by modification time (newest first)
        files_with_time = []
        for f in files:
            filepath = os.path.join(IMAGE_DIR, f)
            mod_time = os.path.getmtime(filepath)
            files_with_time.append((f, mod_time))
        
        # Get the most recent file
        latest_file = max(files_with_time, key=lambda x: x[1])[0]
        
        # Return the actual image file
        return send_from_directory(IMAGE_DIR, latest_file)
        
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
    print("  GET  /images - List images")
    print("  GET  /image/<filename> - Download image")
    
    # Run on all interfaces, port 5512
    app.run(host='0.0.0.0', port=5512, debug=False, threaded=True) 
