#!/usr/bin/env python3
"""
Unified RLDS conversion script that can convert all episodes or specific types.

Usage:
    python convert_to_rlds_unified.py              # Convert all episodes
    python convert_to_rlds_unified.py numbered     # Convert only numbered episodes
    python convert_to_rlds_unified.py autorecorded # Convert only autorecorded episodes
"""

import tensorflow_datasets as tfds
import json
import numpy as np
from pathlib import Path
from typing import Iterator, List, Optional
from PIL import Image
import sys


class RLDSDatasetConverter(tfds.core.GeneratorBasedBuilder):
    """DatasetBuilder for MyCobot robot demonstrations."""
    
    VERSION = tfds.core.Version('1.0.0')
    RELEASE_NOTES = {
        '1.0.0': 'Initial release with real camera images from robot demonstrations.',
    }

    def __init__(self, data_dir, source_dir, **kwargs):
        """Initialize with custom source directory."""
        self.source_dir = Path(source_dir)
        super().__init__(data_dir=data_dir, **kwargs)

    def _info(self) -> tfds.core.DatasetInfo:
        """Returns the dataset metadata."""
        return tfds.core.DatasetInfo(
            builder=self,
            description="MyCobot 280 robot demonstrations with joint/Cartesian states and camera images",
            features=tfds.features.FeaturesDict({
                'steps': tfds.features.Dataset({
                    'observation': tfds.features.FeaturesDict({
                        'image': tfds.features.Image(shape=(256, 256, 3), dtype=np.uint8, encoding_format='jpeg'),
                        'state': tfds.features.Tensor(shape=(7,), dtype=np.float32),  # xyz(3) + rpy(3) + gripper(1)
                    }),
                    'action': tfds.features.Tensor(shape=(7,), dtype=np.float32),  # cartesian_deltas(6) + gripper(1)
                    'discount': tfds.features.Scalar(dtype=np.float32),
                    'reward': tfds.features.Scalar(dtype=np.float32),
                    'is_first': tfds.features.Scalar(dtype=np.bool_),
                    'is_last': tfds.features.Scalar(dtype=np.bool_),
                    'is_terminal': tfds.features.Scalar(dtype=np.bool_),
                    'language_instruction': tfds.features.Text(),
                }),
                'episode_metadata': tfds.features.FeaturesDict({
                    'file_path': tfds.features.Text(),
                    'episode_id': tfds.features.Text(),
                    'episode_length': tfds.features.Scalar(dtype=np.int32),
                    'task_success': tfds.features.Scalar(dtype=np.bool_),
                    'task_name': tfds.features.Text(),
                }),
            }),
            supervised_keys=None,
            homepage='https://github.com/mycobot/demonstrations',
        )

    def _split_generators(self, dl_manager):
        """Returns SplitGenerators."""
        json_files = sorted(self.source_dir.glob('*.json'))
        
        # Filter out metadata files
        json_files = [f for f in json_files if f.name != 'dataset_metadata.json']
        
        if not json_files:
            raise ValueError(f"No JSON files found in {self.source_dir}")
        
        print(f"Found {len(json_files)} episodes to convert from {self.source_dir}")
        
        # Split into train (95%) and validation (5%)
        total_episodes = len(json_files)
        val_size = max(1, int(0.05 * total_episodes))  # At least 1 episode for validation
        train_size = total_episodes - val_size
        
        train_files = json_files[:train_size]
        val_files = json_files[train_size:]
        
        print(f"Train episodes: {len(train_files)} ({len(train_files)/total_episodes*100:.1f}%)")
        print(f"Validation episodes: {len(val_files)} ({len(val_files)/total_episodes*100:.1f}%)")
        
        return {
            tfds.Split.TRAIN: self._generate_examples(train_files),
            tfds.Split.VALIDATION: self._generate_examples(val_files),
        }

    def _normalize_gripper_value(self, gripper_value: float) -> float:
        """Normalize gripper value from [0, 100] to [0, 1]."""
        return np.clip(gripper_value / 100.0, 0.0, 1.0)

    def _generate_examples(self, json_files) -> Iterator[tuple]:
        """Yields examples from matched trace JSON files."""
        total_steps = 0
        matched_images = 0
        
        for episode_idx, json_file in enumerate(json_files):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Extract metadata
                metadata = data.get('metadata', {})
                
                # Skip if no trace data
                trace = data.get('trace', [])
                if not trace:
                    print(f"Warning: No trace data in {json_file}")
                    continue
                
                # Use the description from trace metadata as language instruction
                language_instruction = metadata.get('description', 'no description found')
                
                # Prepare episode steps
                steps = []
                
                for step_idx, step in enumerate(trace):
                    # Extract coordinates (xyz, rpy)
                    coords = step.get('coords', [])
                    if not isinstance(coords, list) or len(coords) != 6:
                        continue
                    
                    xyz_pos = np.array(coords[:3], dtype=np.float32)
                    rpy_orient = np.array(coords[3:], dtype=np.float32) * np.pi / 180.0
                    
                    # Combined state: [xyz_pos(3), rpy_orient(3), gripper(1)]
                    # Normalize gripper from [0, 100] to [0, 1]
                    gripper_state = np.array([self._normalize_gripper_value(float(step['gripper_value']))], dtype=np.float32)
                    state = np.concatenate([xyz_pos, rpy_orient, gripper_state])
                    
                    # Calculate actions (cartesian deltas only)
                    cartesian_deltas = np.zeros(6, dtype=np.float32)
                    
                    if step_idx < len(trace) - 1:
                        next_step = trace[step_idx + 1]
                        next_coords = next_step.get('coords', [])
                        
                        # Cartesian deltas  
                        if isinstance(next_coords, list) and len(next_coords) == 6:
                            next_xyz = np.array(next_coords[:3], dtype=np.float32)
                            next_rpy = np.array(next_coords[3:], dtype=np.float32) * np.pi / 180.0
                            xyz_deltas = next_xyz - xyz_pos
                            rpy_deltas = next_rpy - rpy_orient
                            cartesian_deltas = np.concatenate([xyz_deltas, rpy_deltas])
                    
                    # Add gripper action (normalized to 0-1)
                    gripper_action = np.array([self._normalize_gripper_value(float(step['gripper_value']))], dtype=np.float32)
                    
                    # Combined action: [cartesian_deltas(6), gripper(1)]
                    action = np.concatenate([cartesian_deltas, gripper_action])
                    
                    # Load actual image if available
                    image_array = self._load_image_for_step(json_file, step)
                    total_steps += 1
                    if image_array is None:
                        # Create a placeholder when no matching image is found
                        image_array = self._create_placeholder_image()
                    else:
                        matched_images += 1
                    
                    # Create step data
                    step_data = {
                        'observation': {
                            'image': image_array,
                            'state': state,
                        },
                        'action': action,
                        'discount': 1.0,
                        'reward': 0.0,
                        'is_first': step_idx == 0,
                        'is_last': step_idx == len(trace) - 1,
                        'is_terminal': False,
                        'language_instruction': language_instruction,
                    }
                    
                    steps.append(step_data)
                
                if steps:
                    # Create episode metadata
                    episode_metadata = {
                        'file_path': str(json_file),
                        'episode_id': json_file.stem,
                        'episode_length': len(steps),
                        'task_success': metadata.get('task_success', True),
                        'task_name': metadata.get('task_name', 'unknown'),
                    }
                    
                    # Yield the complete episode
                    yield json_file.stem, {
                        'steps': steps,
                        'episode_metadata': episode_metadata,
                    }
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        print(f"\nConversion complete!")
        print(f"Total steps processed: {total_steps}")
        print(f"Steps with matched images: {matched_images}")
        print(f"Image match rate: {matched_images/total_steps*100:.1f}%")
    
    def _load_image_for_step(self, json_file: Path, step: dict) -> Optional[np.ndarray]:
        """Load the actual camera image for a step."""
        image_filename = step.get('image')
        if not image_filename:
            return None
        
        # Build image path
        episode_name = json_file.stem
        base_dir = Path(__file__).parent.parent.parent
        img_path = base_dir / 'data' / 'raw' / 'images' / episode_name / image_filename
        
        if not img_path.exists():
            return None
        
        # Load and resize image
        try:
            img = Image.open(img_path)
            
            # Resize to 256x256
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            img_array = np.array(img)
            
            # Ensure it's RGB (not RGBA)
            if img_array.shape[-1] == 4:
                img_array = img_array[:, :, :3]
            
            return img_array.astype(np.uint8)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            return None
    
    def _create_placeholder_image(self) -> np.ndarray:
        """Creates a gray placeholder image when no matching camera image is found."""
        # Simple gray image to indicate missing data
        gray_value = 128
        return np.full((256, 256, 3), gray_value, dtype=np.uint8)


