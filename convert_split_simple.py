#!/usr/bin/env python3
"""
Simple conversion script for split datasets.
Usage:
    python convert_split_simple.py numbered
    python convert_split_simple.py autorecorded
"""

import sys
import os
import subprocess
from pathlib import Path
import shutil

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['numbered', 'autorecorded']:
        print("Usage: python convert_split_simple.py [numbered|autorecorded]")
        sys.exit(1)
    
    dataset_type = sys.argv[1]
    source_dir = f"traces_matched_{dataset_type}"
    target_dir = "traces_matched"
    output_dir = f"rlds_dataset_{dataset_type}"
    
    # Backup existing traces_matched if it exists
    if Path(target_dir).exists():
        backup_dir = f"{target_dir}_backup"
        if Path(backup_dir).exists():
            shutil.rmtree(backup_dir)
        shutil.move(target_dir, backup_dir)
    
    # Copy split dataset to traces_matched
    shutil.copytree(source_dir, target_dir)
    
    # Remove dataset_metadata.json if it exists
    metadata_file = Path(target_dir) / "dataset_metadata.json"
    if metadata_file.exists():
        metadata_file.unlink()
    
    # Backup existing rlds_dataset if it exists
    if Path("rlds_dataset").exists():
        if Path(output_dir).exists():
            shutil.rmtree(output_dir)
        shutil.move("rlds_dataset", output_dir)
    
    # Run conversion
    print(f"\nConverting {dataset_type} episodes...")
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)
    
    result = subprocess.run([
        sys.executable, 
        "convert_trace_to_rlds.py"
    ], env=env)
    
    # Move output to specific directory
    if Path("rlds_dataset").exists():
        if Path(output_dir).exists():
            shutil.rmtree(output_dir)
        shutil.move("rlds_dataset", output_dir)
    
    # Restore original traces_matched
    shutil.rmtree(target_dir)
    if Path(f"{target_dir}_backup").exists():
        shutil.move(f"{target_dir}_backup", target_dir)
    
    if result.returncode == 0:
        print(f"\nSuccessfully created dataset at: {output_dir}/")
    else:
        print(f"\nConversion failed with return code: {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()