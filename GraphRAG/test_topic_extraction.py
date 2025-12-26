# -*- coding: utf-8 -*-
"""
Test topic extraction to debug why specific patterns don't match
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Simulate the _extract_topic_from_text logic
text = "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?"
text_lower = text.lower()

print("=" * 80)
print("TOPIC EXTRACTION DEBUG")
print("=" * 80)

print(f"\nOriginal: {text}")
print(f"Lowercased: {text_lower}")
print(f"Length: {len(text_lower)}")

# Test specific patterns
patterns = [
    ("hủy nạp tiền tự động", ["hủy dịch vụ nạp tiền tự động", "hủy nạp tiền tự động"]),
    ("nạp tiền", ["nạp tiền", "nạp", "deposit", "top-up"]),
]

print("\n" + "=" * 80)
print("PATTERN MATCHING TEST")
print("=" * 80)

for topic_name, keywords in patterns:
    print(f"\nTopic: {topic_name}")
    for keyword in keywords:
        match = keyword in text_lower
        print(f"  Pattern: '{keyword}'")
        print(f"  Match: {match}")
        if match:
            print(f"  ✅ WOULD EXTRACT: {topic_name}")
            break

# Show character-by-character comparison
print("\n" + "=" * 80)
print("CHARACTER ANALYSIS")
print("=" * 80)

keyword = "hủy dịch vụ nạp tiền tự động"
print(f"\nSearching for: '{keyword}'")
print(f"In text: '{text_lower}'")

# Check if substring exists
if keyword in text_lower:
    print("✅ MATCH FOUND!")
    idx = text_lower.index(keyword)
    print(f"Position: {idx}")
else:
    print("❌ NO MATCH")

    # Try to find where it differs
    print("\nLooking for partial matches:")
    parts = ["hủy", "dịch vụ", "nạp tiền", "tự động"]
    for part in parts:
        if part in text_lower:
            print(f"  ✅ Found: '{part}'")
        else:
            print(f"  ❌ Missing: '{part}'")
