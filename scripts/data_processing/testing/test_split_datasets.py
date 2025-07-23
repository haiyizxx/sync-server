#!/usr/bin/env python3
"""Test the split datasets to ensure they load correctly."""

import tensorflow_datasets as tfds
import sys
import argparse
from pathlib import Path
import numpy as np

def test_dataset(dataset_dir, dataset_name, verbose=False):
    """Test loading a specific dataset."""
    print(f"\n{'='*60}")
    print(f"Testing {dataset_name}")
    print(f"Dataset directory: {dataset_dir}")
    print('='*60)
    
    try:
        # Load the dataset
        ds = tfds.load(
            'rlds_dataset_converter',
            data_dir=dataset_dir,
            split='train'
        )
        print("✓ Dataset loaded successfully!")
        
        # Count episodes
        episode_count = 0
        total_steps = 0
        
        for i, episode in enumerate(ds):
            episode_count += 1
            
            # Count steps in this episode
            steps_in_episode = 0
            for step in episode['steps']:
                steps_in_episode += 1
                total_steps += 1
            
            # Print first few episodes
            if i < 3:
                metadata = episode['episode_metadata']
                print(f"\nEpisode {i}:")
                print(f"  Task name: {metadata['task_name'].numpy().decode()}")
                print(f"  Duration: {metadata['duration_seconds'].numpy():.2f}s")
                print(f"  Steps: {steps_in_episode}")
                
                # Get first step to check language instruction
                first_step = next(iter(episode['steps'].take(1)))
                lang = first_step['language_instruction'].numpy().decode()
                print(f"  Language instruction: '{lang}'")
                
                # Show detailed step information if verbose
                if verbose and i == 0:  # Only show for first episode
                    print("\n  Detailed step information:")
                    for j, step in enumerate(episode['steps'].take(3)):
                        print(f"\n    Step {j}:")
                        # Show actual image data (first few pixels)
                        image = step['observation']['image'].numpy()
                        print(f"      Image shape: {image.shape}")
                        print(f"      Image sample (top-left 3x3): \n{image[:3, :3, :]}")
                        
                        # Show actual state values
                        state = step['observation']['state'].numpy()
                        print(f"      State (xyz[mm], rpy[rad], gripper): {state}")
                        
                        # Show action values
                        action = step['action'].numpy()
                        print(f"      Action (xyz_deltas, rpy_deltas, gripper): {action}")
                        
                        print(f"      Reward: {step['reward'].numpy()}")
                        print(f"      Is first: {step['is_first'].numpy()}, Is last: {step['is_last'].numpy()}")
        
        print(f"\n✓ Total episodes: {episode_count}")
        print(f"✓ Total steps: {total_steps}")
        print(f"✓ Average steps per episode: {total_steps/episode_count:.1f}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test RLDS datasets')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Show detailed step information (images, states, actions)')
    parser.add_argument('--dataset', '-d', choices=['all', 'combined', 'numbered', 'autorecorded'],
                       default='all', help='Which dataset to test (default: all)')
    args = parser.parse_args()
    
    # Set up datasets to test
    base_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'processed' / 'rlds'
    all_datasets = {
        'combined': (str(base_dir / "rlds_dataset"), "Combined dataset (all episodes)"),
        'numbered': (str(base_dir / "rlds_dataset_numbered"), "Numbered episodes only"),
        'autorecorded': (str(base_dir / "rlds_dataset_autorecorded"), "Auto-recorded episodes only")
    }
    
    # Select which datasets to test
    if args.dataset == 'all':
        datasets = list(all_datasets.values())
    else:
        datasets = [all_datasets[args.dataset]]
    
    results = []
    for dataset_dir, dataset_name in datasets:
        success = test_dataset(dataset_dir, dataset_name, verbose=args.verbose)
        results.append((dataset_name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {name}")

if __name__ == "__main__":
    main()