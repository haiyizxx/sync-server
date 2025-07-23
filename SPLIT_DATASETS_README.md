# Split Datasets

This directory contains tools and data for splitting the robot demonstration dataset into two categories:

## Dataset Types

### 1. Numbered Episodes (`rlds_dataset_numbered/`)
- **Count**: 42 episodes  
- **Naming**: Simple numeric identifiers (11, 12, 13, etc.)
- **Language Instructions**: Minimal - just the episode number
- **Size**: ~234MB across 2 TFRecord shards
- **Use Case**: When you want minimal language conditioning

### 2. Auto-recorded Episodes (`rlds_dataset_autorecorded/`)
- **Count**: 48 episodes
- **Naming**: Timestamp-based (20250722155656, etc.)
- **Language Instructions**: Descriptive - "Automatically recorded task [timestamp]"
- **Size**: ~72MB in 1 TFRecord shard
- **Use Case**: When you want more descriptive language instructions

## Usage

### Converting Split Datasets

Use the simple conversion script:
```bash
python convert_split_simple.py numbered      # Creates rlds_dataset_numbered/
python convert_split_simple.py autorecorded  # Creates rlds_dataset_autorecorded/
```

### Loading in TensorFlow
```python
import tensorflow_datasets as tfds

# Load numbered episodes
ds_numbered = tfds.load(
    'rdls_dataset_converter',
    data_dir='./rlds_dataset_numbered',
    split='train'
)

# Load auto-recorded episodes
ds_auto = tfds.load(
    'rdls_dataset_converter', 
    data_dir='./rlds_dataset_autorecorded',
    split='train'
)
```

## Notes

- Both datasets skip steps with empty coordinates to avoid processing errors
- Episodes with no valid steps (all empty coords) are excluded
- The datasets use the same structure as the original combined dataset
- Images are matched using the improved distribution algorithm with time offset handling