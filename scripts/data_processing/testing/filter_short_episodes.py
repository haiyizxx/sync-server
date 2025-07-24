#!/usr/bin/env python3
"""
Filter out episodes that are too short for OpenVLA finetuning.
"""

import sys
import shutil
from pathlib import Path
import json

def filter_short_episodes(source_dir, output_dir, min_length=15):
    """Filter episodes shorter than min_length steps."""
    
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    # Create output directory
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Get all JSON files
    json_files = list(source_path.glob("*.json"))
    json_files = [f for f in json_files if f.name != 'dataset_metadata.json']
    
    print(f"Found {len(json_files)} episodes in {source_dir}")
    
    kept_episodes = 0
    filtered_episodes = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check episode length
            trace = data.get('trace', [])
            episode_length = len(trace)
            
            if episode_length >= min_length:
                # Copy to output directory
                output_file = output_path / json_file.name
                shutil.copy2(json_file, output_file)
                kept_episodes += 1
                print(f"✓ Kept episode {json_file.stem}: {episode_length} steps")
            else:
                filtered_episodes += 1
                print(f"✗ Filtered episode {json_file.stem}: {episode_length} steps (< {min_length})")
                
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            filtered_episodes += 1
    
    # Copy metadata file if it exists
    metadata_file = source_path / "dataset_metadata.json"
    if metadata_file.exists():
        output_metadata = output_path / "dataset_metadata.json"
        
        # Update metadata
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Update episode count
            metadata['episodes'] = kept_episodes
            metadata['description'] = f"Filtered autorecorded episodes (min {min_length} steps)"
            
            with open(output_metadata, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"Error updating metadata: {e}")
            shutil.copy2(metadata_file, output_metadata)
    
    print(f"\nFiltering complete:")
    print(f"  Kept: {kept_episodes} episodes")
    print(f"  Filtered: {filtered_episodes} episodes")
    print(f"  Output: {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python filter_short_episodes.py <source_dir> <output_dir> [min_length]")
        print("Example: python filter_short_episodes.py ../traces_matched_to_images_autorecorded ../traces_matched_to_images_autorecorded_filtered 15")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]
    min_length = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    
    filter_short_episodes(source_dir, output_dir, min_length)