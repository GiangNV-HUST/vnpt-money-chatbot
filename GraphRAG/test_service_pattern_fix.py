# -*- coding: utf-8 -*-
"""
Test Service pattern fix for context-based queries
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
import config

print("=" * 80)
print("TEST SERVICE PATTERN FIX")
print("=" * 80)

extractor = EnhancedEntityExtractor()

# Test case that had gap
test_cases = [
    "Chọn ngân hàng muốn liên kết",  # Original gap query
    "Liên kết ngân hàng Vietcombank",
    "Mở tài khoản VNPT Money",
    "Yêu cầu gì để mở tài khoản?",  # Should infer VNPT Money
]

print("\n" + "=" * 80)
print("PURE REGEX EXTRACTION (should now extract Service)")
print("=" * 80)

# Disable LLM to test pure regex
config.USE_LLM_FIRST_STRATEGY = False
config.ENABLE_LLM_FALLBACK = False

for i, query in enumerate(test_cases, 1):
    print(f"\n{i}. {query}")
    print("-" * 80)

    entities, confidence = extractor.extract_with_confidence(query)

    print(f"Confidence: {confidence:.0%}")

    # Check Service
    service = entities.get("Service", [])
    if service:
        print(f"✅ Service: {service}")
    else:
        print(f"❌ Service: Not found")

    # Show all entities
    print("All entities:")
    for entity_type, values in entities.items():
        if values and isinstance(values, list):
            print(f"  {entity_type}: {values}")

# Restore settings
config.USE_LLM_FIRST_STRATEGY = True
config.ENABLE_LLM_FALLBACK = True

print("\n" + "=" * 80)
print("EXPECTED RESULTS")
print("=" * 80)

print("""
Query 1 & 2: "liên kết ngân hàng"
  ✅ Should extract Service: ['VNPT Money'] (context pattern)

Query 3: "Mở tài khoản VNPT Money"
  ✅ Should extract Service: ['VNPT Money'] (explicit mention)

Query 4: "mở tài khoản" (without "ngân hàng")
  ✅ Should extract Service: ['VNPT Money'] (context pattern)
""")
