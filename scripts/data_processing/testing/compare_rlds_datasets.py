#!/usr/bin/env python3
"""
Compare numbered and autorecorded RLDS datasets to identify differences 
that could cause finetuning issues.
"""

import sys
import numpy as np
from pathlib import Path
import tensorflow_datasets as tfds
from collections import defaultdict
import matplotlib.pyplot as plt

# Add parent directory to path to import convert_to_rlds
sys.path.append(str(Path(__file__).parent.parent))
from convert_to_rlds import RLDSDatasetConverter


def load_dataset(dataset_path, source_path):
    """Load an RLDS dataset."""
    builder = RLDSDatasetConverter(
        data_dir=str(dataset_path),
        source_dir=str(source_path)
    )
    return builder


def analyze_dataset_structure(builder, dataset_name):
    """Analyze basic dataset structure."""
    print(f"\n=== {dataset_name} Dataset Structure ===")
    
    info = builder.info
    print(f"Total episodes: {info.splits['train'].num_examples + info.splits['validation'].num_examples}")
    print(f"Train episodes: {info.splits['train'].num_examples}")
    print(f"Validation episodes: {info.splits['validation'].num_examples}")
    
    # Load train split for analysis
    ds = builder.as_dataset(split='train', shuffle_files=False)
    
    # Collect episode statistics
    episode_lengths = []
    total_steps = 0
    
    print(f"\nAnalyzing episodes...")
    for i, episode in enumerate(ds.take(10)):  # Sample first 10 episodes
        steps_list = list(episode['steps'])
        episode_length = len(steps_list)
        episode_lengths.append(episode_length)
        total_steps += episode_length
        
        if i < 3:  # Show details for first 3 episodes
            print(f"  Episode {i+1}: {episode_length} steps")
            print(f"    Episode ID: {episode['episode_metadata']['episode_id'].numpy().decode()}")
            print(f"    Task success: {episode['episode_metadata']['task_success'].numpy()}")
    
    # Load full dataset for complete statistics
    all_episode_lengths = []
    all_language_instructions = []
    all_states = []
    all_actions = []
    
    print(f"Loading full dataset for statistics...")
    for episode in ds:
        # Convert steps dataset to list
        steps_list = list(episode['steps'])
        episode_length = len(steps_list)
        all_episode_lengths.append(episode_length)
        
        # Extract language instruction from first step
        if steps_list:
            first_step = steps_list[0]
            lang_inst = first_step['language_instruction'].numpy().decode('utf-8')
            all_language_instructions.append(lang_inst)
            
            # Collect state and action data
            for step in steps_list:
                state = step['observation']['state'].numpy()
                action = step['action'].numpy() 
                all_states.append(state)
                all_actions.append(action)
    
    all_states = np.array(all_states)
    all_actions = np.array(all_actions)
    
    return {
        'episode_lengths': all_episode_lengths,
        'language_instructions': all_language_instructions,
        'states': all_states,
        'actions': all_actions,
        'total_episodes': len(all_episode_lengths),
        'total_steps': sum(all_episode_lengths)
    }


def analyze_language_instructions(stats, dataset_name):
    """Analyze language instruction content."""
    print(f"\n=== {dataset_name} Language Instructions ===")
    
    instructions = stats['language_instructions']
    unique_instructions = list(set(instructions))
    
    print(f"Total episodes: {len(instructions)}")
    print(f"Unique language instructions: {len(unique_instructions)}")
    
    # Show instruction distribution
    instruction_counts = defaultdict(int)
    for inst in instructions:
        instruction_counts[inst] += 1
    
    print(f"\nInstruction distribution:")
    for inst, count in sorted(instruction_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(instructions)) * 100
        print(f"  {count:3d} ({percentage:5.1f}%): {inst[:100]}...")
    
    return {
        'unique_count': len(unique_instructions),
        'instruction_distribution': dict(instruction_counts),
        'sample_instructions': unique_instructions[:5]
    }


