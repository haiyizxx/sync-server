#!/usr/bin/env python3
"""
Combined script to match traces with images and split by episode type.
Handles both numbered episodes (1, 2, 3...) and date-formatted episodes (20250722155656).
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def load_image_timestamps(images_dir: Path) -> Dict[int, str]:
    """
    Load all image metadata files and extract timestamps.
    Returns a dictionary mapping timestamp_ms to image filename.
    """
    image_timestamps = {}
    
    if not images_dir.exists():
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


def classify_episode(episode_name: str) -> str:
    """Classify episode as 'numbered', 'autorecorded', or 'unknown'."""
    if episode_name.isdigit() and len(episode_name) <= 3:
        return 'numbered'
    elif episode_name.startswith('2025') or episode_name.startswith('2024'):
        return 'autorecorded'
    else:
        return 'unknown'


def get_hardcoded_description_for_numbered_episode(episode_number: int) -> str:
    """Get hardcoded description for numbered episodes."""
    return 'can you find the lego piece, pick it up, and move it from right to left?'


def process_all_episodes():
    """Match all traces with images and split into numbered/autorecorded datasets."""
    
    # Base directory
    base_dir = Path(__file__).parent.parent.parent
    
    # Create output directories
    all_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_all'
    numbered_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_numbered'
    auto_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_autorecorded'
    
    for dir_path in [all_dir, numbered_dir, auto_dir]:
        dir_path.mkdir(exist_ok=True, parents=True)
    
    # Get all trace files
    traces_dir = base_dir / 'data' / 'raw' / 'traces'
    trace_files = sorted(traces_dir.glob("*.json"))
    
    if not trace_files:
        print("❌ No trace files found in traces/ folder")
        return
    
    print(f"Found {len(trace_files)} trace files to process")
    
    # Track statistics
    stats = {
        'numbered': {'count': 0, 'matched': 0, 'total_steps': 0},
        'autorecorded': {'count': 0, 'matched': 0, 'total_steps': 0},
        'unknown': {'count': 0, 'matched': 0, 'total_steps': 0}
    }
    
    for trace_file in trace_files:
        episode_name = trace_file.stem
        episode_type = classify_episode(episode_name)
        
        print(f"\n{'='*60}")
        print(f"Processing {episode_type} episode: {episode_name}")
        
        # Load trace data
        try:
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading trace file: {e}")
            continue
        
        # Determine image directory based on episode type
        if episode_type == 'numbered':
            images_dir = base_dir / 'data' / 'raw' / 'images' / episode_name
        elif episode_type == 'autorecorded':
            # For date-formatted episodes, images might be in a directory with the same name
            images_dir = base_dir / 'data' / 'raw' / 'images' / episode_name
        else:
            print(f"⚠️ Unknown episode type, skipping: {episode_name}")
            stats['unknown']['count'] += 1
            continue
        
        # Load image timestamps
        image_timestamps = load_image_timestamps(images_dir)
        
        if not image_timestamps:
            print(f"⚠️ No images found for episode {episode_name}, skipping completely")
            continue
        
        print(f"Found {len(image_timestamps)} images")
        
        # Match traces with images using distribution algorithm
        trace_data, mean_offset, std_dev = distribute_images_to_trace(trace_data, image_timestamps)
        
        # Update description with wrapper for all episodes
        if 'metadata' not in trace_data:
            trace_data['metadata'] = {}
        
        # Get the current description
        if episode_type == 'numbered':
            episode_num = int(episode_name)
            current_description = get_hardcoded_description_for_numbered_episode(episode_num)
        else:
            current_description = trace_data['metadata'].get('description', 'no description found')
        
        # Wrap the description with the robot context
        wrapped_description = f'We use a myCobot 280 robot arm with six degrees of freedom and a gripper. These are the movement instructions: "{current_description}"'
        trace_data['metadata']['description'] = wrapped_description
        
        # Update statistics
        if 'trace' in trace_data:
            trace_count = len(trace_data['trace'])
            matched_count = sum(1 for step in trace_data['trace'] if step.get('image') is not None)
            stats[episode_type]['count'] += 1
            stats[episode_type]['total_steps'] += trace_count
            stats[episode_type]['matched'] += matched_count
            
            print(f"Matched {matched_count}/{trace_count} steps ({matched_count/trace_count*100:.1f}%)")
            if mean_offset is not None:
                print(f"Mean offset: {mean_offset:.1f}ms, Std dev: {std_dev:.1f}ms")
        
        # Save to all episodes directory
        output_file = all_dir / f"{episode_name}.json"
        with open(output_file, 'w') as f:
            json.dump(trace_data, f, indent=2)
        
        # Also save to type-specific directory
        if episode_type == 'numbered':
            type_output = numbered_dir / f"{episode_name}.json"
        else:  # autorecorded
            type_output = auto_dir / f"{episode_name}.json"
        
        with open(type_output, 'w') as f:
            json.dump(trace_data, f, indent=2)
        
        print(f"Saved to: {output_file} and {type_output}")
    
    # Create metadata files
    create_metadata_files(numbered_dir, auto_dir, stats)
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for episode_type in ['numbered', 'autorecorded', 'unknown']:
        s = stats[episode_type]
        if s['count'] > 0:
            print(f"\n{episode_type.capitalize()} episodes:")
            print(f"  Episodes: {s['count']}")
            print(f"  Total steps: {s['total_steps']}")
            print(f"  Matched steps: {s['matched']}")
            if s['total_steps'] > 0:
                print(f"  Match rate: {s['matched']/s['total_steps']*100:.1f}%")
    
    total_episodes = sum(s['count'] for s in stats.values())
    total_steps = sum(s['total_steps'] for s in stats.values())
    total_matched = sum(s['matched'] for s in stats.values())
    
    print(f"\nTotal:")
    print(f"  Episodes processed: {total_episodes}")
    print(f"  Total steps: {total_steps}")
    print(f"  Total matched: {total_matched}")
    if total_steps > 0:
        print(f"  Overall match rate: {total_matched/total_steps*100:.1f}%")


def create_metadata_files(numbered_dir: Path, auto_dir: Path, stats: dict):
    """Create metadata files for each dataset type."""
    
    # Numbered episodes metadata
    numbered_meta = {
        "dataset_type": "numbered_episodes",
        "description": "Robot demonstrations with simple numeric task identifiers",
        "episodes": stats['numbered']['count'],
        "total_steps": stats['numbered']['total_steps'],
        "matched_steps": stats['numbered']['matched'],
        "match_rate": stats['numbered']['matched'] / stats['numbered']['total_steps'] * 100 if stats['numbered']['total_steps'] > 0 else 0,
        "task_mapping": {
            "1-10": "Pick and place tasks",
            "11-20": "Stacking tasks",
            "21-30": "Sorting tasks",
            "31-40": "Assembly tasks",
            "41-50": "Manipulation tasks",
            "51-57": "Complex sequences"
        }
    }
    
    with open(numbered_dir / "dataset_metadata.json", 'w') as f:
        json.dump(numbered_meta, f, indent=2)
    
    # Auto-recorded episodes metadata
    auto_meta = {
        "dataset_type": "auto_recorded_episodes",
        "description": "Robot demonstrations with timestamp-based identifiers from rapid recording sessions",
        "episodes": stats['autorecorded']['count'],
        "total_steps": stats['autorecorded']['total_steps'],
        "matched_steps": stats['autorecorded']['matched'],
        "match_rate": stats['autorecorded']['matched'] / stats['autorecorded']['total_steps'] * 100 if stats['autorecorded']['total_steps'] > 0 else 0,
        "recording_format": "YYYYMMDDHHMMSS",
        "recording_date": "2025-07-22",
        "recording_method": "Keyboard-controlled rapid recording (record_trace_keyboard.py)"
    }
    
    with open(auto_dir / "dataset_metadata.json", 'w') as f:
        json.dump(auto_meta, f, indent=2)
    
    print("\n✅ Created metadata files for both dataset types")


if __name__ == "__main__":
    process_all_episodes()