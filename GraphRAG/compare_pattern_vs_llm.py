# -*- coding: utf-8 -*-
"""
So sánh entity extraction giữa Pattern-based và LLM
Kiểm tra xem regex patterns đã đủ coverage chưa
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from enhanced_entity_extractor import EnhancedEntityExtractor
from simple_entity_extractor import SimpleEntityExtractor

print("=" * 80)
print("COMPARISON: Pattern-based vs LLM Entity Extraction")
print("=" * 80)

# Test queries covering different entity types
test_queries = [
    # Topic variations
    ("Thanh toán hóa đơn", "Tôi muốn thanh toán hóa đơn viễn thông qua VNPT Money"),
    ("Thanh toán hóa đơn điện", "Làm sao thanh toán tiền điện trên app?"),
    ("Thanh toán hóa đơn nước", "Tôi muốn thanh toán hóa đơn nước"),
    ("Nạp tiền điện thoại", "Tôi muốn nạp tiền điện thoại"),
    ("Nạp tiền game", "Làm sao nạp tiền vào game?"),
    ("Hủy nạp tiền tự động", "Tôi muốn hủy dịch vụ nạp tiền tự động"),
    ("Hủy thanh toán tự động", "Làm sao hủy thanh toán tự động?"),
    ("Chuyển tiền", "Tôi muốn chuyển tiền đến ngân hàng"),
    ("Rút tiền", "Làm sao rút tiền về ngân hàng?"),
    ("Mua vé máy bay", "Tôi muốn mua vé máy bay"),
    ("Mua vé tàu", "Làm sao mua vé tàu?"),
    ("Đăng ký", "Tôi muốn đăng ký dịch vụ"),
    ("Liên kết ngân hàng", "Làm sao liên kết ngân hàng?"),
    ("Đổi mật khẩu", "Tôi muốn đổi mật khẩu"),
    ("Kiểm tra số dư", "Làm sao kiểm tra số dư?"),
    ("Lịch sử giao dịch", "Tôi muốn xem lịch sử giao dịch"),
]

enhanced_extractor = EnhancedEntityExtractor()
simple_extractor = SimpleEntityExtractor()

results = []

for category, query in test_queries:
    print(f"\n{'=' * 80}")
    print(f"Category: {category}")
    print(f"Query: {query}")
    print(f"{'=' * 80}")

    # Pattern-based only (from SimpleEntityExtractor)
    pattern_entities = simple_extractor.extract(query)

    # Enhanced (with regex patterns)
    enhanced_no_llm = enhanced_extractor.extract(query)  # This uses patterns only

    # Full extraction with LLM
    full_entities, confidence = enhanced_extractor.extract_with_confidence(query)

    print(f"\n1. PATTERN-BASED (Simple):")
    print(f"   Topics: {pattern_entities.get('Topic', [])}")
    print(f"   Actions: {pattern_entities.get('Action', [])}")

    print(f"\n2. ENHANCED PATTERNS (with regex):")
    print(f"   Topics: {enhanced_no_llm.get('Topic', [])}")
    print(f"   Actions: {enhanced_no_llm.get('Action', [])}")

    print(f"\n3. FULL (with LLM fallback):")
    print(f"   Topics: {full_entities.get('Topic', [])}")
    print(f"   Actions: {full_entities.get('Action', [])}")
    print(f"   Confidence: {confidence:.0%}")

    # Analysis
    pattern_topics = set(pattern_entities.get('Topic', []))
    enhanced_topics = set(enhanced_no_llm.get('Topic', []))
    full_topics = set(full_entities.get('Topic', []))

    print(f"\n📊 ANALYSIS:")

    if pattern_topics == full_topics:
        print(f"   ✅ Pattern-based matches LLM perfectly")
        match_status = "PERFECT"
    elif enhanced_topics == full_topics:
        print(f"   ✅ Enhanced patterns match LLM")
        match_status = "GOOD"
    elif full_topics - enhanced_topics:
        missing = full_topics - enhanced_topics
        print(f"   ⚠️ Missing from patterns: {missing}")
        match_status = "PARTIAL"
    elif enhanced_topics and not full_topics:
        print(f"   ⚠️ Patterns found topics but LLM didn't")
        match_status = "PATTERN_BETTER"
    else:
        print(f"   ❌ Pattern coverage incomplete")
        match_status = "POOR"

    results.append({
        "category": category,
        "pattern_topics": pattern_topics,
        "enhanced_topics": enhanced_topics,
        "full_topics": full_topics,
        "confidence": confidence,
        "match_status": match_status
    })

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY - Pattern Coverage Analysis")
print(f"{'=' * 80}")

match_counts = {
    "PERFECT": 0,
    "GOOD": 0,
    "PARTIAL": 0,
    "PATTERN_BETTER": 0,
    "POOR": 0
}

for r in results:
    match_counts[r["match_status"]] += 1

total = len(results)
print(f"\nTotal test cases: {total}")
print(f"\n✅ PERFECT (pattern = LLM): {match_counts['PERFECT']}/{total} ({match_counts['PERFECT']/total*100:.0f}%)")
print(f"✅ GOOD (enhanced = LLM): {match_counts['GOOD']}/{total} ({match_counts['GOOD']/total*100:.0f}%)")
print(f"⚠️ PARTIAL (missing some): {match_counts['PARTIAL']}/{total} ({match_counts['PARTIAL']/total*100:.0f}%)")
print(f"⚠️ PATTERN_BETTER: {match_counts['PATTERN_BETTER']}/{total} ({match_counts['PATTERN_BETTER']/total*100:.0f}%)")
print(f"❌ POOR (incomplete): {match_counts['POOR']}/{total} ({match_counts['POOR']/total*100:.0f}%)")

coverage = (match_counts['PERFECT'] + match_counts['GOOD']) / total * 100
print(f"\n📊 Overall Pattern Coverage: {coverage:.0f}%")

if coverage >= 90:
    print("🎉 EXCELLENT - Pattern coverage is very good!")
elif coverage >= 70:
    print("✅ GOOD - Pattern coverage is acceptable")
elif coverage >= 50:
    print("⚠️ FAIR - Pattern coverage needs improvement")
else:
    print("❌ POOR - Need to add more patterns")

# Identify gaps
print(f"\n{'=' * 80}")
print("GAPS TO FILL - Topics that need regex patterns")
print(f"{'=' * 80}")

gaps = {}
for r in results:
    if r["match_status"] == "PARTIAL":
        missing = r["full_topics"] - r["enhanced_topics"]
        if missing:
            gaps[r["category"]] = list(missing)

if gaps:
    for category, missing_topics in gaps.items():
        print(f"\n❌ {category}:")
        for topic in missing_topics:
            print(f"   Missing pattern for: '{topic}'")
else:
    print("\n✅ No gaps found - all topics are covered!")
