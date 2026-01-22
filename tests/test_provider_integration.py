#!/usr/bin/env python3
"""
Quick test of model provider integration with TUI
"""

from src.utils.model_providers import ModelProviderManager, ModelInfo
from src.cli.benchmark_config import ModelSpec, BenchmarkConfig, PromptSpec, TestParams

def test_provider_integration():
    """Test model provider and config integration."""
    
    print("="*70)
    print("  MODEL PROVIDER INTEGRATION TEST")
    print("="*70 + "\n")
    
    # 1. Create provider manager
    manager = ModelProviderManager()
    print("✓ Provider manager initialized")
    
    # 2. Check available providers
    available = manager.get_available_providers()
    print(f"✓ Available providers: {list(available.keys())}\n")
    
    # 3. List Ollama models
    ollama_models = manager.list_models_by_provider("ollama")
    print(f"✓ Found {len(ollama_models)} Ollama models\n")
    
    # 4. Demonstrate grouping
    print("Models by Family:")
    grouped_family = manager.group_models(ollama_models, group_by="family")
    for family, models in list(grouped_family.items())[:4]:
        print(f"  {family}: {len(models):2d} models", end="")
        if models:
            print(f" (e.g., {models[0].display_name})")
        else:
            print()
    
    print(f"\nModels by Quantization:")
    grouped_quant = manager.group_models(ollama_models, group_by="quantization")
    for quant, models in list(grouped_quant.items())[:4]:
        print(f"  {quant:20s}: {len(models):2d} models")
    
    # 5. Test filtering
    print(f"\n✓ Filtering examples:")
    
    qwen_models = manager.filter_models(ollama_models, family="qwen")
    print(f"  Qwen models: {len(qwen_models)}")
    
    q2_models = manager.filter_models(ollama_models, quantization="Q2_K")
    print(f"  Q2_K quantized: {len(q2_models)}")
    
    # 6. Create ModelSpec from ModelInfo
    print(f"\n✓ Converting models to ModelSpec:")
    if qwen_models:
        model_info = qwen_models[0]
        spec = ModelSpec(
            name=model_info.name,
            provider="ollama",
            size_params=model_info.size_params,
            family=model_info.family,
            quantization=model_info.quantization,
            size_bytes=model_info.size_bytes,
            tags=[model_info.family]
        )
        print(f"  Example: {spec.display_name}")
    
    # 7. Create config with multiple models
    print(f"\n✓ Creating BenchmarkConfig:")
    selected_models = qwen_models[:2] if len(qwen_models) >= 2 else ollama_models[:2]
    
    model_specs = [
        ModelSpec(
            name=m.name,
            provider="ollama",
            size_params=m.size_params,
            family=m.family,
            quantization=m.quantization,
            size_bytes=m.size_bytes,
            tags=[m.family]
        )
        for m in selected_models[:2]
    ]
    
    config = BenchmarkConfig(
        name="Test Configuration",
        description="Testing model provider integration",
        models=model_specs,
        prompts=PromptSpec(
            user_styles=["minimal", "casual"],
            system_styles=["analytical", "casual"]
        ),
        params=TestParams(
            difficulties=[1, 2],
            task_types=["MEG"],
        ),
        output_dir="test_results"
    )
    
    print(f"  Name: {config.name}")
    print(f"  Models: {len(config.models)}")
    for model in config.models:
        print(f"    • {model.display_name}")
    print(f"  Total tests: {config.total_test_count()}")
    print(f"  Estimated time: {config.estimated_duration_minutes():.0f} min")
    
    print("\n" + "="*70)
    print("  ✅ ALL TESTS PASSED")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        test_provider_integration()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
