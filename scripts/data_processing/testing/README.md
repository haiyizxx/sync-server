# Dataset Testing Scripts

This folder contains testing scripts for the RLDS dataset processing pipeline.

## Test Scripts

### test_split_datasets.py
Comprehensive test for RLDS datasets with flexible options.

```bash
# Run in conda environment
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh && conda activate env

# Test all datasets (default)
python test_split_datasets.py

# Test with verbose output (shows image pixels, states, actions)
python test_split_datasets.py --verbose

# Test specific dataset only
python test_split_datasets.py --dataset combined
python test_split_datasets.py --dataset numbered
python test_split_datasets.py --dataset autorecorded

# Combine options
python test_split_datasets.py --dataset numbered --verbose
```

Options:
- `--verbose`, `-v`: Show detailed step information including image pixels, state values, and actions
- `--dataset`, `-d`: Choose which dataset to test (all, combined, numbered, autorecorded)

### check_language_instructions.py
Checks language instructions in the matched trace files before RLDS conversion.
```bash
python check_language_instructions.py
```

## Requirements
- TensorFlow and TensorFlow Datasets installed
- Conda environment activated (for RLDS tests)
- Datasets must be generated first using the processing pipeline

## Dataset Locations
- Combined: `/data/processed/rlds/rlds_dataset/`
- Numbered: `/data/processed/rlds/rlds_dataset_numbered/`
- Autorecorded: `/data/processed/rlds/rlds_dataset_autorecorded/`