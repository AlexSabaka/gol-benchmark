#!/usr/bin/env python3
"""
Benchmark Visualization Engine

Auto-generates charts from test results.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class VisualizationEngine:
    """Generates visualizations from benchmark results."""
    
    def __init__(self, output_dir: str, dpi: int = 300):
        self.output_dir = Path(output_dir)
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (14, 8)
        plt.rcParams['font.size'] = 11
        plt.rcParams['font.family'] = 'sans-serif'
    
    def load_results(self, results_file: Path) -> List[Dict]:
        """Load results from JSON file."""
        with open(results_file, 'r') as f:
            return json.load(f)
    
    def _save_figure(self, filename: str):
        """Save current figure as PNG."""
        filepath = self.charts_dir / f"{filename}.png"
        plt.savefig(
            filepath,
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
        )
        plt.close()
        print(f"✓ Saved: {filepath}")
        return filepath
    
    def generate_accuracy_by_model_chart(self, results: List[Dict]) -> Path:
        """Generate bar chart of accuracy by model."""
        df = pd.DataFrame(results)
        
        # Group by model and calculate mean accuracy
        model_accuracy = df.groupby('model')['accuracy'].mean().sort_values(ascending=False)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(model_accuracy)))
        bars = ax.bar(range(len(model_accuracy)), model_accuracy.values, color=colors)
        
        ax.set_xticks(range(len(model_accuracy)))
        ax.set_xticklabels(model_accuracy.index, rotation=45, ha='right')
        ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Model', fontsize=12, fontweight='bold')
        ax.set_title('Benchmark Results: Accuracy by Model', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, model_accuracy.values)):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=9)
        
        return self._save_figure("accuracy_by_model")
    
    def generate_accuracy_heatmap(self, results: List[Dict]) -> Path:
        """Generate heatmap of accuracy by model and task type."""
        df = pd.DataFrame(results)
        
        # Pivot table: models x task_type
        pivot = df.pivot_table(
            values='accuracy',
            index='model',
            columns='task_type',
            aggfunc='mean'
        )
        
        fig, ax = plt.subplots(figsize=(10, max(6, len(pivot) * 0.4)))
        sns.heatmap(
            pivot,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            center=50,
            cbar_kws={'label': 'Accuracy (%)'},
            ax=ax,
            vmin=0,
            vmax=100,
            linewidths=0.5,
        )
        
        ax.set_title('Accuracy Heatmap: Models vs Task Types', fontsize=14, fontweight='bold')
        ax.set_ylabel('Model', fontsize=12, fontweight='bold')
        ax.set_xlabel('Task Type', fontsize=12, fontweight='bold')
        
        return self._save_figure("accuracy_heatmap")
    
    def generate_difficulty_analysis(self, results: List[Dict]) -> Path:
        """Generate line chart showing performance across difficulties."""
        df = pd.DataFrame(results)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot line for each model
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            difficulty_acc = model_data.groupby('difficulty')['accuracy'].mean().sort_index()
            ax.plot(difficulty_acc.index, difficulty_acc.values, marker='o', label=model, linewidth=2)
        
        ax.set_xlabel('Difficulty Level', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Model Performance Across Difficulty Levels', fontsize=14, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)
        
        return self._save_figure("difficulty_analysis")
    
    def generate_task_comparison(self, results: List[Dict]) -> Path:
        """Generate comparison of different task types."""
        df = pd.DataFrame(results)
        
        # Create subplots for each task type
        task_types = df['task_type'].unique()
        fig, axes = plt.subplots(1, len(task_types), figsize=(6*len(task_types), 5))
        
        if len(task_types) == 1:
            axes = [axes]
        
        for idx, task_type in enumerate(task_types):
            task_data = df[df['task_type'] == task_type]
            model_acc = task_data.groupby('model')['accuracy'].mean().sort_values(ascending=False)
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(model_acc)))
            axes[idx].barh(range(len(model_acc)), model_acc.values, color=colors)
            axes[idx].set_yticks(range(len(model_acc)))
            axes[idx].set_yticklabels(model_acc.index)
            axes[idx].set_xlabel('Accuracy (%)', fontweight='bold')
            axes[idx].set_title(f'{task_type} Task', fontweight='bold')
            axes[idx].set_xlim(0, 110)
            
            # Add value labels
            for i, val in enumerate(model_acc.values):
                axes[idx].text(val + 1, i, f'{val:.1f}%', va='center', fontsize=9)
        
        fig.suptitle('Accuracy by Task Type', fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        return self._save_figure("task_comparison")
    
    def generate_model_efficiency_matrix(self, results: List[Dict]) -> Path:
        """Generate efficiency matrix (accuracy vs complexity proxy)."""
        df = pd.DataFrame(results)
        
        # Calculate average accuracy and "complexity" (difficulty × task variety)
        model_stats = []
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            avg_acc = model_data['accuracy'].mean()
            model_stats.append({'model': model, 'accuracy': avg_acc})
        
        stats_df = pd.DataFrame(model_stats)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        scatter = ax.scatter(
            range(len(stats_df)),
            stats_df['accuracy'],
            s=300,
            alpha=0.7,
            c=stats_df['accuracy'],
            cmap='viridis',
            edgecolors='black',
            linewidth=2
        )
        
        ax.set_xticks(range(len(stats_df)))
        ax.set_xticklabels(stats_df['model'], rotation=45, ha='right')
        ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Model Efficiency Matrix', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 110)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Accuracy (%)', fontweight='bold')
        
        # Add value labels
        for i, (idx, row) in enumerate(stats_df.iterrows()):
            ax.text(i, row['accuracy'] + 2, f"{row['accuracy']:.1f}%",
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        return self._save_figure("efficiency_matrix")
    
    def generate_distribution_boxplot(self, results: List[Dict]) -> Path:
        """Generate box plot showing accuracy distribution."""
        df = pd.DataFrame(results)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Sort models by median accuracy
        model_medians = df.groupby('model')['accuracy'].median().sort_values(ascending=False)
        sorted_models = model_medians.index.tolist()
        
        data_to_plot = [df[df['model'] == model]['accuracy'].values for model in sorted_models]
        
        bp = ax.boxplot(
            data_to_plot,
            labels=sorted_models,
            patch_artist=True,
            notch=True,
        )
        
        # Color boxes
        colors = plt.cm.Set3(np.linspace(0, 1, len(sorted_models)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_xticklabels(sorted_models, rotation=45, ha='right')
        ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
        ax.set_title('Accuracy Distribution by Model', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 110)
        
        return self._save_figure("distribution_boxplot")
    
    def generate_all_charts(self, results_file: Path) -> Dict[str, Path]:
        """Generate all available charts."""
        print(f"\n📊 Generating visualizations from {results_file}")
        
        results = self.load_results(results_file)
        
        if not results:
            print("⚠️  No results to visualize")
            return {}
        
        charts = {}
        
        print("Generating charts...")
        charts['accuracy_by_model'] = self.generate_accuracy_by_model_chart(results)
        charts['accuracy_heatmap'] = self.generate_accuracy_heatmap(results)
        charts['difficulty_analysis'] = self.generate_difficulty_analysis(results)
        charts['task_comparison'] = self.generate_task_comparison(results)
        charts['efficiency_matrix'] = self.generate_model_efficiency_matrix(results)
        charts['distribution_boxplot'] = self.generate_distribution_boxplot(results)
        
        print(f"\n✓ Generated {len(charts)} charts in {self.charts_dir}")
        return charts
    
    def generate_html_index(self) -> Path:
        """Generate HTML index for browsing charts."""
        charts = list(self.charts_dir.glob("*.png"))
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .gallery { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .chart { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart img { width: 100%; height: auto; }
        .chart h3 { margin-top: 0; color: #666; }
        .timestamp { color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <h1>📊 Benchmark Results</h1>
    <p class="timestamp">Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    <div class="gallery">
"""
        
        for chart_path in sorted(charts):
            chart_name = chart_path.stem
            html += f"""        <div class="chart">
            <h3>{chart_name.replace('_', ' ').title()}</h3>
            <img src="{chart_path.name}" alt="{chart_name}">
        </div>
"""
        
        html += """    </div>
</body>
</html>
"""
        
        index_file = self.output_dir / "index.html"
        with open(index_file, 'w') as f:
            f.write(html)
        
        print(f"✓ Generated HTML index: {index_file}")
        return index_file


if __name__ == "__main__":
    # Example
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    
    engine = VisualizationEngine(str(output_dir))
    print(f"Visualization engine ready")
    print(f"Output: {engine.charts_dir}")
