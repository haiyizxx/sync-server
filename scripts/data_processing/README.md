# Data Processing Scripts

This folder contains scripts for processing robot demonstration data into RLDS (Reinforcement Learning Datasets) format.

## Prerequisites

Before running any scripts, activate the conda environment:
```bash
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh && conda activate env
```

## Pipeline Overview

The data processing pipeline consists of two main steps:
1. **Match images to traces and split by type**
2. **Convert to RLDS format**

## Scripts

### 1. match_and_split_traces.py

Processes raw traces and images, matches them together, and splits into different dataset types.

**Input:**
- `data/raw/traces/` - Robot trace JSON files
- `data/raw/images/` - Image directories organized by episode

**Output:**
- `data/processed/traces_matched_to_images_all/` - All matched episodes
- `data/processed/traces_matched_to_images_numbered/` - Numbered episodes only (1, 2, 3...)
- `data/processed/traces_matched_to_images_autorecorded/` - Date-formatted episodes (20250722...)

**Usage:**
```bash
python match_and_split_traces.py
```

**What it does:**
- Loads all trace files from raw data
- Matches each trace with corresponding images based on timestamps
- Uses distribution algorithm to assign images evenly across trace steps
- Automatically classifies episodes as numbered vs auto-recorded
- Creates metadata files with statistics
- Saves to both combined and split directories

### 2. convert_to_rlds.py

Converts matched trace data to TensorFlow RLDS format for use with robot learning frameworks.

**Input:**
- Matched trace directories (from step 1)

**Output:**
- `data/processed/rlds/rlds_dataset/` - Combined RLDS dataset
- `data/processed/rlds/rlds_dataset_numbered/` - Numbered episodes RLDS
- `data/processed/rlds/rlds_dataset_autorecorded/` - Auto-recorded episodes RLDS

**Usage:**
```bash
# Convert all episodes (default)
python convert_to_rlds.py

# Convert specific dataset types
python convert_to_rlds.py numbered
python convert_to_rlds.py autorecorded
```

**Features:**
- Normalizes gripper values from [0, 100] to [0, 1] range
- Creates 7-dimensional state vectors: [xyz(3) + rpy(3) + gripper(1)]
- Calculates 7-dimensional action vectors: [cartesian_deltas(6) + gripper(1)]
- Stores language instructions in episode metadata
- Resizes images to 256x256 RGB format
- Creates placeholder images when originals are missing

## Complete Pipeline Example

```bash
# 1. Match images to traces and split datasets
python match_and_split_traces.py

# 2. Convert all to RLDS format
python convert_to_rlds.py           # All episodes
python convert_to_rlds.py numbered  # Numbered only
python convert_to_rlds.py autorecorded  # Auto-recorded only
```

## Testing

Use the testing scripts to verify your datasets:

```bash
# Test all RLDS datasets
python testing/test_split_datasets.py

# Test with detailed output
python testing/test_split_datasets.py --verbose

# Test specific dataset
python testing/test_split_datasets.py --dataset numbered
```

See `testing/README.md` for more testing options.

## Dataset Statistics

| Dataset Type | Episodes | Avg Steps/Episode | Description |
|-------------|----------|-------------------|-------------|
| Numbered | ~52 | ~76 | Longer episodes with simple numeric IDs |
| Auto-recorded | ~48 | ~24 | Shorter episodes from rapid recording sessions |
| Combined | ~100 | ~48 | All episodes together |

## File Formats

### Input Trace Format
```json
{
  "metadata": {
    "task_name": "1",
    "task_success": true,
    "duration_seconds": 15.5
  },
  "trace": [
    {
      "timestamp_ms": 1753206362703,
      "coords": [88.0, -51.7, 403.6, 2.09, 35.45, -107.01],
      "gripper_value": 0,
      "image": "28_1753206363929.jpg"
    }
  ]
}
```

### RLDS Output Format
- **Episode metadata**: task_name, language_instruction, duration, etc.
- **Steps**: observation (image + state), action, reward, discount, episode flags
- **Images**: 256x256x3 RGB format
- **States**: [x, y, z, roll, pitch, yaw, gripper] (7D)
- **Actions**: [dx, dy, dz, droll, dpitch, dyaw, dgripper] (7D)

## Troubleshooting

### Common Issues

1. **No trace files found**
   - Check that `data/raw/traces/` contains .json files
   - Verify file permissions

2. **No images found for episode**
   - Check that `data/raw/images/{episode_name}/` exists
   - Verify image metadata .json files are present

3. **TensorFlow import errors**
   - Ensure conda environment is activated
   - Install missing dependencies: `pip install tensorflow tensorflow-datasets`

4. **Low image match rates**
   - Check timestamp synchronization between traces and images
   - Review matching algorithm parameters in script

### Performance Notes

- Processing 100 episodes takes ~5-10 minutes
- RLDS conversion creates large files (300MB+ total)
- Use `--verbose` flag sparingly as it slows down testing

## Integration with OpenVLA

The generated RLDS datasets are compatible with OpenVLA fine-tuning:

```bash
# Example OpenVLA fine-tuning command
export DATA_ROOT="/path/to/rlds_dataset_numbered"
bash openvla_lora_finetune.sh
```

See the main documentation for detailed OpenVLA integration instructions.