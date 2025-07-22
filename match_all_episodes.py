#!/usr/bin/env python3
"""
Script to match traces with images for all episodes in tuning_data.
"""

import subprocess
import os
import sys

def main():
    # Find all episode directories
    base_dir = "tuning_data/run-traces-images"
    
    if not os.path.exists(base_dir):
        print(f"❌ Directory not found: {base_dir}")
        sys.exit(1)
    
    # Get all numbered directories
    episodes = []
    for item in os.listdir(base_dir):
        if item.isdigit():
            episodes.append(int(item))
    
    if not episodes:
        print("❌ No episode directories found")
        sys.exit(1)
    
    episodes.sort()
    print(f"Found {len(episodes)} episodes: {episodes}")
    
    # Process each episode
    successful = 0
    failed = 0
    
    for episode in episodes:
        print(f"\n{'='*60}")
        print(f"Processing episode {episode}...")
        print(f"{'='*60}")
        
        # Run the matching script with 500ms tolerance and overwrite original
        cmd = ["python3", "match_traces_images_tuning.py", str(episode), 
               "--tolerance", "500", "--overwrite-original"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Episode {episode} processed successfully")
                # Extract match rate from output
                for line in result.stdout.split('\n'):
                    if "Match rate:" in line:
                        print(f"   {line.strip()}")
                successful += 1
            else:
                print(f"❌ Episode {episode} failed")
                print("Error output:", result.stderr)
                failed += 1
        except Exception as e:
            print(f"❌ Error processing episode {episode}: {e}")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total episodes: {len(episodes)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ All episodes processed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failed} episodes failed")
        sys.exit(1)

if __name__ == "__main__":
    main()