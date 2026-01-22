"""
Parse and visualize test results from 9 configurations across 3 models.
3 Prompt Styles (minimal, casual, linguistic) × 3 System Styles (analytical, casual, adversarial)
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path

# Configure style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Data from test results
data = {
    'minimal_analytical': {
        'gemma3:4b': 45.37,
        'qwen_reasoning': 40.74,
        'qwen3:1.7b': 35.19,
    },
    'casual_analytical': {
        'qwen_reasoning': 32.41,
        'gemma3:4b': 30.56,
        'qwen3:1.7b': 27.78,
    },
    'linguistic_analytical': {
        'gemma3:4b': 46.30,
        'qwen_reasoning': 40.74,
        'qwen3:1.7b': 24.07,
    },
    'minimal_casual': {
        'qwen3:1.7b': 53.70,
        'gemma3:4b': 25.93,
        'qwen_reasoning': 24.07,
    },
    'casual_casual': {
        'qwen_reasoning': 50.93,
        'qwen3:1.7b': 50.00,
        'gemma3:4b': 43.52,
    },
    'linguistic_casual': {
        'qwen3:1.7b': 56.48,
        'qwen_reasoning': 54.63,
        'gemma3:4b': 28.70,
    },
    'minimal_adversarial': {
        'qwen3:1.7b': 55.56,
        'qwen_reasoning': 50.93,
        'gemma3:4b': 39.81,
    },
    'casual_adversarial': {
        'qwen3:1.7b': 54.63,
        'gemma3:4b': 36.11,
        'qwen_reasoning': 34.26,
    },
    'linguistic_adversarial': {
        'gemma3:4b': 75.93,
        'qwen3:1.7b': 68.52,
        'qwen_reasoning': 67.59,
    },
}

# Short model names
model_names = {
    'gemma3:4b': 'Gemma 3 4B',
    'qwen_reasoning': 'Qwen 2.5 3B Reasoning',
    'qwen3:1.7b': 'Qwen 3 1.7B',
}

# Create output directory
output_dir = Path('docs/images/prompt_benchmark_nov2025')
output_dir.mkdir(parents=True, exist_ok=True)

print(f"📊 Generating visualizations in {output_dir}/\n")

# ============================================================================
# 1. HEATMAP: All 3 Models Across 9 Configurations
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 4))
fig.suptitle('Model Performance Across 9 Prompt Configurations\n(Normalized Accuracy %)', 
             fontsize=14, fontweight='bold', y=1.02)

configs = list(data.keys())
prompt_styles = ['minimal', 'casual', 'linguistic']
system_styles = ['analytical', 'casual', 'adversarial']

for idx, model_key in enumerate(['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']):
    # Build 3x3 matrix for this model
    matrix = np.zeros((3, 3))
    for i, p_style in enumerate(prompt_styles):
        for j, s_style in enumerate(system_styles):
            config_key = f'{p_style}_{s_style}'
            matrix[i, j] = data[config_key][model_key]
    
    # Heatmap
    sns.heatmap(matrix, annot=True, fmt='.1f', cmap='RdYlGn', 
                ax=axes[idx], cbar=True, vmin=20, vmax=80,
                xticklabels=system_styles, yticklabels=prompt_styles)
    axes[idx].set_title(f'{model_names[model_key]}', fontweight='bold')
    axes[idx].set_xlabel('System Prompt Style')
    if idx == 0:
        axes[idx].set_ylabel('User Prompt Style')

plt.tight_layout()
plt.savefig(output_dir / '01_heatmaps_all_models.png', dpi=300, bbox_inches='tight')
print("✅ 01_heatmaps_all_models.png")
plt.close()

# ============================================================================
# 2. GROUPED BAR CHART: All Configurations
# ============================================================================
fig, ax = plt.subplots(figsize=(14, 6))

config_names = [
    'Min\nAnalytical',
    'Cas\nAnalytical', 
    'Ling\nAnalytical',
    'Min\nCasual',
    'Cas\nCasual',
    'Ling\nCasual',
    'Min\nAdversarial',
    'Cas\nAdversarial',
    'Ling\nAdversarial',
]

x = np.arange(len(configs))
width = 0.25

for idx, model_key in enumerate(['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']):
    values = [data[config][model_key] for config in configs]
    ax.bar(x + idx * width, values, width, label=model_names[model_key], alpha=0.85)

ax.set_xlabel('Configuration (Prompt Style × System Style)', fontweight='bold')
ax.set_ylabel('Normalized Accuracy (%)', fontweight='bold')
ax.set_title('Performance Across All 9 Configurations', fontsize=13, fontweight='bold', pad=20)
ax.set_xticks(x + width)
ax.set_xticklabels(config_names, fontsize=9)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 85)

plt.tight_layout()
plt.savefig(output_dir / '02_grouped_bars_all_configs.png', dpi=300, bbox_inches='tight')
print("✅ 02_grouped_bars_all_configs.png")
plt.close()

# ============================================================================
# 3. PROMPT STYLE IMPACT (System Style = Adversarial, Best Case)
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))

prompt_styles_full = ['Minimal', 'Casual', 'Linguistic']
configs_adversarial = ['minimal_adversarial', 'casual_adversarial', 'linguistic_adversarial']

x = np.arange(len(prompt_styles_full))
width = 0.25

for idx, model_key in enumerate(['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']):
    values = [data[config][model_key] for config in configs_adversarial]
    ax.bar(x + idx * width, values, width, label=model_names[model_key], alpha=0.85)

ax.set_xlabel('User Prompt Style', fontweight='bold')
ax.set_ylabel('Normalized Accuracy (%)', fontweight='bold')
ax.set_title('Impact of Prompt Style (System: Adversarial)', fontsize=13, fontweight='bold', pad=20)
ax.set_xticks(x + width)
ax.set_xticklabels(prompt_styles_full)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 85)

plt.tight_layout()
plt.savefig(output_dir / '03_prompt_style_impact.png', dpi=300, bbox_inches='tight')
print("✅ 03_prompt_style_impact.png")
plt.close()

# ============================================================================
# 4. SYSTEM STYLE IMPACT (Prompt Style = Linguistic, Best Case)
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))

system_styles_full = ['Analytical', 'Casual', 'Adversarial']
configs_linguistic = ['linguistic_analytical', 'linguistic_casual', 'linguistic_adversarial']

x = np.arange(len(system_styles_full))
width = 0.25

for idx, model_key in enumerate(['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']):
    values = [data[config][model_key] for config in configs_linguistic]
    ax.bar(x + idx * width, values, width, label=model_names[model_key], alpha=0.85)

ax.set_xlabel('System Prompt Style', fontweight='bold')
ax.set_ylabel('Normalized Accuracy (%)', fontweight='bold')
ax.set_title('Impact of System Prompt Style (User Prompt: Linguistic)', fontsize=13, fontweight='bold', pad=20)
ax.set_xticks(x + width)
ax.set_xticklabels(system_styles_full)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 85)

plt.tight_layout()
plt.savefig(output_dir / '04_system_style_impact.png', dpi=300, bbox_inches='tight')
print("✅ 04_system_style_impact.png")
plt.close()

# ============================================================================
# 5. MODEL COMPARISON: Min/Max Performance
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))

all_accuracies = {model: [] for model in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']}
for config in configs:
    for model in all_accuracies:
        all_accuracies[model].append(data[config][model])

models_list = [model_names[k] for k in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']]
mins = [min(all_accuracies[k]) for k in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']]
maxs = [max(all_accuracies[k]) for k in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']]
means = [np.mean(all_accuracies[k]) for k in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']]

x = np.arange(len(models_list))
width = 0.25

ax.bar(x - width, mins, width, label='Minimum', alpha=0.85, color='#d62728')
ax.bar(x, means, width, label='Average', alpha=0.85, color='#2ca02c')
ax.bar(x + width, maxs, width, label='Maximum', alpha=0.85, color='#1f77b4')

ax.set_ylabel('Normalized Accuracy (%)', fontweight='bold')
ax.set_title('Model Performance Range (Min/Avg/Max)', fontsize=13, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(models_list)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 85)

# Add value labels
for i, (mi, me, ma) in enumerate(zip(mins, means, maxs)):
    ax.text(i - width, mi + 1, f'{mi:.1f}%', ha='center', fontsize=8)
    ax.text(i, me + 1, f'{me:.1f}%', ha='center', fontsize=8)
    ax.text(i + width, ma + 1, f'{ma:.1f}%', ha='center', fontsize=8)

plt.tight_layout()
plt.savefig(output_dir / '05_model_performance_range.png', dpi=300, bbox_inches='tight')
print("✅ 05_model_performance_range.png")
plt.close()

# ============================================================================
# 6. RADAR CHART: Model Comparison Across 9 Configs
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5), subplot_kw=dict(projection='polar'))
fig.suptitle('Model Performance Across All 9 Configurations (Radar)', 
             fontsize=14, fontweight='bold', y=0.98)

angles = np.linspace(0, 2 * np.pi, len(configs), endpoint=False).tolist()
angles += angles[:1]  # Complete the circle

for idx, model_key in enumerate(['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']):
    ax = axes[idx]
    values = [data[config][model_key] for config in configs]
    values += values[:1]  # Complete the circle
    
    ax.plot(angles, values, 'o-', linewidth=2, label=model_names[model_key])
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([c.replace('_', '\n') for c in configs], fontsize=8)
    ax.set_ylim(0, 80)
    ax.set_title(model_names[model_key], fontweight='bold', pad=20)
    ax.grid(True)

plt.tight_layout()
plt.savefig(output_dir / '06_radar_all_configs.png', dpi=300, bbox_inches='tight')
print("✅ 06_radar_all_configs.png")
plt.close()

# ============================================================================
# 7. BEST/WORST CONFIGURATIONS COMPARISON
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 6))

# Find best and worst for each model
best_worst = {}
for model_key in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']:
    configs_scores = [(config, data[config][model_key]) for config in configs]
    best_config, best_score = max(configs_scores, key=lambda x: x[1])
    worst_config, worst_score = min(configs_scores, key=lambda x: x[1])
    best_worst[model_names[model_key]] = {
        'best': (best_config, best_score),
        'worst': (worst_config, worst_score),
    }

models_list = list(best_worst.keys())
best_scores = [best_worst[m]['best'][1] for m in models_list]
worst_scores = [best_worst[m]['worst'][1] for m in models_list]

x = np.arange(len(models_list))
width = 0.35

ax.bar(x - width/2, best_scores, width, label='Best Configuration', alpha=0.85, color='#2ca02c')
ax.bar(x + width/2, worst_scores, width, label='Worst Configuration', alpha=0.85, color='#d62728')

ax.set_ylabel('Normalized Accuracy (%)', fontweight='bold')
ax.set_title('Best vs Worst Configuration Performance by Model', fontsize=13, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(models_list)
ax.legend(loc='upper left', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 85)

# Add labels
for i, model in enumerate(models_list):
    best_config = best_worst[model]['best'][0]
    worst_config = best_worst[model]['worst'][0]
    ax.text(i - width/2, best_scores[i] + 1, f'{best_config}', ha='center', fontsize=8, rotation=0)
    ax.text(i + width/2, worst_scores[i] + 1, f'{worst_config}', ha='center', fontsize=8, rotation=0)

plt.tight_layout()
plt.savefig(output_dir / '07_best_worst_configs.png', dpi=300, bbox_inches='tight')
print("✅ 07_best_worst_configs.png")
plt.close()

# ============================================================================
# 8. SUMMARY STATISTICS TABLE
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 4))
ax.axis('tight')
ax.axis('off')

summary_data = []
for model_key in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']:
    accuracies = [data[config][model_key] for config in configs]
    summary_data.append([
        model_names[model_key],
        f'{max(accuracies):.2f}%',
        f'{min(accuracies):.2f}%',
        f'{np.mean(accuracies):.2f}%',
        f'{np.std(accuracies):.2f}%',
    ])

table = ax.table(cellText=summary_data,
                colLabels=['Model', 'Max', 'Min', 'Mean', 'Std Dev'],
                cellLoc='center',
                loc='center',
                colWidths=[0.3, 0.15, 0.15, 0.15, 0.15])

table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Style header
for i in range(5):
    table[(0, i)].set_facecolor('#40466e')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Alternate row colors
for i in range(1, 4):
    for j in range(5):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#f0f0f0')
        else:
            table[(i, j)].set_facecolor('#ffffff')

plt.title('Performance Summary Statistics', fontsize=13, fontweight='bold', pad=20)
plt.savefig(output_dir / '08_summary_statistics.png', dpi=300, bbox_inches='tight')
print("✅ 08_summary_statistics.png")
plt.close()

# ============================================================================
# Generate JSON Summary
# ============================================================================
summary_json = {
    'test_date': datetime.now().isoformat(),
    'test_configurations': 9,
    'models': list(model_names.values()),
    'configurations': configs,
    'data': data,
    'statistics': {
        model_names[k]: {
            'max': float(max([data[config][k] for config in configs])),
            'min': float(min([data[config][k] for config in configs])),
            'mean': float(np.mean([data[config][k] for config in configs])),
            'std': float(np.std([data[config][k] for config in configs])),
        }
        for k in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']
    }
}

with open(output_dir / 'summary.json', 'w') as f:
    json.dump(summary_json, f, indent=2)

print("✅ summary.json")
print(f"\n📊 All visualizations saved to {output_dir}/\n")

# Print summary
print("=" * 80)
print("PERFORMANCE SUMMARY")
print("=" * 80)
for model_key in ['gemma3:4b', 'qwen_reasoning', 'qwen3:1.7b']:
    accuracies = [data[config][model_key] for config in configs]
    print(f"\n{model_names[model_key]}:")
    print(f"  Max:  {max(accuracies):.2f}%")
    print(f"  Min:  {min(accuracies):.2f}%")
    print(f"  Avg:  {np.mean(accuracies):.2f}%")
    print(f"  Std:  {np.std(accuracies):.2f}%")

print("\n" + "=" * 80)
