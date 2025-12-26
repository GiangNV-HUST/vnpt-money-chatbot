# -*- coding: utf-8 -*-
"""
Test to verify the entity extraction fix works
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor

extractor = EnhancedEntityExtractor()

query = "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?"

print("=" * 80)
print("ENTITY EXTRACTION FIX TEST")
print("=" * 80)
print(f"\nQuery: {query}")

entities = extractor.extract(query)

print(f"\nExtracted Topics: {entities.get('Topic', [])}")
print(f"Extracted Actions: {entities.get('Action', [])}")
print(f"Extracted UIElements: {entities.get('UIElement', [])}")

print("\n" + "=" * 80)
if "Nạp tiền" in entities.get("Topic", []) and "Hủy dịch vụ nạp tiền tự động" in entities.get("Topic", []):
    print("❌ STILL BROKEN: Both generic and specific topics extracted")
elif "Hủy dịch vụ nạp tiền tự động" in entities.get("Topic", []):
    print("✅ FIXED: Only specific topic extracted")
else:
    print("⚠️ UNEXPECTED: Neither topic found")