def analyze_episode_lengths(stats, dataset_name):
    """Analyze episode length distribution."""
    print(f"\n=== {dataset_name} Episode Lengths ===")
    
    lengths = stats['episode_lengths']
    
    print(f"Episode count: {len(lengths)}")
    print(f"Total steps: {sum(lengths)}")
    print(f"Mean length: {np.mean(lengths):.1f}")
    print(f"Median length: {np.median(lengths):.1f}")
    print(f"Min length: {np.min(lengths)}")
    print(f"Max length: {np.max(lengths)}")
    print(f"Std deviation: {np.std(lengths):.1f}")
    
    # Show distribution
    print(f"\nLength distribution:")
    bins = [0, 10, 20, 30, 50, 75, 100, 150, 200, float('inf')]
    bin_labels = ['1-10', '11-20', '21-30', '31-50', '51-75', '76-100', '101-150', '151-200', '200+']
    
    for i in range(len(bins)-1):
        count = sum(1 for l in lengths if bins[i] < l <= bins[i+1])
        percentage = (count / len(lengths)) * 100
        print(f"  {bin_labels[i]:>8}: {count:3d} episodes ({percentage:5.1f}%)")
    
    return {
        'mean': np.mean(lengths),
        'median': np.median(lengths),
        'std': np.std(lengths),
        'min': np.min(lengths),
        'max': np.max(lengths)
    }


def analyze_states_actions(stats, dataset_name):
    """Analyze state and action data distributions."""
    print(f"\n=== {dataset_name} States and Actions ===")
    
    states = stats['states']
    actions = stats['actions']
    
    print(f"Total steps: {len(states)}")
    print(f"State shape: {states.shape}")
    print(f"Action shape: {actions.shape}")
    
    # Analyze state ranges (xyz, rpy, gripper)
    print(f"\nState analysis (xyz, rpy, gripper):")
    state_labels = ['x', 'y', 'z', 'roll', 'pitch', 'yaw', 'gripper']
    for i in range(states.shape[1]):
        values = states[:, i]
        print(f"  {state_labels[i]:>7}: min={np.min(values):8.2f}, max={np.max(values):8.2f}, "
              f"mean={np.mean(values):8.2f}, std={np.std(values):8.2f}")
    
    # Analyze action ranges
    print(f"\nAction analysis (xyz_delta, rpy_delta, gripper):")
    action_labels = ['dx', 'dy', 'dz', 'droll', 'dpitch', 'dyaw', 'gripper']
    for i in range(actions.shape[1]):
        values = actions[:, i]
        print(f"  {action_labels[i]:>7}: min={np.min(values):8.2f}, max={np.max(values):8.2f}, "
              f"mean={np.mean(values):8.2f}, std={np.std(values):8.2f}")
    
    # Check for any NaN or infinite values
    nan_states = np.isnan(states).any()
    inf_states = np.isinf(states).any()
    nan_actions = np.isnan(actions).any()
    inf_actions = np.isinf(actions).any()
    
    print(f"\nData quality:")
    print(f"  States - NaN: {nan_states}, Inf: {inf_states}")
    print(f"  Actions - NaN: {nan_actions}, Inf: {inf_actions}")
    
    return {
        'state_ranges': {state_labels[i]: {
            'min': np.min(states[:, i]),
            'max': np.max(states[:, i]),
            'mean': np.mean(states[:, i]),
            'std': np.std(states[:, i])
        } for i in range(states.shape[1])},
        'action_ranges': {action_labels[i]: {
            'min': np.min(actions[:, i]),
            'max': np.max(actions[:, i]),
            'mean': np.mean(actions[:, i]),
            'std': np.std(actions[:, i])
        } for i in range(actions.shape[1])},
        'has_nan_inf': {
            'states_nan': nan_states,
            'states_inf': inf_states,
            'actions_nan': nan_actions,
            'actions_inf': inf_actions
        }
    }


