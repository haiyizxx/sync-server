#!/usr/bin/env python3
"""
Generate probability distribution plots for offset and standard deviation from matching results.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import subprocess
import re

def extract_matching_stats():
    """Run the matching script and extract offset and std dev values."""
    # Run the matching script
    result = subprocess.run(['python3', 'match_traces_images_folder.py'], 
                          capture_output=True, text=True)
    
    # Parse the output
    offsets = []
    std_devs = []
    episodes = []
    
    lines = result.stdout.split('\n')
    current_episode = None
    
    for line in lines:
        if "Processing episode" in line:
            match = re.search(r'Processing episode (\S+)\.\.\.', line)
            if match:
                current_episode = match.group(1)
        elif "Mean offset:" in line and current_episode:
            match = re.search(r'Mean offset: ([-\d.]+)ms, Std dev: ([\d.]+)ms', line)
            if match:
                offset = float(match.group(1))
                std_dev = float(match.group(2))
                offsets.append(offset)
                std_devs.append(std_dev)
                episodes.append(current_episode)
    
    return episodes, offsets, std_devs

def plot_distributions(episodes, offsets, std_devs):
    """Create distribution plots for offset and standard deviation."""
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Separate regular episodes from date-formatted ones
    regular_offsets = []
    regular_stds = []
    date_offsets = []
    date_stds = []
    
    for ep, offset, std in zip(episodes, offsets, std_devs):
        if ep.startswith('2025'):
            date_offsets.append(offset)
            date_stds.append(std)
        else:
            regular_offsets.append(offset)
            regular_stds.append(std)
    
    # Plot 1: Offset Distribution
    ax1.hist(regular_offsets, bins=30, alpha=0.7, label='Regular episodes', color='blue', density=True)
    ax1.hist(date_offsets, bins=20, alpha=0.7, label='Date-formatted episodes', color='red', density=True)
    ax1.set_xlabel('Offset (ms)')
    ax1.set_ylabel('Probability Density')
    ax1.set_title('Distribution of Mean Offsets between Trace and Image Timestamps')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add statistics text
    ax1.text(0.02, 0.98, f'Regular: μ={np.mean(regular_offsets):.1f}ms, σ={np.std(regular_offsets):.1f}ms\n' +
                         f'Date-formatted: μ={np.mean(date_offsets):.1f}ms, σ={np.std(date_offsets):.1f}ms',
             transform=ax1.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Plot 2: Standard Deviation Distribution
    ax2.hist(regular_stds, bins=30, alpha=0.7, label='Regular episodes', color='blue', density=True)
    ax2.hist(date_stds, bins=20, alpha=0.7, label='Date-formatted episodes', color='red', density=True)
    ax2.set_xlabel('Standard Deviation (ms)')
    ax2.set_ylabel('Probability Density')
    ax2.set_title('Distribution of Timing Standard Deviations (after offset removal)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add statistics text
    ax2.text(0.02, 0.98, f'Regular: μ={np.mean(regular_stds):.1f}ms, σ={np.std(regular_stds):.1f}ms\n' +
                         f'Date-formatted: μ={np.mean(date_stds):.1f}ms, σ={np.std(date_stds):.1f}ms',
             transform=ax2.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('matching_stats_distribution.png', dpi=150, bbox_inches='tight')
    plt.savefig('matching_stats_distribution.pdf', bbox_inches='tight')
    print("Plots saved as matching_stats_distribution.png and matching_stats_distribution.pdf")
    
    # Create box plots for better visualization of outliers
    fig2, (ax3, ax4) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Box plot for offsets
    ax3.boxplot([regular_offsets, date_offsets], labels=['Regular', 'Date-formatted'])
    ax3.set_ylabel('Offset (ms)')
    ax3.set_title('Box Plot of Mean Offsets')
    ax3.grid(True, alpha=0.3)
    
    # Box plot for standard deviations
    ax4.boxplot([regular_stds, date_stds], labels=['Regular', 'Date-formatted'])
    ax4.set_ylabel('Standard Deviation (ms)')
    ax4.set_title('Box Plot of Standard Deviations')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('matching_stats_boxplot.png', dpi=150, bbox_inches='tight')
    plt.savefig('matching_stats_boxplot.pdf', bbox_inches='tight')
    print("Box plots saved as matching_stats_boxplot.png and matching_stats_boxplot.pdf")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Regular episodes (n={len(regular_offsets)}):")
    print(f"  Offset: mean={np.mean(regular_offsets):.1f}ms, std={np.std(regular_offsets):.1f}ms, " +
          f"min={np.min(regular_offsets):.1f}ms, max={np.max(regular_offsets):.1f}ms")
    print(f"  Std Dev: mean={np.mean(regular_stds):.1f}ms, std={np.std(regular_stds):.1f}ms, " +
          f"min={np.min(regular_stds):.1f}ms, max={np.max(regular_stds):.1f}ms")
    
    print(f"\nDate-formatted episodes (n={len(date_offsets)}):")
    print(f"  Offset: mean={np.mean(date_offsets):.1f}ms, std={np.std(date_offsets):.1f}ms, " +
          f"min={np.min(date_offsets):.1f}ms, max={np.max(date_offsets):.1f}ms")
    print(f"  Std Dev: mean={np.mean(date_stds):.1f}ms, std={np.std(date_stds):.1f}ms, " +
          f"min={np.min(date_stds):.1f}ms, max={np.max(date_stds):.1f}ms")

if __name__ == "__main__":
    print("Extracting matching statistics...")
    episodes, offsets, std_devs = extract_matching_stats()
    
    if offsets:
        print(f"Found {len(offsets)} episodes with matching statistics")
        plot_distributions(episodes, offsets, std_devs)
    else:
        print("No matching statistics found!")