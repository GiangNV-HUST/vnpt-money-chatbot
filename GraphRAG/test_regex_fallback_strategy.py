# -*- coding: utf-8 -*-
"""
Test Regex Fallback Strategy:
LLM extract chính → Neo4j query → Nếu empty → Bổ sung regex entities → Retry Neo4j
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
import config

print("=" * 80)
print("REGEX FALLBACK STRATEGY TEST")
print("=" * 80)

print("""
CHIẾN LƯỢC:
1. LLM extract entities (PRIMARY)
2. Giả lập Neo4j query với LLM entities
3. Nếu không tìm thấy kết quả → Bổ sung regex entities
4. Retry với entities đầy đủ hơn

Mục tiêu: LLM làm chính, regex chỉ bổ sung khi cần
""")

extractor = EnhancedEntityExtractor()

# Test cases - những câu LLM có thể infer quá mức hoặc miss literal patterns
test_cases = [
    {
        "query": "Chuyển tiền từ Vietinbank sang VNPT Money cần điều kiện gì?",
        "description": "LLM có thể infer Service nhưng miss Bank pattern"
    },
    {
        "query": "Nhập số tiền cần chuyển",
        "description": "LLM có thể miss Action pattern 'Nhập số tiền'"
    },
    {
        "query": "Bấm nút Xác nhận để hoàn tất",
        "description": "LLM có thể miss UIElement pattern 'Xác nhận'"
    },
    {
        "query": "Làm sao thanh toán hóa đơn điện qua app?",
        "description": "LLM infer Service, có thể miss literal Topic"
    },
]

print("\n" + "=" * 80)
print("TEST CASES")
print("=" * 80)

for i, test_case in enumerate(test_cases, 1):
    query = test_case["query"]
    description = test_case["description"]

    print(f"\n{'=' * 80}")
    print(f"TEST {i}: {query}")
    print(f"Scenario: {description}")
    print(f"{'=' * 80}")

    # Step 1: LLM-First extraction (current setting)
    print("\n🎯 STEP 1: LLM-First Extraction (PRIMARY)")
    print("-" * 80)

    config.USE_LLM_FIRST_STRATEGY = True
    config.ENABLE_LLM_FALLBACK = True

    llm_entities, llm_conf = extractor.extract_with_confidence(query)

    print(f"Confidence: {llm_conf:.0%}")
    print("LLM Entities:")
    llm_entity_count = 0
    for entity_type, values in llm_entities.items():
        if values and isinstance(values, list):
            llm_entity_count += len(values)
            print(f"  {entity_type}: {values}")

    # Step 2: Simulate Neo4j query (assume no results)
    print(f"\n🔍 STEP 2: Simulate Neo4j Query")
    print("-" * 80)
    print("Assume: Neo4j returns 0 results with LLM entities ❌")

    # Step 3: Regex fallback
    print(f"\n🔄 STEP 3: Regex Fallback (SUPPLEMENT)")
    print("-" * 80)

    # Extract pure regex entities
    config.USE_LLM_FIRST_STRATEGY = False
    config.ENABLE_LLM_FALLBACK = False

    regex_entities, regex_conf = extractor.extract_with_confidence(query)

    print(f"Confidence: {regex_conf:.0%}")
    print("Pure Regex Entities:")
    regex_entity_count = 0
    for entity_type, values in regex_entities.items():
        if values and isinstance(values, list):
            regex_entity_count += len(values)
            print(f"  {entity_type}: {values}")

    # Step 4: Merge (LLM + Regex supplement)
    print(f"\n✅ STEP 4: Augmented Entities (LLM + Regex supplement)")
    print("-" * 80)

    augmented = llm_entities.copy()
    added_entities = []

    for entity_type, regex_values in regex_entities.items():
        if not regex_values or not isinstance(regex_values, list):
            continue

        llm_values = llm_entities.get(entity_type, [])

        for regex_val in regex_values:
            # Check if exists
            exists = any(
                regex_val.lower() in llm_val.lower() or
                llm_val.lower() in regex_val.lower()
                for llm_val in llm_values
                if isinstance(llm_val, str)
            )

            if not exists:
                if entity_type not in augmented:
                    augmented[entity_type] = []
                if regex_val not in augmented[entity_type]:
                    augmented[entity_type].append(regex_val)
                    added_entities.append(f"{entity_type}={regex_val}")

    # Show augmented results
    augmented_count = 0
    for entity_type, values in augmented.items():
        if values and isinstance(values, list):
            augmented_count += len(values)

    print("Augmented Entities:")
    for entity_type, values in augmented.items():
        if values and isinstance(values, list):
            print(f"  {entity_type}: {values}")

    print(f"\n📊 Summary:")
    print(f"  LLM entities:       {llm_entity_count}")
    print(f"  Regex entities:     {regex_entity_count}")
    print(f"  Augmented total:    {augmented_count}")
    print(f"  Added from regex:   {len(added_entities)}")

    if added_entities:
        print(f"\n  ➕ Entities added by regex:")
        for entity in added_entities:
            print(f"     - {entity}")
        print(f"\n  ✅ Regex fallback would help! Retry Neo4j with augmented entities.")
    else:
        print(f"\n  ℹ️ No additional entities from regex. LLM coverage was complete.")

# Restore settings
config.USE_LLM_FIRST_STRATEGY = True
config.ENABLE_LLM_FALLBACK = True

print("\n" + "=" * 80)
print("OVERALL CONCLUSION")
print("=" * 80)

print("""
Chiến lược Regex Fallback hoạt động như sau:

1. **LLM Extract (PRIMARY)**:
   - Luôn chạy đầu tiên
   - Semantic understanding tốt
   - Confidence cao (95%)
   - Có thể infer entities từ context

2. **Neo4j Query với LLM entities**:
   - Thử tìm kết quả với entities từ LLM
   - Nếu tìm thấy → Hoàn thành ✅

3. **Regex Fallback (SUPPLEMENT)**:
   - Chỉ trigger khi Neo4j returns empty
   - Extract pure regex patterns
   - Bổ sung entities mà LLM missed
   - Retry Neo4j với entities augmented

4. **Lợi ích**:
   ✅ LLM làm chính (semantic understanding)
   ✅ Regex bổ sung literal patterns khi cần
   ✅ Best of both worlds
   ✅ Không waste LLM cho mọi retry

**Config**:
- USE_LLM_FIRST_STRATEGY = True (LLM chính)
- USE_REGEX_FALLBACK_ON_EMPTY_RESULTS = True (Regex bổ sung khi cần)
""")
