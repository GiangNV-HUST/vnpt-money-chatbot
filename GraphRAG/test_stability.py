# -*- coding: utf-8 -*-
"""
Test stability - chạy cùng test nhiều lần để check consistency
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_case(question, completed_steps):
    """Test a single case - return True if completion detected"""
    chatbot = GraphRAGChatbot()

    # Query 1: Initial
    chatbot.chat(question)

    # Query 2: Complete N-1 steps
    chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")

    # Query 3: Continue
    chatbot.chat("tiếp tục")

    # Query 4: Continue again (should show COMPLETION)
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    # Check for completion
    has_completion = (
        ("hotline" in answer4.lower() and "1900" in answer4) or
        ("hoàn thành" in answer4.lower() and "✅" in answer4)
    )

    return has_completion

print("=" * 80)
print("STABILITY TEST - Running same test 3 times")
print("=" * 80)

# Test 1: Hủy nạp tiền tự động (đã fix)
print("\nTest Case: Hủy nạp tiền tự động (6 bước)")
print("-" * 80)
results_huy = []
for i in range(3):
    print(f"Run {i+1}/3...", end=" ")
    result = test_case("Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?", 5)
    results_huy.append(result)
    print("✅ PASS" if result else "❌ FAIL")

# Test 2: Mua vé máy bay (đã fix)
print("\nTest Case: Mua vé máy bay (3 bước)")
print("-" * 80)
results_mua_ve = []
for i in range(3):
    print(f"Run {i+1}/3...", end=" ")
    result = test_case("Làm sao mua vé máy bay trên VNPT Money?", 2)
    results_mua_ve.append(result)
    print("✅ PASS" if result else "❌ FAIL")

# Test 3: Rút tiền về ngân hàng (occasionally flaky?)
print("\nTest Case: Rút tiền về ngân hàng (5 bước)")
print("-" * 80)
results_rut = []
for i in range(3):
    print(f"Run {i+1}/3...", end=" ")
    result = test_case("Làm sao rút tiền về ngân hàng từ VNPT Money?", 4)
    results_rut.append(result)
    print("✅ PASS" if result else "❌ FAIL")

print("\n" + "=" * 80)
print("STABILITY SUMMARY")
print("=" * 80)

def analyze_stability(name, results):
    passed = sum(results)
    total = len(results)
    rate = passed / total * 100

    if rate == 100:
        status = "✅ STABLE (100%)"
    elif rate >= 66:
        status = "⚠️ MOSTLY STABLE (≥66%)"
    else:
        status = "❌ UNSTABLE (<66%)"

    print(f"{name}: {passed}/{total} ({rate:.0f}%) - {status}")
    return rate

rate1 = analyze_stability("Hủy nạp tiền tự động", results_huy)
rate2 = analyze_stability("Mua vé máy bay", results_mua_ve)
rate3 = analyze_stability("Rút tiền về ngân hàng", results_rut)

avg_stability = (rate1 + rate2 + rate3) / 3
print(f"\nOverall stability: {avg_stability:.0f}%")

if avg_stability >= 90:
    print("🎉 System is HIGHLY STABLE")
elif avg_stability >= 70:
    print("✅ System is REASONABLY STABLE")
else:
    print("⚠️ System stability needs improvement")
