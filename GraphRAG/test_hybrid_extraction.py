# -*- coding: utf-8 -*-
"""
Test Hybrid Extraction (Pattern + LLM Fallback)
So sánh performance giữa Pure Pattern và Hybrid approach
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import time
from enhanced_entity_extractor import EnhancedEntityExtractor
import config

def test_hybrid_vs_pattern():
    """Test so sánh Pattern vs Hybrid"""

    print("=" * 80)
    print("HYBRID EXTRACTION TEST - Pattern + LLM Fallback")
    print("=" * 80)

    # Test queries - bao gồm cả easy và hard cases
    test_queries = [
        # EASY queries (pattern should handle well)
        "Phí rút tiền là bao nhiêu?",
        "Làm sao nạp tiền từ Vietinbank?",
        "Hủy liên kết ngân hàng",

        # MEDIUM queries (pattern may struggle)
        "Rút 500k về bank có mất phí không?",  # "bank" thay vì tên bank cụ thể
        "Tôi muốn ngừng liên kết với VCB",  # "ngừng" thay vì "hủy"
        "Tốn bao nhiêu khi rút tiền?",  # Không có từ "phí"

        # HARD queries (pattern likely fails)
        "Tôi chuyển tiền rồi mà người nhận chưa thấy gì",  # Complex error
        "Disconnect Vietcombank khỏi ví",  # English + slang
        "Giao dịch báo thành công nhưng không về",  # Implicit error
    ]

    extractor = EnhancedEntityExtractor()

    print(f"\n🔧 Config:")
    print(f"   LLM Fallback Enabled: {config.ENABLE_LLM_FALLBACK}")
    print(f"   Fallback Threshold: {config.LLM_FALLBACK_THRESHOLD:.2%}")
    print(f"   Fallback for Questions: {config.LLM_FALLBACK_FOR_QUESTIONS}")
    print(f"   Fallback for Ambiguous: {config.LLM_FALLBACK_FOR_AMBIGUOUS}")

    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print(f"{'='*80}")

        # Measure time
        start_time = time.time()

        try:
            # Extract with hybrid approach
            entities, confidence = extractor.extract_with_confidence(query)
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

            # Count entities
            total_entities = sum(len(v) for k, v in entities.items()
                               if k != 'out_of_scope' and isinstance(v, list))

            print(f"\n📊 Results:")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   Total entities: {total_entities}")
            print(f"   Extraction time: {elapsed_time:.1f}ms")

            if total_entities > 0:
                print(f"\n📌 Extracted Entities:")
                for entity_type, values in entities.items():
                    if values and entity_type != 'out_of_scope' and isinstance(values, list):
                        print(f"   {entity_type}: {values}")
            else:
                print("   ⚠️  No entities extracted!")

            # Determine if LLM was used (confidence = 0.95 indicates LLM)
            used_llm = (confidence == 0.95)
            method = "🤖 LLM" if used_llm else "📝 Pattern"

            print(f"\n💡 Method: {method}")

            results.append({
                "query": query,
                "confidence": confidence,
                "total_entities": total_entities,
                "time_ms": elapsed_time,
                "used_llm": used_llm
            })

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary statistics
    print("\n\n" + "=" * 80)
    print("📊 SUMMARY STATISTICS")
    print("=" * 80)

    llm_count = sum(1 for r in results if r["used_llm"])
    pattern_count = len(results) - llm_count

    print(f"\n📈 Method Distribution:")
    print(f"   Pattern-only: {pattern_count}/{len(results)} ({pattern_count/len(results)*100:.1f}%)")
    print(f"   LLM Fallback: {llm_count}/{len(results)} ({llm_count/len(results)*100:.1f}%)")

    # Average times
    if pattern_count > 0:
        pattern_times = [r["time_ms"] for r in results if not r["used_llm"]]
        avg_pattern_time = sum(pattern_times) / len(pattern_times)
        print(f"\n⏱️  Average Time:")
        print(f"   Pattern: {avg_pattern_time:.1f}ms")

    if llm_count > 0:
        llm_times = [r["time_ms"] for r in results if r["used_llm"]]
        avg_llm_time = sum(llm_times) / len(llm_times)
        print(f"   LLM: {avg_llm_time:.1f}ms")

    # Entity extraction coverage
    avg_entities = sum(r["total_entities"] for r in results) / len(results)
    print(f"\n📊 Entity Coverage:")
    print(f"   Average entities per query: {avg_entities:.1f}")

    zero_entity_count = sum(1 for r in results if r["total_entities"] == 0)
    print(f"   Queries with NO entities: {zero_entity_count}/{len(results)}")

    # Estimated cost (if using LLM)
    if llm_count > 0:
        # Assume ~$0.0001 per LLM call (gpt-4o-mini)
        cost_per_call = 0.0001
        total_cost = llm_count * cost_per_call
        monthly_cost = total_cost * 30  # Assuming same pattern daily

        print(f"\n💰 Estimated Cost:")
        print(f"   Cost for this test: ${total_cost:.6f}")
        print(f"   If same pattern daily (30 days): ${monthly_cost:.4f}/month")

    # Detailed results table
    print(f"\n\n{'='*80}")
    print("📋 DETAILED RESULTS")
    print(f"{'='*80}")
    print(f"{'No.':<4} {'Method':<10} {'Entities':<10} {'Time (ms)':<12} {'Query':<40}")
    print("-" * 80)

    for i, r in enumerate(results, 1):
        method = "LLM" if r["used_llm"] else "Pattern"
        query_short = r["query"][:37] + "..." if len(r["query"]) > 40 else r["query"]
        print(f"{i:<4} {method:<10} {r['total_entities']:<10} {r['time_ms']:<12.1f} {query_short:<40}")

    print("=" * 80)


if __name__ == "__main__":
    test_hybrid_vs_pattern()
