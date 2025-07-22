"""Test loading the created RLDS dataset."""

import tensorflow_datasets as tfds

# Load the dataset
ds = tfds.load('rdls_dataset_converter', split='train', data_dir='/Users/chris/rena/sync-server/rlds_dataset')

# Print dataset info
print("Dataset loaded successfully!")
print(f"Number of episodes: {len(ds)}")

# Inspect first episode
for i, episode in enumerate(ds.take(1)):
    print(f"\nEpisode {i}:")
    print(f"Episode metadata: {episode['episode_metadata']}")
    print(f"Number of steps: {len(episode['steps'])}")
    
    # Look at first few steps
    for j, step in enumerate(episode['steps'].take(5)):
        print(f"\n  Step {j}:")
        # Show actual image data (first few pixels)
        image = step['observation']['image'].numpy()
        print(f"    Image shape: {image.shape}")
        print(f"    Image sample (top-left 3x3): \n{image[:3, :3, :]}")
        
        # Show actual state values
        state = step['observation']['state'].numpy()
        print(f"    State (joints[rad], xyz[mm], rpy[rad], gripper): {state}")
        
        # Show action values
        action = step['action'].numpy()
        print(f"    Action (joint_deltas, xyz_deltas, rpy_deltas, gripper): {action}")
        
        print(f"    Language instruction: {step['language_instruction'].numpy().decode()}")
        print(f"    Reward: {step['reward'].numpy()}")
        print(f"    Is first: {step['is_first'].numpy()}, Is last: {step['is_last'].numpy()}")