def main():
    """Main conversion function."""
    # Parse command line arguments
    dataset_type = 'all'
    if len(sys.argv) > 1:
        if sys.argv[1] not in ['numbered', 'autorecorded', 'simple']:
            print("Usage: python convert_to_rlds.py [numbered|autorecorded|simple]")
            print("  No argument: converts all episodes")
            print("  numbered: converts only numbered episodes")
            print("  autorecorded: converts only autorecorded episodes")
            print("  simple: converts only simple trace episodes")
            sys.exit(1)
        dataset_type = sys.argv[1]
    
    # Set up paths
    base_dir = Path(__file__).parent.parent.parent
    
    if dataset_type == 'all':
        source_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_all'
        output_dir = base_dir / 'data' / 'processed' / 'rlds' / 'rlds_dataset'
    elif dataset_type == 'simple':
        source_dir = base_dir / 'data' / 'processed' / 'traces_matched_to_images_simple'
        output_dir = base_dir / 'data' / 'processed' / 'rlds' / 'rlds_dataset_simple'
    else:
        source_dir = base_dir / 'data' / 'processed' / f'traces_matched_to_images_{dataset_type}'
        output_dir = base_dir / 'data' / 'processed' / 'rlds' / f'rlds_dataset_{dataset_type}'
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)
    
    print(f"Converting {dataset_type} episodes...")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")
    
    # Create the dataset
    builder = RLDSDatasetConverter(
        data_dir=str(output_dir),
        source_dir=str(source_dir)
    )
    
    # Build the dataset
    builder.download_and_prepare()
    
    print(f"\nDataset created successfully at: {output_dir}")
    
    # Print dataset info
    ds_info = builder.info
    print(f"\nDataset info:")
    print(f"  Train episodes: {ds_info.splits['train'].num_examples}")
    print(f"  Validation episodes: {ds_info.splits['validation'].num_examples}")
    print(f"  Total episodes: {ds_info.splits['train'].num_examples + ds_info.splits['validation'].num_examples}")
    print(f"  Features: {list(ds_info.features.keys())}")


if __name__ == '__main__':
    main()