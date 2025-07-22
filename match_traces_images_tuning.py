#!/usr/bin/env python3
"""
Script to match trace timestamps with image timestamps for tuning_data format.
Fills the 'image' field in each trace entry with the best matching image filename.

Usage:
    python3 match_traces_images_tuning.py <episode_number> [--tolerance <ms>] [--overwrite-original]
    
Examples:
    python3 match_traces_images_tuning.py 1
    python3 match_traces_images_tuning.py 1 --tolerance 300
    python3 match_traces_images_tuning.py 1 --overwrite-original
"""

import json
import os
import glob
import argparse
import sys
from typing import Dict, List, Optional

def load_image_timestamps(images_dir: str) -> Dict[int, str]:
    """
    Load all image metadata files and extract timestamps.
    Returns a dictionary mapping timestamp_ms to image filename.
    """
    image_timestamps = {}
    
    if not os.path.exists(images_dir):
        print(f"❌ Images directory not found: {images_dir}")
        return image_timestamps
    
    # Find all .json metadata files
    json_files = glob.glob(os.path.join(images_dir, "*.jpg.json"))
    
    if not json_files:
        print(f"❌ No image metadata files found in: {images_dir}")
        return image_timestamps
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                metadata = json.load(f)
                
            # Convert timestamp from string seconds to integer milliseconds
            timestamp_seconds = float(metadata['timestamp'])
            timestamp_ms = int(timestamp_seconds * 1000)  # Convert to milliseconds
            
            image_timestamps[timestamp_ms] = metadata['filename']
        except Exception as e:
            print(f"⚠️ Error reading {json_file}: {e}")
    
    return image_timestamps

def find_closest_image(trace_timestamp_ms: int, image_timestamps: Dict[int, str], max_tolerance_ms: int = 200) -> Optional[str]:
    """
    Find the closest image timestamp to the given trace timestamp.
    Returns the image filename if within tolerance, None otherwise.
    """
    if not image_timestamps:
        return None
        
    closest_timestamp = None
    closest_filename = None
    min_diff = float('inf')
    
    for img_timestamp_ms, filename in image_timestamps.items():
        diff = abs(trace_timestamp_ms - img_timestamp_ms)
        if diff < min_diff:
            min_diff = diff
            closest_timestamp = img_timestamp_ms
            closest_filename = filename
    
    # Only return if within tolerance
    if min_diff <= max_tolerance_ms:
        return closest_filename
    else:
        return None

def match_traces_with_images(episode_number: int, max_tolerance_ms: int = 200, overwrite_original: bool = False):
    """
    Main function to match traces with images for a given episode.
    """
    # Paths for tuning_data structure
    base_dir = f"tuning_data/run-traces-images/{episode_number}"
    trace_file = f"{base_dir}/trace-{episode_number}.json"
    images_dir = f"{base_dir}/images-{episode_number}"
    
    if overwrite_original:
        output_file = trace_file
    else:
        output_file = f"{base_dir}/trace-{episode_number}_matched.json"
    
    print(f"Processing episode: {episode_number}")
    print(f"Trace file: {trace_file}")
    print(f"Images directory: {images_dir}")
    
    # Check if trace file exists
    if not os.path.exists(trace_file):
        print(f"❌ Trace file not found: {trace_file}")
        return None, 0
    
    # Load image timestamps
    print("Loading image timestamps...")
    image_timestamps = load_image_timestamps(images_dir)
    
    if not image_timestamps:
        print("❌ No images found to match with")
        return None, 0
        
    print(f"Found {len(image_timestamps)} images")
    
    # Load trace data
    print(f"\nLoading trace data from {trace_file}...")
    try:
        with open(trace_file, 'r') as f:
            trace_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading trace file: {e}")
        return None, 0
    
    if 'trace' not in trace_data:
        print("❌ No 'trace' field found in trace data")
        return None, 0
    
    # Match traces with images
    print(f"\nMatching traces with images (tolerance: {max_tolerance_ms}ms)...")
    matched_count = 0
    total_traces = len(trace_data['trace'])
    
    for i, trace_entry in enumerate(trace_data['trace']):
        if 'timestamp_ms' not in trace_entry:
            print(f"  Trace {i+1}: No timestamp found, skipping")
            continue
            
        trace_timestamp = trace_entry['timestamp_ms']
        
        # Find closest image
        matched_image = find_closest_image(trace_timestamp, image_timestamps, max_tolerance_ms)
        
        if matched_image:
            trace_entry['image'] = matched_image
            matched_count += 1
            # Calculate the actual difference for reporting
            img_timestamp = None
            for ts_ms, filename in image_timestamps.items():
                if filename == matched_image:
                    img_timestamp = ts_ms
                    break
            diff = abs(trace_timestamp - img_timestamp) if img_timestamp else 0
            print(f"  Trace {i+1} (t={trace_timestamp}) -> {matched_image} (diff: {diff}ms)")
        else:
            trace_entry['image'] = None
            # Only print first few misses to avoid clutter
            if i < 5 or i > total_traces - 5:
                print(f"  Trace {i+1} (t={trace_timestamp}) -> No match within tolerance")
            elif i == 5:
                print("  ... (skipping further no-match messages) ...")
    
    print(f"\nMatched {matched_count} out of {total_traces} traces with images")
    
    # Save updated trace data
    try:
        with open(output_file, 'w') as f:
            json.dump(trace_data, f, indent=2)
        print(f"\nUpdated trace data saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error saving updated trace data: {e}")
        return None, 0
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Episode: {episode_number}")
    print(f"  Total traces: {total_traces}")
    print(f"  Total images: {len(image_timestamps)}")
    print(f"  Matched: {matched_count}")
    print(f"  Unmatched: {total_traces - matched_count}")
    print(f"  Match rate: {matched_count/total_traces*100:.1f}%")
    print(f"  Tolerance: {max_tolerance_ms}ms")
    
    return trace_data, matched_count

def main():
    parser = argparse.ArgumentParser(
        description="Match trace timestamps with image timestamps for tuning_data format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 match_traces_images_tuning.py 1
  python3 match_traces_images_tuning.py 1 --tolerance 300
  python3 match_traces_images_tuning.py 1 --overwrite-original
        """
    )
    
    parser.add_argument(
        "episode_number",
        type=int,
        help="Episode number to process (e.g., 1, 2, 3...)"
    )
    
    parser.add_argument(
        "--tolerance",
        type=int,
        default=200,
        help="Maximum time difference in milliseconds for matching (default: 200)"
    )
    
    parser.add_argument(
        "--overwrite-original",
        action="store_true",
        help="Overwrite the original trace file instead of creating a new one"
    )
    
    args = parser.parse_args()
    
    if args.tolerance < 0:
        print("❌ Tolerance must be a positive number")
        sys.exit(1)
    
    try:
        trace_data, matched_count = match_traces_with_images(
            args.episode_number, 
            args.tolerance, 
            args.overwrite_original
        )
        
        if trace_data is not None:
            print(f"\n✅ Successfully processed episode {args.episode_number}")
            sys.exit(0)
        else:
            print(f"\n❌ Failed to process episode {args.episode_number}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error processing episode {args.episode_number}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()