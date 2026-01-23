#!/usr/bin/env python3

"""Test/demonstrate the enhanced report generation on real result files"""

import sys
import glob
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.stages.analyze_results import analyze_results

def demo_enhanced_reports():
    """Demo the enhanced report generation on any available result files."""
    
    print("🎯 Demonstrating Enhanced Report Generation System")
    print("=" * 60)
    
    # Find any available result files
    result_patterns = [
        'results/*.json.gz',
        'results/*/*.json.gz', 
        'testsets/*.json.gz'
    ]
    
    result_files = []
    for pattern in result_patterns:
        matches = glob.glob(pattern)
        result_files.extend(matches)
    
    if not result_files:
        print("❌ No result files found to analyze")
        print("   Patterns searched:")
        for pattern in result_patterns:
            print(f"     - {pattern}")
        return
    
    print(f"📁 Found {len(result_files)} result files:")
    for file in result_files[:5]:  # Show first 5
        print(f"   - {file}")
    if len(result_files) > 5:
        print(f"   ... and {len(result_files) - 5} more")
    
    # Set up output paths
    output_dir = Path('enhanced_reports_demo')
    output_dir.mkdir(exist_ok=True)
    
    markdown_path = output_dir / 'enhanced_benchmark_report.md'
    charts_dir = output_dir / 'charts'
    
    print(f"\\n📊 Generating enhanced reports...")
    print(f"   📄 Markdown: {markdown_path}")
    print(f"   🌐 HTML: {markdown_path.with_suffix('.html')}")
    print(f"   📈 Charts: {charts_dir}/")
    
    try:
        # Generate enhanced reports
        analyze_results(
            result_files=result_files[:10],  # Limit to first 10 files
            output=str(markdown_path),
            visualize=True,
            output_dir=str(charts_dir)
        )
        
        print("\\n✅ Enhanced Reports Generated Successfully!")
        
        # Show improvements
        print("\\n🔥 Key Enhancements Included:")
        print("   ✅ Fixed malformed markdown (proper newlines)")
        print("   ✅ Comprehensive HTML version with styling")
        print("   ✅ Enhanced error analysis for parse failures")
        print("   ✅ Sophisticated visualizations:")
        
        if charts_dir.exists():
            chart_files = list(charts_dir.glob('*.png'))
            for chart in sorted(chart_files):
                chart_name = chart.stem.replace('_', ' ').title()
                print(f"       📈 {chart_name}")
        
        print("\\n🎉 Demo completed! Check the enhanced_reports_demo/ directory")
        
    except Exception as e:
        print(f"❌ Error during report generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_enhanced_reports()