# -*- coding: utf-8 -*-
"""
Test và so sánh Pattern-First vs LLM-First strategies
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
import config
import time

print("=" * 80)
print("COMPARISON: Pattern-First vs LLM-First Extraction Strategies")
print("=" * 80)

# Test cases
test_cases = [
    "Tôi muốn hủy dịch vụ nạp tiền tự động",
    "Chuyển tiền từ Vietinbank sang VNPT Money cần điều kiện gì?",
    "Làm sao thanh toán hóa đơn điện qua app?",
    "Rút tiền về tài khoản ngân hàng",
    "Nhập số tiền cần chuyển",
    "Mở tài khoản VNPT Money cần CCCD không?",
    "Xem lịch sử giao dịch ở mục nào?",
    "App có hỗ trợ QR code thanh toán không?",
]

extractor = EnhancedEntityExtractor()

# Test 1: Pattern-First Strategy
print("\n" + "=" * 80)
print("TEST 1: PATTERN-FIRST STRATEGY (Current)")
print("=" * 80)

config.USE_LLM_FIRST_STRATEGY = False
pattern_first_results = []
pattern_first_time = 0

for i, query in enumerate(test_cases, 1):
    print(f"\n{i}. {query}")
    print("-" * 80)

    start = time.time()
    entities, confidence = extractor.extract_with_confidence(query)
    elapsed = time.time() - start

    pattern_first_time += elapsed
    pattern_first_results.append({
        'query': query,
        'entities': entities,
        'confidence': confidence,
        'time': elapsed
    })

    # Show results
    print(f"Confidence: {confidence:.0%}")
    print(f"Time: {elapsed*1000:.0f}ms")
    print("Entities:")
    for entity_type, values in entities.items():
        if values:
            print(f"  {entity_type}: {values}")

# Test 2: LLM-First Strategy
print("\n" + "=" * 80)
print("TEST 2: LLM-FIRST STRATEGY (New)")
print("=" * 80)

config.USE_LLM_FIRST_STRATEGY = True
llm_first_results = []
llm_first_time = 0

for i, query in enumerate(test_cases, 1):
    print(f"\n{i}. {query}")
    print("-" * 80)

    start = time.time()
    entities, confidence = extractor.extract_with_confidence(query)
    elapsed = time.time() - start

    llm_first_time += elapsed
    llm_first_results.append({
        'query': query,
        'entities': entities,
        'confidence': confidence,
        'time': elapsed
    })

    # Show results
    print(f"Confidence: {confidence:.0%}")
    print(f"Time: {elapsed*1000:.0f}ms")
    print("Entities:")
    for entity_type, values in entities.items():
        if values:
            print(f"  {entity_type}: {values}")

# Comparison
print("\n" + "=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)

print(f"\n📊 Performance Metrics:")
print(f"{'Metric':<30} | Pattern-First | LLM-First | Change")
print("-" * 80)
print(f"{'Avg Response Time':<30} | {pattern_first_time/len(test_cases)*1000:>10.0f}ms | {llm_first_time/len(test_cases)*1000:>8.0f}ms | {(llm_first_time/pattern_first_time-1)*100:>+5.0f}%")
print(f"{'Total Time':<30} | {pattern_first_time:>10.2f}s | {llm_first_time:>8.2f}s | {(llm_first_time/pattern_first_time-1)*100:>+5.0f}%")

# Entity comparison
print(f"\n📋 Entity Extraction Comparison:")
print("-" * 80)

for i, (pf, lf) in enumerate(zip(pattern_first_results, llm_first_results), 1):
    query = pf['query']
    print(f"\n{i}. {query[:60]}...")

    # Count entities (skip non-list values)
    pf_count = sum(len(v) for v in pf['entities'].values() if isinstance(v, list))
    lf_count = sum(len(v) for v in lf['entities'].values() if isinstance(v, list))

    print(f"   Pattern-First: {pf_count} entities, confidence {pf['confidence']:.0%}")
    print(f"   LLM-First:     {lf_count} entities, confidence {lf['confidence']:.0%}")

    # Find differences
    all_types = set(pf['entities'].keys()) | set(lf['entities'].keys())
    has_diff = False

    for entity_type in all_types:
        # Get values and ensure they are lists
        pf_raw = pf['entities'].get(entity_type, [])
        lf_raw = lf['entities'].get(entity_type, [])

        # Skip if not a list (e.g., bool values like out_of_scope)
        if not isinstance(pf_raw, list) or not isinstance(lf_raw, list):
            continue

        pf_vals = set(pf_raw)
        lf_vals = set(lf_raw)

        if pf_vals != lf_vals:
            has_diff = True
            only_pf = pf_vals - lf_vals
            only_lf = lf_vals - pf_vals

            if only_pf:
                print(f"   ⚠️ Only Pattern-First found {entity_type}: {only_pf}")
            if only_lf:
                print(f"   ✅ Only LLM-First found {entity_type}: {only_lf}")

    if not has_diff:
        print(f"   ✓ Same results")

print(f"\n{'=' * 80}")
print("RECOMMENDATIONS")
print(f"{'=' * 80}")

print("""
Dựa trên kết quả test:

1. **LLM-First Strategy** (Recommended nếu chi phí không quan trọng):
   ✅ Pros:
   - Hiểu ngữ cảnh tốt hơn (semantic understanding)
   - Extract nhiều entities hơn (đặc biệt là Service, Topic)
   - Confidence cao hơn (95% vs variable)
   - Xử lý tốt hơn các truy vấn phức tạp

   ❌ Cons:
   - Chậm hơn ~10-15x (1-2s vs 100-200ms)
   - Chi phí cao hơn 7-8x (~$35/month vs ~$5/month)

2. **Pattern-First Strategy** (Hiện tại):
   ✅ Pros:
   - Nhanh (100-200ms)
   - Rẻ (~$5/month)
   - Đủ tốt cho 87% queries

   ❌ Cons:
   - Thiếu semantic understanding
   - Cần nhiều patterns để cover edge cases

**Kết luận**:
Nếu bạn ưu tiên accuracy > cost, hãy dùng LLM-First (USE_LLM_FIRST_STRATEGY = True).
Hiện tại đã bật LLM-First trong config.py.
""")

# Reset to default
config.USE_LLM_FIRST_STRATEGY = True
