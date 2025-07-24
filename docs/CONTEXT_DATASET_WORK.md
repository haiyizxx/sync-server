# Dataset Work Context - July 23, 2025

## Current Status
- Successfully split the dataset into numbered and auto-recorded episodes
- All three datasets (combined, numbered, auto-recorded) are loading correctly in tests
- User reported autorecorded dataset "does not work" but tests show it loads fine
- Need to investigate specific issue with autorecorded dataset in actual usage

## Important Commands

### Conda Environment Activation
```bash
# Activate the conda environment (required before running any Python scripts)
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh && conda activate env
```

### Dataset Generation Pipeline

1. **Generate matched traces from raw data:**
```bash
python match_traces_images_folder.py
# Input: traces/ and images/ folders
# Output: traces_matched/ folder with image references added
```

2. **Split matched traces by type:**
```bash
python split_dataset_by_type.py
# Input: traces_matched/
# Output: traces_matched_numbered/ and traces_matched_autorecorded/
```

3. **Convert to RLDS format:**
```bash
# Combined dataset (all episodes)
python convert_to_rlds.py
# Output: rlds_dataset/

# Numbered episodes only
python convert_to_rlds.py numbered
# Output: rlds_dataset_numbered/

# Auto-recorded episodes only
python convert_to_rlds.py autorecorded
# Output: rlds_dataset_autorecorded/
```

### Testing Commands

```bash
# Test all three datasets
python test_split_datasets.py

# Test specific dataset loading
python test_dataset.py  # Tests the combined dataset
```

## Dataset Statistics

| Dataset | Episodes | Total Steps | Avg Steps/Episode | Size |
|---------|----------|-------------|-------------------|------|
| Combined | 90 | 4317 | 48.0 | ~307MB |
| Numbered | 42 | 3186 | 75.9 | ~234MB |
| Auto-recorded | 48 | 1131 | 23.6 | ~72MB |

## Key Differences
- **Numbered episodes**: Longer episodes (avg 75.9 steps), simple numeric language instructions
- **Auto-recorded episodes**: Shorter episodes (avg 23.6 steps), descriptive language instructions

## Git LFS Setup
Large TFRecord files are tracked with Git LFS:
```bash
git lfs track "*.tfrecord*"
git add .gitattributes
```

## OpenVLA Fine-tuning

### Setup
1. First activate the OpenVLA conda environment:
```bash
conda activate openvla-oft
```

2. Navigate to the OpenVLA directory:
```bash
cd /Users/chris/rena/openvla-oft/vla-scripts
```

3. Run fine-tuning with the numbered dataset:
```bash
# Set environment variables
export DATA_ROOT="/Users/chris/rena/sync-server/rlds_dataset_numbered"
export WANDB_ENTITY="your-wandb-entity"
export WANDB_PROJECT="mycobot-finetune"

# Run the script
bash /Users/chris/rena/sync-server/openvla_lora_finetune.sh
```

### Script Configuration
The `openvla_lora_finetune.sh` script supports environment variables:
- `VLA_PATH`: Path to base VLA model (default: openvla/openvla-7b)
- `DATA_ROOT`: Path to RLDS dataset (default: ./rlds_dataset_numbered)
- `DATASET_NAME`: Dataset name (default: rlds_dataset_converter)
- `BATCH_SIZE`: Training batch size (default: 4)
- `LEARNING_RATE`: Learning rate (default: 5e-4)
- `MAX_STEPS`: Maximum training steps (default: 10000)
- `LORA_RANK`: LoRA rank (default: 32)

## Next Steps
- Investigate specific issue with autorecorded dataset in actual training/usage
- User needs to provide more details about what "does not work" means
- Possible issues to check:
  - OpenVLA compatibility with shorter episodes
  - Language instruction processing differences
  - Image loading issues (all showed gray in test output)

## File Structure
```
sync-server/
├── data/
│   ├── raw/
│   │   ├── traces/                      # Original trace files
│   │   └── images/                      # Original image folders
│   └── processed/
│       ├── traces_matched_to_images_all/         # Combined matched traces
│       ├── traces_matched_to_images_numbered/    # Numbered episodes only
│       ├── traces_matched_to_images_autorecorded/# Auto-recorded episodes only
│       └── rlds/
│           ├── rlds_dataset/             # Combined RLDS dataset
│           ├── rlds_dataset_numbered/    # Numbered RLDS dataset
│           └── rlds_dataset_autorecorded/# Auto-recorded RLDS dataset
├── scripts/
│   ├── data_processing/
│   │   ├── convert_to_rlds.py           # RLDS conversion script
│   │   ├── match_and_split_traces.py    # Combined matching and splitting
│   │   └── testing/
│   │       ├── check_language_instructions.py
│   │       ├── plot_matching_stats.py
│   │       └── test_split_datasets.py
│   ├── recording/
│   │   ├── record_trace.py
│   │   ├── record_trace_auto.py
│   │   └── record_trace_keyboard.py
│   └── testing/                          # Hardware testing scripts
│       ├── debug_gripper.py
│       ├── debug_gripper_recording.py
│       ├── test.py
│       ├── test_gripper.py
│       └── testmovement.py
└── docs/
    └── CONTEXT_DATASET_WORK.md          # This documentation
```