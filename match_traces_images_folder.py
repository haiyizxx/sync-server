#!/usr/bin/env python3
"""
Script to match traces with images and create matched output files.

Reads traces from traces/ folder and matches them with images from images/ folder,
then outputs the matched traces to traces_matched/ folder.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

def load_image_timestamps(images_dir: Path) -> Dict[int, str]:
    """
    Load all image metadata files and extract timestamps.
    Returns a dictionary mapping timestamp_ms to image filename.
    """
    image_timestamps = {}
    
    if not images_dir.exists():
        print(f"❌ Images directory not found: {images_dir}")
        return image_timestamps
    
    # Find all .json metadata files
    for json_file in images_dir.glob("*.jpg.json"):
        try:
            with open(json_file, 'r') as f:
                metadata = json.load(f)
                
            # Convert timestamp from string seconds to integer milliseconds
            timestamp_seconds = float(metadata['timestamp'])
            timestamp_ms = int(timestamp_seconds * 1000)
            
            image_timestamps[timestamp_ms] = metadata['filename']
        except Exception as e:
            print(f"⚠️ Error reading {json_file}: {e}")
    
    return image_timestamps

def distribute_images_to_trace(trace_data: dict, image_timestamps: Dict[int, str]) -> tuple:
    """
    Distribute available images across the trace timeline.
    Maps images to trace steps based on relative timing, ensuring even distribution.
    Returns (updated_trace_data, mean_offset, std_dev_after_offset)
    """
    if not image_timestamps or 'trace' not in trace_data or not trace_data['trace']:
        return trace_data, None, None
    
    # Get trace timeline
    trace_steps = trace_data['trace']
    trace_timestamps = []
    valid_indices = []
    
    for i, step in enumerate(trace_steps):
        if 'timestamp_ms' in step:
            trace_timestamps.append(step['timestamp_ms'])
            valid_indices.append(i)
    
    if not trace_timestamps:
        return trace_data, None, None
    
    # Get sorted images
    sorted_images = sorted(image_timestamps.items())
    
    # Calculate ranges
    trace_start = min(trace_timestamps)
    trace_end = max(trace_timestamps)
    trace_duration = trace_end - trace_start
    
    img_start = sorted_images[0][0]
    img_end = sorted_images[-1][0]
    img_duration = img_end - img_start
    
    # Map each image to the best matching trace step based on relative position
    image_assignments = {}
    raw_offsets = []  # For calculating mean offset
    
    for img_ts, img_filename in sorted_images:
        # Calculate relative position of image in its timeline (0-1)
        if img_duration > 0:
            img_relative_pos = (img_ts - img_start) / img_duration
        else:
            img_relative_pos = 0.5
        
        # Find corresponding position in trace timeline
        target_trace_ts = trace_start + (img_relative_pos * trace_duration)
        
        # Find closest trace step
        best_idx = None
        min_diff = float('inf')
        best_trace_ts = None
        
        for i, trace_ts in zip(valid_indices, trace_timestamps):
            diff = abs(trace_ts - target_trace_ts)
            if diff < min_diff:
                min_diff = diff
                best_idx = i
                best_trace_ts = trace_ts
        
        if best_idx is not None:
            image_assignments[best_idx] = img_filename
            # Calculate raw offset for this image-trace pair
            raw_offset = img_ts - best_trace_ts
            raw_offsets.append(raw_offset)
    
    # Calculate mean offset and standard deviation
    if raw_offsets:
        mean_offset = sum(raw_offsets) / len(raw_offsets)
        # Calculate std dev after removing mean offset
        variance = sum((offset - mean_offset) ** 2 for offset in raw_offsets) / len(raw_offsets)
        std_dev = variance ** 0.5
    else:
        mean_offset = None
        std_dev = None
    
    # Apply image assignments and fill gaps
    last_image = None
    matched_count = 0
    for i, step in enumerate(trace_steps):
        if i in image_assignments:
            step['image'] = image_assignments[i]
            last_image = image_assignments[i]
            matched_count += 1
        else:
            # Keep the same image as previous step if no new assignment
            step['image'] = last_image
            if last_image is not None:
                matched_count += 1
    
    return trace_data, mean_offset, std_dev

def match_all_traces():
    """Match all traces with images and save to traces_matched folder."""
    
    # Create output directory
    output_dir = Path("traces_matched")
    output_dir.mkdir(exist_ok=True)
    
    # Get all trace files
    traces_dir = Path("traces")
    trace_files = sorted([f for f in traces_dir.glob("*.json") if f.stem.isdigit()])
    
    if not trace_files:
        print("❌ No numbered trace files found in traces/ folder")
        return
    
    print(f"Found {len(trace_files)} trace files to process")
    
    total_steps = 0
    total_matched = 0
    
    for trace_file in trace_files:
        episode_num = trace_file.stem
        print(f"\n{'='*60}")
        print(f"Processing episode {episode_num}...")
        
        # Load trace data
        try:
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading trace file: {e}")
            continue
        
        # Load image timestamps for this episode
        images_dir = Path("images") / episode_num
        image_timestamps = load_image_timestamps(images_dir)
        
        if not image_timestamps:
            print(f"❌ No images found for episode {episode_num}")
            # Still save the trace without images
            output_file = output_dir / f"{episode_num}.json"
            with open(output_file, 'w') as f:
                json.dump(trace_data, f, indent=2)
            continue
        
        print(f"Found {len(image_timestamps)} images")
        
        # Match traces with images using distribution algorithm
        trace_data, mean_offset, std_dev = distribute_images_to_trace(trace_data, image_timestamps)
        
        if 'trace' in trace_data:
            trace_count = len(trace_data['trace'])
            matched_count = sum(1 for step in trace_data['trace'] if step.get('image') is not None)
            total_steps += trace_count
            total_matched += matched_count
            
            print(f"Matched {matched_count}/{trace_count} steps ({matched_count/trace_count*100:.1f}%)")
            if mean_offset is not None:
                print(f"Mean offset: {mean_offset:.1f}ms, Std dev: {std_dev:.1f}ms")
        
        # Save matched trace
        output_file = output_dir / f"{episode_num}.json"
        with open(output_file, 'w') as f:
            json.dump(trace_data, f, indent=2)
        
        print(f"Saved matched trace to: {output_file}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total episodes processed: {len(trace_files)}")
    print(f"Total steps: {total_steps}")
    print(f"Total matched: {total_matched}")
    if total_steps > 0:
        print(f"Overall match rate: {total_matched/total_steps*100:.1f}%")

if __name__ == "__main__":
    match_all_traces()