#!/usr/bin/env python3
"""
Generate visualizations for prompt analysis report.
Creates heatmaps, bar charts, and performance comparison graphs.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 11
plt.rcParams['lines.linewidth'] = 2

# Create output directory
output_dir = Path("./analysis_visualizations")
output_dir.mkdir(exist_ok=True)

# ======================== DATA PREPARATION ========================

# Complete test matrix data
data_matrix = {
    'minimal': {
        'qwen3:0.6b': {'adversarial': 53.70, 'casual': 35.19, 'analytical': 35.19},
        'gemma3:1b': {'adversarial': 27.78, 'casual': 35.05, 'analytical': 57.41},
    },
    'casual': {
        'qwen3:0.6b': {'adversarial': 43.52, 'casual': 34.26, 'analytical': 50.00},
        'gemma3:1b': {'adversarial': 39.81, 'casual': 36.11, 'analytical': 52.78},
    },
    'linguistic': {
        'qwen3:0.6b': {'adversarial': 62.96, 'casual': 63.89, 'analytical': 47.22},
        'gemma3:1b': {'adversarial': 79.63, 'casual': 83.33, 'analytical': 75.00},
    },
}

# ======================== VISUALIZATION 1: HEATMAP BY MODEL & USER PROMPT ========================

def plot_heatmap_qwen():
    """Heatmap for qwen3:0.6b across all configurations."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    
    for idx, user_style in enumerate(['minimal', 'casual', 'linguistic']):
        system_styles = ['adversarial', 'casual', 'analytical']
        values = [data_matrix[user_style]['qwen3:0.6b'][s] for s in system_styles]
        
        # Create heatmap data
        heatmap_data = np.array([values])
        
        ax = axes[idx]
        sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='RdYlGn', vmin=30, vmax=65,
                    xticklabels=system_styles, yticklabels=['Accuracy %'], ax=ax,
                    cbar_kws={'label': 'Accuracy (%)'}, linewidths=2, linecolor='black')
        
        ax.set_title(f'qwen3:0.6b\n(User Prompt: {user_style.upper()})', fontsize=12, fontweight='bold')
        ax.set_xlabel('System Prompt Style', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'heatmap_qwen3_0_6b.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: heatmap_qwen3_0_6b.png")
    plt.close()

def plot_heatmap_gemma():
    """Heatmap for gemma3:1b across all configurations."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    
    for idx, user_style in enumerate(['minimal', 'casual', 'linguistic']):
        system_styles = ['adversarial', 'casual', 'analytical']
        values = [data_matrix[user_style]['gemma3:1b'][s] for s in system_styles]
        
        # Create heatmap data
        heatmap_data = np.array([values])
        
        ax = axes[idx]
        sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='RdYlGn', vmin=25, vmax=85,
                    xticklabels=system_styles, yticklabels=['Accuracy %'], ax=ax,
                    cbar_kws={'label': 'Accuracy (%)'}, linewidths=2, linecolor='black')
        
        ax.set_title(f'gemma3:1b\n(User Prompt: {user_style.upper()})', fontsize=12, fontweight='bold')
        ax.set_xlabel('System Prompt Style', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'heatmap_gemma3_1b.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: heatmap_gemma3_1b.png")
    plt.close()

# ======================== VISUALIZATION 2: CROSS-COMPARISON HEATMAP ========================

def plot_comparison_matrix():
    """Heatmap showing qwen vs gemma performance difference."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, user_style in enumerate(['minimal', 'casual', 'linguistic']):
        system_styles = ['adversarial', 'casual', 'analytical']
        qwen_vals = [data_matrix[user_style]['qwen3:0.6b'][s] for s in system_styles]
        gemma_vals = [data_matrix[user_style]['gemma3:1b'][s] for s in system_styles]
        
        # Calculate difference (gemma - qwen, positive means gemma better)
        diff = np.array([g - q for g, q in zip(gemma_vals, qwen_vals)])
        diff_heatmap = np.array([diff])
        
        ax = axes[idx]
        sns.heatmap(diff_heatmap, annot=True, fmt='.1f', cmap='coolwarm', center=0,
                    vmin=-30, vmax=30, xticklabels=system_styles, yticklabels=['Δ Accuracy %'], ax=ax,
                    cbar_kws={'label': 'Δ (Gemma - Qwen) %'}, linewidths=2, linecolor='black')
        
        ax.set_title(f'Performance Gap\n(User Prompt: {user_style.upper()})\nPositive = Gemma Better',
                    fontsize=12, fontweight='bold')
        ax.set_xlabel('System Prompt Style', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'heatmap_comparison_matrix.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: heatmap_comparison_matrix.png")
    plt.close()

# ======================== VISUALIZATION 3: LINE PLOTS - SYSTEM PROMPT EFFECT ========================

def plot_system_prompt_effect():
    """Line plot showing how system prompt affects performance by model."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    system_styles = ['adversarial', 'casual', 'analytical']
    colors = {'qwen3:0.6b': '#1f77b4', 'gemma3:1b': '#ff7f0e'}
    markers = {'qwen3:0.6b': 'o', 'gemma3:1b': 's'}
    
    for idx, user_style in enumerate(['minimal', 'casual', 'linguistic']):
        ax = axes[idx]
        
        for model in ['qwen3:0.6b', 'gemma3:1b']:
            values = [data_matrix[user_style][model][s] for s in system_styles]
            ax.plot(system_styles, values, marker=markers[model], color=colors[model],
                   linewidth=2.5, markersize=10, label=model)
            
            # Add value labels
            for i, v in enumerate(values):
                ax.text(i, v + 2, f'{v:.1f}%', ha='center', fontsize=9, fontweight='bold')
        
        ax.set_title(f'User Prompt: {user_style.upper()}', fontsize=12, fontweight='bold')
        ax.set_xlabel('System Prompt Style', fontsize=11)
        ax.set_ylabel('Accuracy (%)', fontsize=11)
        ax.set_ylim(20, 90)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'line_system_prompt_effect.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: line_system_prompt_effect.png")
    plt.close()

# ======================== VISUALIZATION 4: BAR CHARTS - USER PROMPT EFFECT ========================

def plot_user_prompt_effect():
    """Bar chart showing how user prompt affects performance by model."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    user_styles = ['minimal', 'casual', 'linguistic']
    system_styles = ['adversarial', 'casual', 'analytical']
    
    x = np.arange(len(user_styles))
    width = 0.15
    
    colors_map = {
        'adversarial': '#d62728',
        'casual': '#2ca02c',
        'analytical': '#9467bd'
    }
    
    for model in ['qwen3:0.6b', 'gemma3:1b']:
        for idx, system_style in enumerate(system_styles):
            values = [data_matrix[user_style][model][system_style] for user_style in user_styles]
            offset = width * (idx - 1 + (0.5 if model == 'gemma3:1b' else 0))
            
            label = f'{system_style} ({model})'
            ax.bar(x + offset, values, width, label=label, alpha=0.8)
    
    ax.set_xlabel('User Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Across All Prompt Combinations', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([s.upper() for s in user_styles], fontsize=11)
    ax.legend(fontsize=9, ncol=3, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'bar_user_prompt_effect.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: bar_user_prompt_effect.png")
    plt.close()

# ======================== VISUALIZATION 5: PERFORMANCE RANGE ANALYSIS ========================

def plot_performance_ranges():
    """Show performance range for each model across all configurations."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    models = ['qwen3:0.6b', 'gemma3:1b']
    colors_bars = {'qwen3:0.6b': '#1f77b4', 'gemma3:1b': '#ff7f0e'}
    
    for model_idx, model in enumerate(models):
        all_values = []
        for user_style in ['minimal', 'casual', 'linguistic']:
            for system_style in ['adversarial', 'casual', 'analytical']:
                all_values.append(data_matrix[user_style][model][system_style])
        
        all_values = np.array(all_values)
        mean_val = all_values.mean()
        min_val = all_values.min()
        max_val = all_values.max()
        std_val = all_values.std()
        
        # Plot range as error bar
        ax.errorbar(model_idx, mean_val, 
                   yerr=[[mean_val - min_val], [max_val - mean_val]],
                   fmt='o', markersize=12, capsize=10, capthick=2,
                   color=colors_bars[model], label=model, linewidth=2)
        
        # Add annotations
        ax.text(model_idx, max_val + 3, f'Max: {max_val:.1f}%', ha='center', fontsize=10, fontweight='bold')
        ax.text(model_idx, min_val - 3, f'Min: {min_val:.1f}%', ha='center', fontsize=10, fontweight='bold')
        ax.text(model_idx, mean_val, f'Mean: {mean_val:.1f}%', ha='right', fontsize=9, 
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Performance Range Across All Configurations\n(Min-Max with Mean)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, fontsize=11)
    ax.set_ylim(15, 95)
    ax.grid(axis='y', alpha=0.3)
    ax.legend(fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_ranges.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: performance_ranges.png")
    plt.close()

# ======================== VISUALIZATION 6: COMPLETE HEATMAP MATRIX ========================

def plot_complete_heatmap_matrix():
    """Single comprehensive heatmap showing all combinations."""
    # Prepare data structure for heatmap
    heatmap_data_qwen = []
    heatmap_data_gemma = []
    
    user_styles = ['minimal', 'casual', 'linguistic']
    system_styles = ['adversarial', 'casual', 'analytical']
    
    for user_style in user_styles:
        qwen_row = [data_matrix[user_style]['qwen3:0.6b'][s] for s in system_styles]
        gemma_row = [data_matrix[user_style]['gemma3:1b'][s] for s in system_styles]
        heatmap_data_qwen.append(qwen_row)
        heatmap_data_gemma.append(gemma_row)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Qwen heatmap
    sns.heatmap(np.array(heatmap_data_qwen), annot=True, fmt='.2f', cmap='RdYlGn',
               vmin=30, vmax=65, xticklabels=system_styles, yticklabels=user_styles,
               ax=axes[0], cbar_kws={'label': 'Accuracy (%)'}, linewidths=2, linecolor='black',
               annot_kws={"size": 12, "weight": "bold"})
    axes[0].set_title('qwen3:0.6b Performance Matrix', fontsize=13, fontweight='bold')
    axes[0].set_xlabel('System Prompt Style', fontsize=11)
    axes[0].set_ylabel('User Prompt Style', fontsize=11)
    
    # Gemma heatmap
    sns.heatmap(np.array(heatmap_data_gemma), annot=True, fmt='.2f', cmap='RdYlGn',
               vmin=25, vmax=85, xticklabels=system_styles, yticklabels=user_styles,
               ax=axes[1], cbar_kws={'label': 'Accuracy (%)'}, linewidths=2, linecolor='black',
               annot_kws={"size": 12, "weight": "bold"})
    axes[1].set_title('gemma3:1b Performance Matrix', fontsize=13, fontweight='bold')
    axes[1].set_xlabel('System Prompt Style', fontsize=11)
    axes[1].set_ylabel('User Prompt Style', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'heatmap_complete_matrix.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: heatmap_complete_matrix.png")
    plt.close()

# ======================== VISUALIZATION 7: SPIDER/RADAR CHART ========================

def plot_radar_comparison():
    """Radar chart comparing models across different prompt combinations."""
    categories = ['Min+Adv', 'Min+Cas', 'Min+Ana', 'Cas+Adv', 'Cas+Cas', 'Cas+Ana', 'Ling+Adv', 'Ling+Cas', 'Ling+Ana']
    
    qwen_values = [
        53.70, 35.19, 35.19,  # minimal
        43.52, 34.26, 50.00,  # casual
        62.96, 63.89, 47.22   # linguistic
    ]
    
    gemma_values = [
        27.78, 35.05, 57.41,  # minimal
        39.81, 36.11, 52.78,  # casual
        79.63, 83.33, 75.00   # linguistic
    ]
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    qwen_values_plot = qwen_values + [qwen_values[0]]
    gemma_values_plot = gemma_values + [gemma_values[0]]
    angles_plot = angles + [angles[0]]
    
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))
    
    ax.plot(angles_plot, qwen_values_plot, 'o-', linewidth=2, label='qwen3:0.6b', color='#1f77b4')
    ax.fill(angles_plot, qwen_values_plot, alpha=0.25, color='#1f77b4')
    
    ax.plot(angles_plot, gemma_values_plot, 's-', linewidth=2, label='gemma3:1b', color='#ff7f0e')
    ax.fill(angles_plot, gemma_values_plot, alpha=0.25, color='#ff7f0e')
    
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(20, 85)
    ax.set_yticks([30, 45, 60, 75])
    ax.set_rlabel_position(0)
    ax.grid(True)
    
    ax.set_title('Performance Across All 9 Prompt Combinations\n(User+System)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'radar_all_combinations.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: radar_all_combinations.png")
    plt.close()

# ======================== VISUALIZATION 8: PERFORMANCE DELTA ANALYSIS ========================

def plot_performance_deltas():
    """Show performance improvements/degradations."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Qwen: Effect of system prompt on minimal prompts
    ax = axes[0, 0]
    categories = ['adversarial', 'casual', 'analytical']
    values = [53.70, 35.19, 35.19]
    baseline = 35.19
    deltas = [v - baseline for v in values]
    colors = ['green' if d > 0 else 'red' for d in deltas]
    
    bars = ax.bar(categories, deltas, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_ylabel('Δ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('qwen3:0.6b: System Prompt Effect\n(Minimal User Prompt)', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    for bar, delta in zip(bars, deltas):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{delta:+.1f}%', ha='center', va='bottom' if delta > 0 else 'top', fontweight='bold')
    
    # 2. Gemma: Effect of system prompt on minimal prompts
    ax = axes[0, 1]
    values = [27.78, 35.05, 57.41]
    baseline = 35.05
    deltas = [v - baseline for v in values]
    colors = ['green' if d > 0 else 'red' for d in deltas]
    
    bars = ax.bar(categories, deltas, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_ylabel('Δ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('gemma3:1b: System Prompt Effect\n(Minimal User Prompt)', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    for bar, delta in zip(bars, deltas):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{delta:+.1f}%', ha='center', va='bottom' if delta > 0 else 'top', fontweight='bold')
    
    # 3. Qwen: Effect of user prompt on casual system
    ax = axes[1, 0]
    user_categories = ['minimal', 'casual', 'linguistic']
    values = [35.19, 34.26, 63.89]
    baseline = 34.26
    deltas = [v - baseline for v in values]
    colors = ['green' if d > 0 else 'red' for d in deltas]
    
    bars = ax.bar(user_categories, deltas, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_ylabel('Δ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('qwen3:0.6b: User Prompt Effect\n(Casual System Prompt)', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    for bar, delta in zip(bars, deltas):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{delta:+.1f}%', ha='center', va='bottom' if delta > 0 else 'top', fontweight='bold')
    
    # 4. Gemma: Effect of user prompt on casual system
    ax = axes[1, 1]
    values = [35.05, 36.11, 83.33]
    baseline = 36.11
    deltas = [v - baseline for v in values]
    colors = ['green' if d > 0 else 'red' for d in deltas]
    
    bars = ax.bar(user_categories, deltas, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_ylabel('Δ Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('gemma3:1b: User Prompt Effect\n(Casual System Prompt)', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    for bar, delta in zip(bars, deltas):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{delta:+.1f}%', ha='center', va='bottom' if delta > 0 else 'top', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_deltas.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: performance_deltas.png")
    plt.close()

# ======================== MAIN EXECUTION ========================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GENERATING PROMPT ANALYSIS VISUALIZATIONS")
    print("="*60 + "\n")
    
    plot_heatmap_qwen()
    plot_heatmap_gemma()
    plot_comparison_matrix()
    plot_system_prompt_effect()
    plot_user_prompt_effect()
    plot_performance_ranges()
    plot_complete_heatmap_matrix()
    plot_radar_comparison()
    plot_performance_deltas()
    
    print("\n" + "="*60)
    print(f"✅ ALL VISUALIZATIONS COMPLETE!")
    print(f"📁 Saved to: {output_dir.absolute()}")
    print("="*60 + "\n")
