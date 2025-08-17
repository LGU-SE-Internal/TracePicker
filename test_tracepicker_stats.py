#!/usr/bin/env python3
"""
测试TracePicker的统计功能和结果保存
类似TraStrainer的测试方式
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracepicker import tracepicker_algorithm


def test_tracepicker_with_stats():
    """测试TracePicker的统计功能"""

    # 数据路径 - 您需要替换为实际的数据路径
    data_path = Path("test/your-experiment-data-folder")

    if not data_path.exists():
        print(f"❌ Data path not found: {data_path}")
        print("Please update the data_path variable with your actual data folder")
        return

    print(f"Testing TracePicker on: {data_path}")
    print("=" * 60)

    # 测试1: 基本采样 (10%)
    print("Test 1: Basic sampling (rate=0.1)")
    print("-" * 50)

    result1 = tracepicker_algorithm(
        data_folder=data_path, sample_rate=0.1, buffer_size=4000, seed=42
    )

    # 提取统计信息
    stats1 = result1.get("statistics", {})

    print(f"Total traces loaded: {stats1.get('total_traces_loaded', 'N/A')}")
    print(f"  - Normal traces: {stats1.get('normal_traces_loaded', 'N/A')}")
    print(f"  - Abnormal traces: {stats1.get('abnormal_traces_loaded', 'N/A')}")
    print()
    print(f"Sampled traces: {result1['sampled_traces']}")
    print(f"  - Normal sampled: {stats1.get('sampled_normal', 'N/A')}")
    print(f"  - Abnormal sampled: {stats1.get('sampled_abnormal', 'N/A')}")
    print()
    print("Sampling ratios:")
    print(f"  - Overall: {result1['sampling_ratio']:.3f}")
    print(
        f"  - Normal rate: {stats1.get('normal_sampling_rate', 'N/A'):.3f}"
        if stats1.get("normal_sampling_rate") is not None
        else "  - Normal rate: N/A"
    )
    print(
        f"  - Abnormal rate: {stats1.get('abnormal_sampling_rate', 'N/A'):.3f}"
        if stats1.get("abnormal_sampling_rate") is not None
        else "  - Abnormal rate: N/A"
    )
    print()
    print("Performance:")
    print(f"  - Total time: {result1['processing_time']:.2f}s")
    print(f"  - Encoding time: {result1['encoding_time']:.2f}s")
    print(f"  - Sampling time: {result1['sampling_time']:.2f}s")
    print(f"  - Other time: {result1['other_time']:.2f}s")

    if stats1.get("output_directory"):
        print(f"  - Results saved to: {stats1['output_directory']}")

    print()

    # 测试2: 高采样率 (25%)
    print("Test 2: High sampling rate (rate=0.25)")
    print("-" * 50)

    result2 = tracepicker_algorithm(
        data_folder=data_path,
        sample_rate=0.25,
        buffer_size=2000,  # 更小的buffer
        seed=42,
    )

    stats2 = result2.get("statistics", {})

    print(f"Sampled traces: {result2['sampled_traces']}")
    print(f"  - Normal sampled: {stats2.get('sampled_normal', 'N/A')}")
    print(f"  - Abnormal sampled: {stats2.get('sampled_abnormal', 'N/A')}")
    print(f"Overall sampling ratio: {result2['sampling_ratio']:.3f}")
    print(f"Processing time: {result2['processing_time']:.2f}s")

    if stats2.get("output_directory"):
        print(f"Results saved to: {stats2['output_directory']}")

    print()

    # 验证采样质量
    print("Sampling Quality Validation:")
    print("-" * 50)

    # 测试1验证
    sampled_normal1 = stats1.get("sampled_normal", 0)
    sampled_abnormal1 = stats1.get("sampled_abnormal", 0)

    print("Test 1 (10% sampling):")
    if sampled_normal1 > 0 and sampled_abnormal1 > 0:
        print("  ✅ Successfully sampled both normal and abnormal traces")
    elif sampled_normal1 > 0:
        print("  ⚠️  Only normal traces sampled")
    elif sampled_abnormal1 > 0:
        print("  ⚠️  Only abnormal traces sampled")
    else:
        print("  ❌ No traces sampled")

    # 测试2验证
    sampled_normal2 = stats2.get("sampled_normal", 0)
    sampled_abnormal2 = stats2.get("sampled_abnormal", 0)

    print("Test 2 (25% sampling):")
    if sampled_normal2 > 0 and sampled_abnormal2 > 0:
        print("  ✅ Successfully sampled both normal and abnormal traces")
    elif sampled_normal2 > 0:
        print("  ⚠️  Only normal traces sampled")
    elif sampled_abnormal2 > 0:
        print("  ⚠️  Only abnormal traces sampled")
    else:
        print("  ❌ No traces sampled")

    # 对比分析
    print()
    print("Comparison Analysis:")
    print("-" * 50)
    print("Test 1 vs Test 2:")
    print(
        f"  - Sampling rate: {result1['sampling_ratio']:.3f} vs {result2['sampling_ratio']:.3f}"
    )
    print(
        f"  - Sampled count: {result1['sampled_traces']} vs {result2['sampled_traces']}"
    )
    print(
        f"  - Processing time: {result1['processing_time']:.2f}s vs {result2['processing_time']:.2f}s"
    )

    if result2["sampled_traces"] > result1["sampled_traces"]:
        print("  ✅ Higher sampling rate produced more samples as expected")
    else:
        print("  ⚠️  Unexpected sampling behavior")


if __name__ == "__main__":
    try:
        test_tracepicker_with_stats()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