def compare_datasets():
    """Main comparison function."""
    print("=" * 80)
    print("RLDS Dataset Comparison: Numbered vs Autorecorded")
    print("=" * 80)
    
    # Dataset paths
    base_dir = Path(__file__).parent.parent.parent.parent
    numbered_rlds = base_dir / 'data' / 'processed' / 'rlds' / 'rlds_dataset_numbered'
    numbered_source = base_dir / 'data' / 'processed' / 'traces_matched_to_images_numbered'
    autorecorded_rlds = base_dir / 'data' / 'processed' / 'rlds' / 'rlds_dataset_autorecorded'
    autorecorded_source = base_dir / 'data' / 'processed' / 'traces_matched_to_images_autorecorded'
    
    # Load datasets
    print("Loading datasets...")
    numbered_builder = load_dataset(numbered_rlds, numbered_source)
    autorecorded_builder = load_dataset(autorecorded_rlds, autorecorded_source)
    
    # Analyze both datasets
    print("\n" + "="*60)
    print("ANALYZING NUMBERED DATASET")
    print("="*60)
    numbered_stats = analyze_dataset_structure(numbered_builder, "NUMBERED")
    numbered_lang_analysis = analyze_language_instructions(numbered_stats, "NUMBERED")
    numbered_length_analysis = analyze_episode_lengths(numbered_stats, "NUMBERED")
    numbered_data_analysis = analyze_states_actions(numbered_stats, "NUMBERED")
    
    print("\n" + "="*60)
    print("ANALYZING AUTORECORDED DATASET")  
    print("="*60)
    autorecorded_stats = analyze_dataset_structure(autorecorded_builder, "AUTORECORDED")
    autorecorded_lang_analysis = analyze_language_instructions(autorecorded_stats, "AUTORECORDED")
    autorecorded_length_analysis = analyze_episode_lengths(autorecorded_stats, "AUTORECORDED")
    autorecorded_data_analysis = analyze_states_actions(autorecorded_stats, "AUTORECORDED")
    
    # Generate comparison summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n📊 Dataset Size Comparison:")
    print(f"  Numbered:     {numbered_stats['total_episodes']:3d} episodes, {numbered_stats['total_steps']:5d} steps")
    print(f"  Autorecorded: {autorecorded_stats['total_episodes']:3d} episodes, {autorecorded_stats['total_steps']:5d} steps")
    
    print(f"\n📏 Episode Length Comparison:")
    print(f"  Numbered:     Mean={numbered_length_analysis['mean']:5.1f}, Median={numbered_length_analysis['median']:5.1f}, Std={numbered_length_analysis['std']:5.1f}")
    print(f"  Autorecorded: Mean={autorecorded_length_analysis['mean']:5.1f}, Median={autorecorded_length_analysis['median']:5.1f}, Std={autorecorded_length_analysis['std']:5.1f}")
    
    print(f"\n💬 Language Instruction Comparison:")
    print(f"  Numbered:     {numbered_lang_analysis['unique_count']} unique instructions")
    print(f"  Autorecorded: {autorecorded_lang_analysis['unique_count']} unique instructions")
    
    print(f"\n🔍 Key Differences Identified:")
    
    # Episode length difference
    length_ratio = numbered_length_analysis['mean'] / autorecorded_length_analysis['mean']
    print(f"  • Episode length: Numbered episodes are {length_ratio:.1f}x longer on average")
    
    # Language diversity
    lang_ratio = autorecorded_lang_analysis['unique_count'] / numbered_lang_analysis['unique_count']
    print(f"  • Language diversity: Autorecorded has {lang_ratio:.1f}x more unique instructions")
    
    # Data quality issues
    print(f"\n⚠️  Potential Issues for Finetuning:")
    
    if autorecorded_length_analysis['mean'] < 20:
        print(f"  • SHORT EPISODES: Autorecorded episodes are very short (avg {autorecorded_length_analysis['mean']:.1f} steps)")
        print(f"    This may not provide enough context for learning")
    
    if autorecorded_lang_analysis['unique_count'] > numbered_lang_analysis['unique_count'] * 2:
        print(f"  • HIGH LANGUAGE DIVERSITY: Autorecorded has much more diverse language")
        print(f"    This may make it harder to learn consistent patterns")
    
    if autorecorded_stats['total_steps'] < numbered_stats['total_steps'] / 2:
        print(f"  • LIMITED TRAINING DATA: Autorecorded has much fewer total steps")
        print(f"    This may not be sufficient for effective finetuning")
    
    # Check for data quality issues
    auto_quality = autorecorded_data_analysis['has_nan_inf']
    num_quality = numbered_data_analysis['has_nan_inf']
    
    if any(auto_quality.values()) and not any(num_quality.values()):
        print(f"  • DATA QUALITY: Autorecorded dataset has NaN/Inf values")
    
    print(f"\n🎯 Recommendations:")
    if autorecorded_length_analysis['mean'] < numbered_length_analysis['mean'] / 2:
        print(f"  • Consider filtering out very short episodes (< 10 steps)")
        print(f"  • Or combine multiple short episodes into longer sequences")
        
    if autorecorded_lang_analysis['unique_count'] > 10:
        print(f"  • Consider grouping similar language instructions")
        print(f"  • Or focus on most common instruction patterns")
        
    if autorecorded_stats['total_steps'] < 1000:
        print(f"  • Dataset may be too small for effective finetuning")
        print(f"  • Consider data augmentation or collecting more episodes")


if __name__ == "__main__":
    compare_datasets()