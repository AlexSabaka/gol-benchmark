#!/usr/bin/env python3
"""
AceMath Quantization Analysis Visualization Generator

Generates comprehensive visualizations for AceMath-1.5B quantization performance
across 9 prompt configurations (3 user styles × 3 system styles).

Outputs 300 DPI PNG files suitable for presentation and publication.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings('ignore')

# Configure style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 100

# Data extracted from results_AceMath_quantizations.txt
data = {
    # User Prompt: minimal
    'minimal_adversarial': {
        'F16': 27.78,
        'Q2_K': 27.78,
        'Q8_0': 31.48,
        'Q4_K_M': 30.56,
    },
    'minimal_casual': {
        'F16': 40.74,
        'Q2_K': 50.00,
        'Q8_0': 40.74,
        'Q4_K_M': 46.30,
    },
    'minimal_analytical': {
        'F16': 27.78,
        'Q2_K': 30.56,
        'Q8_0': 27.78,
        'Q4_K_M': 24.07,
    },
    # User Prompt: casual
    'casual_adversarial': {
        'F16': 31.48,
        'Q2_K': 37.96,
        'Q8_0': 31.48,
        'Q4_K_M': 33.33,
    },
    'casual_casual': {
        'F16': 26.85,
        'Q2_K': 36.11,
        'Q8_0': 26.85,
        'Q4_K_M': 28.70,
    },
    'casual_analytical': {
        'F16': 27.78,
        'Q2_K': 35.19,
        'Q8_0': 25.93,
        'Q4_K_M': 32.41,
    },
    # User Prompt: linguistic
    'linguistic_adversarial': {
        'F16': 34.26,
        'Q2_K': 35.19,
        'Q8_0': 32.41,
        'Q4_K_M': 32.41,
    },
    'linguistic_casual': {
        'F16': 33.33,
        'Q2_K': 50.00,
        'Q8_0': 32.41,
        'Q4_K_M': 39.81,
    },
    'linguistic_analytical': {
        'F16': 34.26,
        'Q2_K': 37.04,
        'Q8_0': 31.48,
        'Q4_K_M': 31.48,
    },
}

# Configuration labels
USER_PROMPTS = ['minimal', 'casual', 'linguistic']
SYSTEM_PROMPTS = ['adversarial', 'casual', 'analytical']
QUANTIZATIONS = ['F16', 'Q2_K', 'Q8_0', 'Q4_K_M']

OUTPUT_DIR = Path('./analysis_visualizations_acemath')
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"📊 AceMath Quantization Analysis Visualization Generator")
print(f"📁 Output directory: {OUTPUT_DIR}")
print(f"🎯 Generating 10+ visualizations at 300 DPI...")
print()


def save_fig(filename: str, dpi: int = 300, bbox_inches: str = 'tight', pad_inches: float = 0.3):
    """Save figure at high DPI."""
    filepath = OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches, pad_inches=pad_inches, facecolor='white')
    plt.close()
    size_mb = filepath.stat().st_size / 1_000_000
    print(f"✓ {filename:50s} ({size_mb:.2f} MB)")


# ============================================================================
# 1. HEATMAP: Quantization Performance Across All Configurations
# ============================================================================

print("\n📈 Chart 1: Performance Heatmap (All Configurations)")

# Create matrix: rows = configurations, cols = quantizations
configs = [f"{u}_{s}" for u in USER_PROMPTS for s in SYSTEM_PROMPTS]
config_labels = [f"{u.capitalize()}\n+ {s.capitalize()}" for u in USER_PROMPTS for s in SYSTEM_PROMPTS]

matrix = np.array([[data[config][quant] for quant in QUANTIZATIONS] for config in configs])

fig, ax = plt.subplots(figsize=(10, 10))
sns.heatmap(
    matrix,
    annot=True,
    fmt='.1f',
    cmap='RdYlGn',
    vmin=20,
    vmax=55,
    cbar_kws={'label': 'Accuracy (%)'},
    xticklabels=QUANTIZATIONS,
    yticklabels=config_labels,
    linewidths=0.5,
    linecolor='gray',
    ax=ax,
    cbar=True,
)
ax.set_title('AceMath-1.5B Quantization Performance\nAcross All 9 Prompt Configurations', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xlabel('Quantization Format', fontsize=12, fontweight='bold')
ax.set_ylabel('Prompt Configuration', fontsize=12, fontweight='bold')
plt.tight_layout()
save_fig('01_heatmap_all_configurations.png')
print(f"   Matrix: {configs[0]} → {configs[-1]}")
print(f"   Range: {matrix.min():.1f}% - {matrix.max():.1f}%")


# ============================================================================
# 2. RADAR CHART: Quantization Comparison (All 9 Configs)
# ============================================================================

print("\n📈 Chart 2: Radar Chart (Quantizations Across All Configs)")

fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))

angles = np.linspace(0, 2 * np.pi, len(configs), endpoint=False).tolist()
angles += angles[:1]  # Complete the circle

colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
config_names_short = [f"{u[0].upper()}{s[0].upper()}" for u in USER_PROMPTS for s in SYSTEM_PROMPTS]

for idx, quant in enumerate(QUANTIZATIONS):
    values = [data[config][quant] for config in configs]
    values += values[:1]
    ax.plot(angles, values, 'o-', linewidth=2, label=quant, color=colors[idx], markersize=6)
    ax.fill(angles, values, alpha=0.15, color=colors[idx])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(config_names_short, size=10)
ax.set_ylim(20, 55)
ax.set_yticks([25, 30, 35, 40, 45, 50, 55])
ax.set_rlabel_position(0)
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11, framealpha=0.95)
ax.set_title('AceMath Quantization Performance Radar\n(9 Prompt Configurations)', 
             fontsize=14, fontweight='bold', pad=30)
plt.tight_layout()
save_fig('02_radar_quantization_comparison.png')
print(f"   9 configurations × 4 quantizations")
print(f"   Axes: {config_names_short[:3]}... (Min User + 3 System Prompts each)")


# ============================================================================
# 3. GROUPED BAR CHART: Performance by Quantization
# ============================================================================

print("\n📈 Chart 3: Grouped Bar Chart (Quantizations)")

fig, ax = plt.subplots(figsize=(14, 8))

x = np.arange(len(configs))
width = 0.2

for idx, quant in enumerate(QUANTIZATIONS):
    values = [data[config][quant] for config in configs]
    ax.bar(x + idx*width, values, width, label=quant, color=colors[idx], alpha=0.8, edgecolor='black', linewidth=0.5)

ax.set_xlabel('Prompt Configuration', fontsize=12, fontweight='bold')
ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('AceMath-1.5B Performance by Quantization Format\nAcross All Prompt Configurations', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(config_names_short, fontsize=10)
ax.legend(loc='upper left', fontsize=11, framealpha=0.95)
ax.set_ylim(20, 55)
ax.grid(axis='y', alpha=0.3, linestyle='--')
plt.tight_layout()
save_fig('03_grouped_bars_by_quantization.png')
print(f"   {len(QUANTIZATIONS)} quantization formats × {len(configs)} configurations")


# ============================================================================
# 4. BOX PLOT: Distribution by Quantization
# ============================================================================

print("\n📈 Chart 4: Box Plot (Distribution by Quantization)")

fig, ax = plt.subplots(figsize=(10, 8))

box_data = [[data[config][quant] for config in configs] for quant in QUANTIZATIONS]
bp = ax.boxplot(box_data, labels=QUANTIZATIONS, patch_artist=True, widths=0.6)

for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Quantization Format', fontsize=12, fontweight='bold')
ax.set_title('AceMath-1.5B Performance Distribution by Quantization\n(Across 9 Prompt Configurations)', 
             fontsize=14, fontweight='bold', pad=20)
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add statistics text
stats_text = "Statistics:\n"
for quant, values in zip(QUANTIZATIONS, box_data):
    mean_val = np.mean(values)
    std_val = np.std(values)
    stats_text += f"{quant}: μ={mean_val:.1f}% σ={std_val:.1f}%\n"

ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
        verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8, pad=0.8))

plt.tight_layout()
save_fig('04_boxplot_distribution.png')
print(f"   Mean ± Std for each quantization")


# ============================================================================
# 5. USER PROMPT IMPACT: Bar Chart (by user prompt style)
# ============================================================================

print("\n📈 Chart 5: Impact of User Prompt Style")

user_scores = {}
for user in USER_PROMPTS:
    configs_for_user = [f"{user}_{sys}" for sys in SYSTEM_PROMPTS]
    user_scores[user] = {
        quant: np.mean([data[config][quant] for config in configs_for_user])
        for quant in QUANTIZATIONS
    }

x_pos = np.arange(len(USER_PROMPTS))
width = 0.2

for idx, quant in enumerate(QUANTIZATIONS):
    values = [user_scores[user][quant] for user in USER_PROMPTS]
    ax.bar(x_pos + idx*width, values, width, label=quant, color=colors[idx], alpha=0.8, edgecolor='black', linewidth=0.5)

fig, ax = plt.subplots(figsize=(11, 7))
for idx, quant in enumerate(QUANTIZATIONS):
    values = [user_scores[user][quant] for user in USER_PROMPTS]
    ax.bar(x_pos + idx*width, values, width, label=quant, color=colors[idx], alpha=0.8, edgecolor='black', linewidth=0.5)

ax.set_xlabel('User Prompt Style', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('Impact of User Prompt Style on Performance\n(Averaged Across System Prompts)', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x_pos + width * 1.5)
ax.set_xticklabels([u.capitalize() for u in USER_PROMPTS], fontsize=11)
ax.legend(loc='upper left', fontsize=11, framealpha=0.95)
ax.set_ylim(25, 45)
ax.grid(axis='y', alpha=0.3, linestyle='--')
plt.tight_layout()
save_fig('05_impact_user_prompt.png')
for user in USER_PROMPTS:
    avg = np.mean([user_scores[user][q] for q in QUANTIZATIONS])
    print(f"   {user.capitalize():15} → Average: {avg:.1f}%")


# ============================================================================
# 6. SYSTEM PROMPT IMPACT: Bar Chart (by system prompt style)
# ============================================================================

print("\n📈 Chart 6: Impact of System Prompt Style")

system_scores = {}
for system in SYSTEM_PROMPTS:
    configs_for_system = [f"{user}_{system}" for user in USER_PROMPTS]
    system_scores[system] = {
        quant: np.mean([data[config][quant] for config in configs_for_system])
        for quant in QUANTIZATIONS
    }

fig, ax = plt.subplots(figsize=(11, 7))
x_pos = np.arange(len(SYSTEM_PROMPTS))

for idx, quant in enumerate(QUANTIZATIONS):
    values = [system_scores[system][quant] for system in SYSTEM_PROMPTS]
    ax.bar(x_pos + idx*width, values, width, label=quant, color=colors[idx], alpha=0.8, edgecolor='black', linewidth=0.5)

ax.set_xlabel('System Prompt Style', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('Impact of System Prompt Style on Performance\n(Averaged Across User Prompts)', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x_pos + width * 1.5)
ax.set_xticklabels([s.capitalize() for s in SYSTEM_PROMPTS], fontsize=11)
ax.legend(loc='upper left', fontsize=11, framealpha=0.95)
ax.set_ylim(25, 45)
ax.grid(axis='y', alpha=0.3, linestyle='--')
plt.tight_layout()
save_fig('06_impact_system_prompt.png')
for system in SYSTEM_PROMPTS:
    avg = np.mean([system_scores[system][q] for q in QUANTIZATIONS])
    print(f"   {system.capitalize():15} → Average: {avg:.1f}%")


# ============================================================================
# 7. QUANTIZATION EFFICIENCY: Performance vs Compression
# ============================================================================

print("\n📈 Chart 7: Quantization Efficiency (Performance vs Compression)")

# Estimated compression ratios
compression = {
    'F16': 1.0,      # Baseline (16-bit float)
    'Q8_0': 0.5,     # 8-bit
    'Q4_K_M': 0.25,  # 4-bit
    'Q2_K': 0.125,   # 2-bit (extreme)
}

fig, ax = plt.subplots(figsize=(11, 8))

for quant in QUANTIZATIONS:
    avg_perf = np.mean([data[config][quant] for config in configs])
    comp_ratio = compression[quant]
    ax.scatter(comp_ratio, avg_perf, s=500, alpha=0.7, label=quant, color=colors[QUANTIZATIONS.index(quant)], edgecolor='black', linewidth=2)
    ax.annotate(quant, (comp_ratio, avg_perf), fontsize=11, fontweight='bold', 
                xytext=(5, 5), textcoords='offset points', ha='left', va='bottom')

ax.set_xlabel('Model Size (Relative to F16)', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Accuracy Across All Configs (%)', fontsize=12, fontweight='bold')
ax.set_title('Quantization Trade-off: Compression vs Performance\nAceMath-1.5B', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xlim(0, 1.1)
ax.set_ylim(33, 36)
ax.grid(True, alpha=0.3, linestyle='--')

# Add annotation
ax.text(0.98, 0.02, 'Lower size ratio = Better compression\nHigher accuracy = Better performance', 
        transform=ax.transAxes, fontsize=10, ha='right', va='bottom',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, pad=0.8))

plt.tight_layout()
save_fig('07_quantization_efficiency.png')

print(f"   Compression ratios: {compression}")


# ============================================================================
# 8. HEATMAP: Quantization by User Prompt
# ============================================================================

print("\n📈 Chart 8: Heatmap (Quantization × User Prompt)")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for user_idx, user in enumerate(USER_PROMPTS):
    matrices = []
    for system in SYSTEM_PROMPTS:
        config = f"{user}_{system}"
        matrices.append([data[config][quant] for quant in QUANTIZATIONS])
    
    matrix = np.array(matrices)
    
    sns.heatmap(
        matrix,
        annot=True,
        fmt='.1f',
        cmap='RdYlGn',
        vmin=20,
        vmax=55,
        xticklabels=QUANTIZATIONS,
        yticklabels=[s.capitalize() for s in SYSTEM_PROMPTS],
        ax=axes[user_idx],
        cbar=(user_idx == 2),
        cbar_kws={'label': 'Accuracy (%)'},
        linewidths=0.5,
        linecolor='gray',
    )
    
    axes[user_idx].set_title(f'{user.capitalize()} User Prompt', fontsize=12, fontweight='bold', pad=10)
    axes[user_idx].set_xlabel('Quantization', fontsize=10, fontweight='bold')
    if user_idx == 0:
        axes[user_idx].set_ylabel('System Prompt', fontsize=10, fontweight='bold')
    else:
        axes[user_idx].set_ylabel('')

fig.suptitle('AceMath Performance: Quantization × User Prompt × System Prompt', 
             fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
save_fig('08_heatmap_by_user_prompt.png')
print(f"   3 panels: one per user prompt style")


# ============================================================================
# 9. PERFORMANCE VARIANCE: Std Dev Analysis
# ============================================================================

print("\n📈 Chart 9: Performance Variance by Quantization")

fig, ax = plt.subplots(figsize=(11, 7))

stds = []
means = []
labels_list = []

for quant in QUANTIZATIONS:
    values = [data[config][quant] for config in configs]
    stds.append(np.std(values))
    means.append(np.mean(values))
    labels_list.append(quant)

x_pos = np.arange(len(QUANTIZATIONS))
ax.bar(x_pos, stds, color=colors, alpha=0.7, edgecolor='black', linewidth=2, width=0.6)

for i, (x, std, mean) in enumerate(zip(x_pos, stds, means)):
    ax.text(x, std + 0.3, f'σ={std:.2f}%\nμ={mean:.1f}%', 
            ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_ylabel('Standard Deviation (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Quantization Format', fontsize=12, fontweight='bold')
ax.set_title('Performance Variance by Quantization Format\n(Lower variance = More stable across prompt configs)', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x_pos)
ax.set_xticklabels(labels_list, fontsize=11)
ax.grid(axis='y', alpha=0.3, linestyle='--')
plt.tight_layout()
save_fig('09_variance_analysis.png')

print(f"   Variance (std dev) for each quantization:")
for quant, std, mean in zip(QUANTIZATIONS, stds, means):
    print(f"   {quant:6} → σ={std:.2f}%, μ={mean:.1f}%")


# ============================================================================
# 10. BEST vs WORST: Configuration Analysis
# ============================================================================

print("\n📈 Chart 10: Best vs Worst Performers")

# Find best and worst configurations
all_scores = [(config, quant, data[config][quant]) 
              for config in configs for quant in QUANTIZATIONS]
all_scores.sort(key=lambda x: x[2], reverse=True)

best_5 = all_scores[:5]
worst_5 = all_scores[-5:]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Best performers
best_labels = [f"{b[0]}\n({b[1]})" for b in best_5]
best_values = [b[2] for b in best_5]
ax1.barh(range(len(best_5)), best_values, color='#2ecc71', alpha=0.8, edgecolor='black', linewidth=1.5)
ax1.set_yticks(range(len(best_5)))
ax1.set_yticklabels(best_labels, fontsize=10)
ax1.set_xlabel('Accuracy (%)', fontsize=11, fontweight='bold')
ax1.set_title('🏆 Top 5 Best Performing Configurations', fontsize=12, fontweight='bold')
ax1.set_xlim(30, 52)
for i, v in enumerate(best_values):
    ax1.text(v - 1, i, f'{v:.1f}%', va='center', ha='right', fontweight='bold', fontsize=10, color='white')

# Worst performers
worst_labels = [f"{w[0]}\n({w[1]})" for w in worst_5]
worst_values = [w[2] for w in worst_5]
ax2.barh(range(len(worst_5)), worst_values, color='#e74c3c', alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.set_yticks(range(len(worst_5)))
ax2.set_yticklabels(worst_labels, fontsize=10)
ax2.set_xlabel('Accuracy (%)', fontsize=11, fontweight='bold')
ax2.set_title('📉 Top 5 Worst Performing Configurations', fontsize=12, fontweight='bold')
ax2.set_xlim(20, 52)
for i, v in enumerate(worst_values):
    ax2.text(v + 0.5, i, f'{v:.1f}%', va='center', ha='left', fontweight='bold', fontsize=10)

plt.suptitle('Configuration Performance Extremes', fontsize=14, fontweight='bold', y=1.00)
plt.tight_layout()
save_fig('10_best_vs_worst_configs.png')

print(f"   🏆 Best: {best_5[0][0]} with {best_5[0][1]} = {best_5[0][2]:.1f}%")
print(f"   📉 Worst: {worst_5[-1][0]} with {worst_5[-1][1]} = {worst_5[-1][2]:.1f}%")


# ============================================================================
# 11. COMBINED METRICS: Overall Leaderboard
# ============================================================================

print("\n📈 Chart 11: Overall Leaderboard (Quantization Ranking)")

fig, ax = plt.subplots(figsize=(12, 7))

quant_stats = {}
for quant in QUANTIZATIONS:
    values = [data[config][quant] for config in configs]
    quant_stats[quant] = {
        'mean': np.mean(values),
        'std': np.std(values),
        'max': np.max(values),
        'min': np.min(values),
    }

# Sort by mean
sorted_quants = sorted(quant_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
quants_sorted = [q[0] for q in sorted_quants]
means_sorted = [q[1]['mean'] for q in sorted_quants]
stds_sorted = [q[1]['std'] for q in sorted_quants]

x_pos = np.arange(len(quants_sorted))
bars = ax.bar(x_pos, means_sorted, yerr=stds_sorted, capsize=10, 
              color=[colors[QUANTIZATIONS.index(q)] for q in quants_sorted],
              alpha=0.8, edgecolor='black', linewidth=2, error_kw={'linewidth': 2})

# Add rank numbers
for i, (bar, mean) in enumerate(zip(bars, means_sorted)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
            f'#{i+1}\n{mean:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Quantization Format', fontsize=12, fontweight='bold')
ax.set_title('AceMath-1.5B Quantization Leaderboard\n(Mean ± Std Dev across all 9 configurations)', 
             fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x_pos)
ax.set_xticklabels(quants_sorted, fontsize=11, fontweight='bold')
ax.set_ylim(32, 37)
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add legend box
legend_text = "Statistics:\n"
for quant in quants_sorted:
    stats = quant_stats[quant]
    legend_text += f"{quant}: max={stats['max']:.1f}%, min={stats['min']:.1f}%, range={stats['max']-stats['min']:.1f}%\n"

ax.text(0.98, 0.02, legend_text, transform=ax.transAxes, fontsize=9.5,
        verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8, pad=0.8))

plt.tight_layout()
save_fig('11_leaderboard_ranking.png')

print(f"\n   Leaderboard (by average accuracy):")
for i, (quant, stats) in enumerate(sorted_quants, 1):
    print(f"   #{i} {quant:6} → {stats['mean']:5.2f}% ± {stats['std']:4.2f}% (range: {stats['max']-stats['min']:.1f}%)")


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*80)
print(f"✅ Successfully generated {11} visualizations!")
print(f"📊 Total file size: {sum((OUTPUT_DIR / f.name).stat().st_size for f in OUTPUT_DIR.glob('*.png')) / 1_000_000:.1f} MB")
print(f"📁 All visualizations saved to: {OUTPUT_DIR.absolute()}")
print("="*80)

# Generate summary statistics
print("\n📋 SUMMARY STATISTICS")
print("-" * 80)
print(f"Total configurations: {len(configs)} (3 user × 3 system prompts)")
print(f"Total quantizations: {len(QUANTIZATIONS)}")
print(f"Total data points: {len(configs) * len(QUANTIZATIONS)}")

all_values = [data[config][quant] for config in configs for quant in QUANTIZATIONS]
print(f"\nOverall Performance:")
print(f"  Mean: {np.mean(all_values):.2f}%")
print(f"  Std Dev: {np.std(all_values):.2f}%")
print(f"  Min: {np.min(all_values):.2f}%")
print(f"  Max: {np.max(all_values):.2f}%")
print(f"  Range: {np.max(all_values) - np.min(all_values):.2f}%")

print("\n✨ Visualizations ready for analysis and reporting!")
