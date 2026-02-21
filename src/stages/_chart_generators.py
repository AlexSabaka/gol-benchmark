"""
Chart generation functions for analyze_results.py
This file contains all specialized chart generators for the intelligent visualization system.
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

# Import color constants from parent module
from . import analyze_results


def _build_data_matrix(results: List[Dict], stats: List[Dict], row_dim: str, col_dim: str, dimensions: Dict) -> tuple:
    """
    Build a data matrix for heatmap generation.
    
    Args:
        results: List of result dicts
        stats: List of extracted stats
        row_dim: Dimension for rows ('models', 'tasks', 'user_prompts', etc.)
        col_dim: Dimension for columns
        dimensions: Detected dimensions dict
        
    Returns:
        (matrix, row_labels, col_labels)
    """
    rows = sorted(dimensions[row_dim + 's']) if row_dim + 's' in dimensions else sorted(dimensions[row_dim])
    cols = sorted(dimensions[col_dim + 's']) if col_dim + 's' in dimensions else sorted(dimensions[col_dim])
    
    # Create matrix
    matrix = np.zeros((len(rows), len(cols)))
    counts = np.zeros((len(rows), len(cols)))  # Track number of data points per cell
    
    for stat in stats:
        row_key = stat.get(f'{row_dim}_name') or stat.get(row_dim)
        col_key = stat.get(f'{col_dim}_style') or stat.get(col_dim)
        
        if row_key in rows and col_key in cols:
            row_idx = rows.index(row_key)
            col_idx = cols.index(col_key)
            matrix[row_idx, col_idx] += stat.get('accuracy', 0) * 100
            counts[row_idx, col_idx] += 1
    
    # Average cells with multiple data points
    matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)
    
    return matrix, rows, cols


# =============================================================================
# PROMPT COMPARISON CHARTS
# =============================================================================

def generate_prompt_heatmap(results, stats, dimensions, output_path, chart_num):
    """1. Prompt Performance Heatmap: User × System accuracy matrix."""
    user_prompts = sorted(dimensions['user_prompts'])
    system_prompts = sorted(dimensions['system_prompts'])
    
    # Build matrix
    matrix = np.zeros((len(user_prompts), len(system_prompts)))
    counts = np.zeros((len(user_prompts), len(system_prompts)))
    
    for stat in stats:
        user = stat.get('user_prompt_style')
        system = stat.get('system_prompt_style')
        
        if user in user_prompts and system in system_prompts:
            u_idx = user_prompts.index(user)
            s_idx = system_prompts.index(system)
            matrix[u_idx, s_idx] += stat.get('accuracy', 0) * 100
            counts[u_idx, s_idx] += 1
    
    # Average
    matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # Labels
    ax.set_xticks(np.arange(len(system_prompts)))
    ax.set_yticks(np.arange(len(user_prompts)))
    ax.set_xticklabels([s.title() for s in system_prompts])
    ax.set_yticklabels([u.title() for u in user_prompts])
    
    # Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Annotate cells
    for i in range(len(user_prompts)):
        for j in range(len(system_prompts)):
            if counts[i, j] > 0:
                text = ax.text(j, i, f'{matrix[i, j]:.1f}%',
                             ha="center", va="center", color="black", fontsize=10, fontweight='bold')
    
    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Accuracy (%)', rotation=-90, va="bottom", fontsize=11)
    
    ax.set_title('Prompt Configuration Performance Matrix', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('System Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('User Prompt Style', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    from . import analyze_results
    analyze_results._save_chart(fig, output_path, chart_num, 'prompt_heatmap')


def generate_user_prompt_impact(results, stats, dimensions, output_path, chart_num):
    """2. User Prompt Impact: Averaged over system prompts."""
    user_prompts = sorted(dimensions['user_prompts'])
    
    # Calculate average accuracy for each user prompt (averaging over system prompts)
    user_scores = defaultdict(lambda: {'accuracies': [], 'tasks': []})
    
    for stat in stats:
        user = stat.get('user_prompt_style')
        if user:
            user_scores[user]['accuracies'].append(stat.get('accuracy', 0) * 100)
            user_scores[user]['tasks'].append(stat.get('task_type', 'unknown'))
    
    # Average per user prompt
    avg_scores = {user: np.mean(data['accuracies']) for user, data in user_scores.items()}
    std_scores = {user: np.std(data['accuracies']) for user, data in user_scores.items()}
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(user_prompts))
    means = [avg_scores.get(u, 0) for u in user_prompts]
    stds = [std_scores.get(u, 0) for u in user_prompts]
    
    # Color by performance
    colors = [analyze_results.SUCCESS_GREEN if m >= 70 else 
              analyze_results.WARNING_ORANGE if m >= 50 else 
              analyze_results.ERROR_RED for m in means]
    
    bars = ax.bar(x_pos, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Annotations
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + stds[i] + 2,
               f'{mean:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.set_xlabel('User Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('User Prompt Impact on Performance\\n(Averaged across System Prompts)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([u.title() for u in user_prompts])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    analyze_results._save_chart(fig, output_path, chart_num, 'user_prompt_impact')


def generate_system_prompt_impact(results, stats, dimensions, output_path, chart_num):
    """3. System Prompt Impact: Averaged over user prompts."""
    system_prompts = sorted(dimensions['system_prompts'])
    
    # Calculate average accuracy for each system prompt
    system_scores = defaultdict(lambda: {'accuracies': []})
    
    for stat in stats:
        system = stat.get('system_prompt_style')
        if system:
            system_scores[system]['accuracies'].append(stat.get('accuracy', 0) * 100)
    
    avg_scores = {s: np.mean(data['accuracies']) for s, data in system_scores.items()}
    std_scores = {s: np.std(data['accuracies']) for s, data in system_scores.items()}
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(system_prompts))
    means = [avg_scores.get(s, 0) for s in system_prompts]
    stds = [std_scores.get(s, 0) for s in system_prompts]
    
    colors = [analyze_results.SUCCESS_GREEN if m >= 70 else 
              analyze_results.WARNING_ORANGE if m >= 50 else 
              analyze_results.ERROR_RED for m in means]
    
    bars = ax.bar(x_pos, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + stds[i] + 2,
               f'{mean:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.set_xlabel('System Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('System Prompt Impact on Performance\\n(Averaged across User Prompts)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([s.title() for s in system_prompts])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    analyze_results._save_chart(fig, output_path, chart_num, 'system_prompt_impact')


def generate_prompt_radar(results, stats, dimensions, output_path, chart_num):
    """4. Prompt Configuration Radar: Multi-dimensional comparison."""
    prompt_configs = sorted(dimensions['prompt_configs'])[:9]  # Limit to 9 for readability
    
    # Calculate average accuracy per config
    config_scores = defaultdict(list)
    for stat in stats:
        user = stat.get('user_prompt_style')
        system = stat.get('system_prompt_style')
        if user and system:
            config_key = f"{user}_{system}"
            if config_key in prompt_configs:
                config_scores[config_key].append(stat.get('accuracy', 0) * 100)
    
    # Average scores
    scores = [np.mean(config_scores[c]) if c in config_scores else 0 for c in prompt_configs]
    
    # Radar chart
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    angles = np.linspace(0, 2 * np.pi, len(prompt_configs), endpoint=False).tolist()
    scores_plot = scores + [scores[0]]  # Close the circle
    angles += angles[:1]
    
    ax.plot(angles, scores_plot, 'o-', linewidth=2, color=analyze_results.INFO_BLUE)
    ax.fill(angles, scores_plot, alpha=0.25, color=analyze_results.INFO_BLUE)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([c.replace('_', '\\n').title() for c in prompt_configs], fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_ylabel('Accuracy (%)', fontsize=10)
    ax.set_title('Prompt Configuration Performance Radar', fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    analyze_results._save_chart(fig, output_path, chart_num, 'prompt_radar')


# Continue with remaining chart generators in next message due to length...
