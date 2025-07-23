#!/usr/bin/env python3
"""Check language instructions in the numbered dataset."""

import tensorflow_datasets as tfds
from pathlib import Path

# Load the numbered dataset
print("Loading numbered dataset...")
base_dir = Path(__file__).parent.parent.parent
ds = tfds.load(
    'rlds_dataset_converter',
    data_dir=str(base_dir / 'data' / 'processed' / 'rlds' / 'rlds_dataset_numbered'),
    split='train'
)

print("\nChecking language instructions in numbered dataset:")
print("=" * 60)

# Check first 10 episodes
for i, episode in enumerate(ds.take(10)):
    # Get episode metadata
    task_name = episode['episode_metadata']['task_name'].numpy().decode()
    
    # Get language instruction from first step
    first_step = next(iter(episode['steps'].take(1)))
    lang = first_step['language_instruction'].numpy().decode()
    
    print(f'Episode {i:2d}: task_name="{task_name}", language_instruction="{lang}"')
    
    # Check if they match
    if task_name != lang:
        print(f'  ⚠️  WARNING: Mismatch! Expected "{task_name}" but got "{lang}"')

print("\n" + "=" * 60)
print("Checking more episodes (20-25)...")

# Skip to episode 20
for i, episode in enumerate(ds.skip(20).take(5)):
    task_name = episode['episode_metadata']['task_name'].numpy().decode()
    first_step = next(iter(episode['steps'].take(1)))
    lang = first_step['language_instruction'].numpy().decode()
    print(f'Episode {i+20}: task_name="{task_name}", language_instruction="{lang}"')

# Let's also check the original traces to understand the issue
print("\n" + "=" * 60)
print("Checking original trace files...")

import json

traces_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_numbered'
sample_files = sorted(traces_dir.glob("*.json"))[:5]

for trace_file in sample_files:
    if trace_file.name == "dataset_metadata.json":
        continue
        
    with open(trace_file) as f:
        data = json.load(f)
        
    metadata = data.get('metadata', {})
    task_name = metadata.get('task_name', trace_file.stem)
    description = metadata.get('description', task_name)
    
    print(f'\nFile: {trace_file.name}')
    print(f'  task_name: "{task_name}"')
    print(f'  description: "{description}"')
    print(f'  Expected language_instruction: "{description}"')