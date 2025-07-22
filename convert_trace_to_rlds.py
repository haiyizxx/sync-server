"""
MyCobot Dataset Builder for RLDS format

Converts MyCobot robot demonstration traces to RLDS (Robotics Learning Data Set) format.
Loads traces from tuning_data/run-traces-images/ and matches them with corresponding camera images.
Produces TensorFlow Datasets compatible with robot learning frameworks.

Expected file structure:
  tuning_data/run-traces-images/
    1/
      trace-1.json
      images-1/
        <command_id>_<timestamp>.jpg
    2/
      trace-2.json  
      images-2/
        <command_id>_<timestamp>.jpg
    ...
"""

import tensorflow_datasets as tfds
import json
import numpy as np
from pathlib import Path
from typing import Iterator, Optional
from PIL import Image


class RDLSDatasetConverter(tfds.core.GeneratorBasedBuilder):
    """DatasetBuilder for MyCobot robot demonstrations."""
    
    VERSION = tfds.core.Version('1.0.0')
    RELEASE_NOTES = {
        '1.0.0': 'Initial release with real camera images from robot demonstrations.',
    }

    def _info(self) -> tfds.core.DatasetInfo:
        """Returns the dataset metadata."""
        return tfds.core.DatasetInfo(
            builder=self,
            description="MyCobot 280 robot demonstrations with joint/Cartesian states and camera images",
            features=tfds.features.FeaturesDict({
                'steps': tfds.features.Dataset({
                    'observation': tfds.features.FeaturesDict({
                        'image': tfds.features.Image(
                            shape=(256, 256, 3),
                            dtype=np.uint8,
                            encoding_format='png'
                        ),
                        'state': tfds.features.Tensor(
                            shape=(13,),  # 6 joint angles + 6 cartesian coords (xyz + rpy) + gripper
                            dtype=np.float32
                        ),
                    }),
                    'action': tfds.features.Tensor(
                        shape=(13,),  # 6 joint deltas + 6 cartesian deltas + gripper
                        dtype=np.float32
                    ),
                    'language_instruction': tfds.features.Text(),
                    'reward': tfds.features.Scalar(dtype=np.float32),
                    'is_first': tfds.features.Scalar(dtype=np.bool_),
                    'is_last': tfds.features.Scalar(dtype=np.bool_),
                    'is_terminal': tfds.features.Scalar(dtype=np.bool_),
                    'discount': tfds.features.Scalar(dtype=np.float32),
                }),
                'episode_metadata': tfds.features.FeaturesDict({
                    'file_path': tfds.features.Text(),
                    'episode_id': tfds.features.Text(),
                    'task_name': tfds.features.Text(),
                    'duration_seconds': tfds.features.Scalar(dtype=np.float32),
                    'total_points': tfds.features.Scalar(dtype=np.int32),
                    'task_success': tfds.features.Scalar(dtype=np.bool_),
                })
            }),
            homepage='https://github.com/your-username/mycobot-dataset',
            citation=r"""@misc{mycobot_dataset,
                title={MyCobot Robot Demonstrations},
                author={Your Name},
                year={2025}
            }""",
        )

    def _split_generators(self, dl_manager: tfds.download.DownloadManager):
        """Returns SplitGenerators."""
        # Point to the data directory
        data_dir = Path(__file__).parent / 'tuning_data' / 'run-traces-images'
        json_files = list(data_dir.glob('*/trace-*.json'))
        
        if not json_files:
            raise ValueError(f"No JSON files found in {data_dir}")
        
        return {
            'train': self._generate_examples(json_files),
        }

    def _generate_examples(self, json_files) -> Iterator[tuple]:
        """Yields examples."""
        total_steps = 0
        matched_images = 0
        
        for episode_idx, json_file in enumerate(json_files):
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            metadata = data['metadata']
            trace = data['trace']
            
            if len(trace) == 0:
                continue
            
            steps = []
            valid_step_idx = 0
            
            for step_idx, step in enumerate(trace):
                # Skip entries with missing data
                angles = step['angles']
                coords = step.get('coords', [])
                if not isinstance(angles, list) or len(angles) != 6:
                    print(f"Skipping malformed step {step_idx}: angles = {angles}")
                    continue
                if not isinstance(coords, list) or len(coords) != 6:
                    print(f"Skipping step {step_idx}: missing or invalid coords = {coords}")
                    continue
                
                # Convert joint angles from degrees to radians
                joints = np.array(angles, dtype=np.float32) * np.pi / 180.0
                
                # Process Cartesian coordinates (XYZ in mm, RPY in degrees)
                xyz_pos = np.array(coords[:3], dtype=np.float32)  # mm
                rpy_orient = np.array(coords[3:], dtype=np.float32) * np.pi / 180.0  # convert to radians
                
                # Combined state: [joint_angles(6), xyz_pos(3), rpy_orient(3), gripper(1)]
                gripper_state = np.array([float(step['gripper_value'])], dtype=np.float32)
                state = np.concatenate([joints, xyz_pos, rpy_orient, gripper_state])
                
                # Calculate actions (deltas for both joint and cartesian)
                joint_deltas = np.zeros(6, dtype=np.float32)
                cartesian_deltas = np.zeros(6, dtype=np.float32)
                
                if step_idx < len(trace) - 1:
                    next_step = trace[step_idx + 1]
                    next_angles = next_step.get('angles', [])
                    next_coords = next_step.get('coords', [])
                    
                    # Joint deltas
                    if isinstance(next_angles, list) and len(next_angles) == 6:
                        next_joints = np.array(next_angles, dtype=np.float32) * np.pi / 180.0
                        joint_deltas = next_joints - joints
                    
                    # Cartesian deltas  
                    if isinstance(next_coords, list) and len(next_coords) == 6:
                        next_xyz = np.array(next_coords[:3], dtype=np.float32)
                        next_rpy = np.array(next_coords[3:], dtype=np.float32) * np.pi / 180.0
                        xyz_deltas = next_xyz - xyz_pos
                        rpy_deltas = next_rpy - rpy_orient
                        cartesian_deltas = np.concatenate([xyz_deltas, rpy_deltas])
                
                # Add gripper action 
                gripper_action = np.array([float(step['gripper_value'])], dtype=np.float32)
                
                # Combined action: [joint_deltas(6), cartesian_deltas(6), gripper(1)]
                action = np.concatenate([joint_deltas, cartesian_deltas, gripper_action])
                
                # Load actual image if available
                image_array = self._load_image_for_step(json_file, step, valid_step_idx)
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
                        'state': state,  # Now includes joints + cartesian coords + gripper
                    },
                    'action': action,
                    'language_instruction': metadata.get('description', 'Robot manipulation task'),
                    'reward': 1.0 if step_idx == len(trace) - 1 and metadata.get('task_success', False) else 0.0,
                    'is_first': valid_step_idx == 0,
                    'is_last': step_idx == len(trace) - 1,
                    'is_terminal': step_idx == len(trace) - 1,
                    'discount': 1.0,
                }
                
                steps.append(step_data)
                valid_step_idx += 1
            
            # Create episode metadata
            episode_metadata = {
                'file_path': str(json_file),
                'episode_id': f"episode_{episode_idx}",
                'task_name': metadata.get('task_name', 'unknown'),
                'duration_seconds': metadata.get('duration_seconds', 0.0),
                'total_points': metadata.get('total_points', len(trace)),
                'task_success': metadata.get('task_success', False),
            }
            
            # Print episode summary
            episode_num = json_file.stem.split('-')[-1]
            episode_matched = sum(1 for s in steps if not np.all(s['observation']['image'] == 128))
            print(f"Episode {episode_num}: {episode_matched}/{len(steps)} images matched")
            
            yield episode_idx, {
                'steps': steps,
                'episode_metadata': episode_metadata,
            }
        
        # Print overall summary
        print(f"\nOverall: {matched_images}/{total_steps} images matched ({matched_images/total_steps*100:.1f}%)")

    def _load_image_for_step(self, json_file: Path, step: dict, step_idx: int) -> Optional[np.ndarray]:
        """Load the image for this step by matching order in the images folder."""
        # Get the episode number from the trace filename (e.g., trace-1.json -> 1)
        episode_num = json_file.stem.split('-')[-1]
        
        # Look for images in the corresponding images folder
        images_dir = json_file.parent / f'images-{episode_num}'
        if not images_dir.exists():
            print(f"Images directory not found: {images_dir}")
            return None
        
        # Get all jpg files sorted by name (which should be in chronological order)
        image_files = sorted(images_dir.glob('*.jpg'))
        
        # Check if we have an image for this step index
        if step_idx < len(image_files):
            img_path = image_files[step_idx]
            try:
                # Load and resize image to 256x256
                img = Image.open(img_path)
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
                img_array = np.array(img)
                
                # Ensure it's RGB (not RGBA)
                if img_array.shape[-1] == 4:
                    img_array = img_array[:, :, :3]
                
                return img_array.astype(np.uint8)
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                return None
        else:
            # No image for this step index
            return None
    
    def _create_placeholder_image(self) -> np.ndarray:
        """Creates a gray placeholder image when no matching camera image is found."""
        # Simple gray image to indicate missing data
        gray_value = 128
        return np.full((256, 256, 3), gray_value, dtype=np.uint8)


if __name__ == '__main__':
    print("Starting dataset creation...")
    # This will create the dataset
    data_dir = Path(__file__).parent / 'rlds_dataset'
    builder = RDLSDatasetConverter(data_dir=str(data_dir))
    print(f"Data directory will be: {builder.data_dir}")
    builder.download_and_prepare()
    print(f"Dataset created at: {builder.data_dir}")