#!/usr/bin/env python3
"""
Split the dataset into two separate datasets based on episode type:
1. numbered_episodes: Episodes with numeric names (11, 12, 13, etc.)
2. auto_recorded_episodes: Episodes with timestamp names (20250722...)
"""

import json
import shutil
from pathlib import Path
from typing import List, Tuple

def categorize_episodes(traces_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Categorize trace files into numbered vs auto-recorded episodes."""
    numbered = []
    auto_recorded = []
    
    for json_file in traces_dir.glob("*.json"):
        episode_name = json_file.stem
        
        # Check if episode name is purely numeric
        if episode_name.isdigit() and len(episode_name) <= 3:
            numbered.append(json_file)
        elif episode_name.startswith("2025"):
            auto_recorded.append(json_file)
        else:
            print(f"Warning: Skipping unrecognized episode format: {episode_name}")
    
    return numbered, auto_recorded

def create_split_datasets(numbered_episodes: List[Path], auto_recorded_episodes: List[Path]):
    """Create two separate trace directories for the split datasets."""
    # Create output directories
    numbered_dir = Path("traces_matched_numbered")
    auto_dir = Path("traces_matched_autorecorded")
    
    # Clean and recreate directories
    for dir_path in [numbered_dir, auto_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir(exist_ok=True)
    
    # Copy numbered episodes
    print(f"\nCopying {len(numbered_episodes)} numbered episodes...")
    for trace_file in numbered_episodes:
        shutil.copy2(trace_file, numbered_dir / trace_file.name)
        print(f"  Copied: {trace_file.name}")
    
    # Copy auto-recorded episodes
    print(f"\nCopying {len(auto_recorded_episodes)} auto-recorded episodes...")
    for trace_file in auto_recorded_episodes:
        shutil.copy2(trace_file, auto_dir / trace_file.name)
        print(f"  Copied: {trace_file.name}")
    
    # Create metadata files
    numbered_meta = {
        "dataset_type": "numbered_episodes",
        "description": "Robot demonstrations with simple numeric task identifiers",
        "episode_count": len(numbered_episodes),
        "episodes": [f.stem for f in numbered_episodes]
    }
    
    auto_meta = {
        "dataset_type": "auto_recorded_episodes", 
        "description": "Robot demonstrations with timestamp-based identifiers",
        "episode_count": len(auto_recorded_episodes),
        "episodes": [f.stem for f in auto_recorded_episodes]
    }
    
    with open(numbered_dir / "dataset_metadata.json", "w") as f:
        json.dump(numbered_meta, f, indent=2)
    
    with open(auto_dir / "dataset_metadata.json", "w") as f:
        json.dump(auto_meta, f, indent=2)
    
    return numbered_dir, auto_dir

def main():
    traces_dir = Path("traces_matched")
    
    if not traces_dir.exists():
        print(f"Error: {traces_dir} directory not found!")
        return
    
    print(f"Analyzing episodes in {traces_dir}...")
    numbered, auto_recorded = categorize_episodes(traces_dir)
    
    print(f"\nFound:")
    print(f"  - {len(numbered)} numbered episodes")
    print(f"  - {len(auto_recorded)} auto-recorded episodes")
    print(f"  - Total: {len(numbered) + len(auto_recorded)} episodes")
    
    # Create split datasets
    numbered_dir, auto_dir = create_split_datasets(numbered, auto_recorded)
    
    print(f"\nDatasets created:")
    print(f"  - {numbered_dir}: {len(numbered)} episodes")
    print(f"  - {auto_dir}: {len(auto_recorded)} episodes")
    
    # Print sample language instructions from each type
    print("\nSample language instructions:")
    
    if numbered:
        with open(numbered[0]) as f:
            data = json.load(f)
            desc = data['metadata'].get('description', data['metadata'].get('task_name', 'Unknown'))
            print(f"  Numbered example ({numbered[0].stem}): \"{desc}\"")
    
    if auto_recorded:
        with open(auto_recorded[0]) as f:
            data = json.load(f)
            desc = data['metadata'].get('description', data['metadata'].get('task_name', 'Unknown'))
            print(f"  Auto-recorded example ({auto_recorded[0].stem}): \"{desc}\"")

if __name__ == "__main__":
    main()