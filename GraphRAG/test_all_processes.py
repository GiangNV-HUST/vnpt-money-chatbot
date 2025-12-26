# -*- coding: utf-8 -*-
"""
Test completion detection với nhiều processes khác nhau
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_process(chatbot, question, completed_steps, total_steps, process_name):
    """
    Test một process cụ thể

    Args:
        question: Câu hỏi ban đầu
        completed_steps: Số bước đã hoàn thành để test
        total_steps: Tổng số bước trong process
        process_name: Tên process (để hiển thị)
    """
    print("\n" + "=" * 80)
    print(f"TEST: {process_name} ({total_steps} bước)")
    print("=" * 80)

    # Query 1: Initial question
    print(f"\n1. User: {question}")
    print("-" * 80)
    r1 = chatbot.chat(question)
    answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))

    # DEBUG: Show which FAQ was matched
    if isinstance(r1, dict) and 'all_results' in r1 and r1['all_results']:
        top_faq = r1['all_results'][0]
        print(f"DEBUG: Matched FAQ ID: {top_faq.get('faq_id', 'N/A')}")
        print(f"DEBUG: FAQ Question: {top_faq.get('question', 'N/A')[:80]}...")

    # Count steps in answer
    import re
    steps_found = len(re.findall(r'Bước\s+\d+:', answer1))
    print(f"Bot trả lời với {steps_found} bước")
    if steps_found > 0:
        print(f"Answer preview: {answer1[:150]}...")

    if steps_found >= total_steps:
        print(f"✅ Hiển thị đủ {total_steps} bước")
    else:
        print(f"⚠️ Chỉ hiển thị {steps_found}/{total_steps} bước")

    # Query 2: Complete n-1 steps
    print(f"\n2. User: Tôi đã làm xong {completed_steps} bước đầu")
    print("-" * 80)
    r2 = chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")
    answer2 = r2 if isinstance(r2, str) else r2.get('answer', str(r2))

    next_step_num = completed_steps + 1
    if f"bước {next_step_num}" in answer2.lower() or f"bước tiếp theo" in answer2.lower():
        print(f"✅ Hiển thị Bước {next_step_num}")
    else:
        print(f"❌ Không hiển thị Bước {next_step_num}")
        print(f"   Got: {answer2[:100]}...")

    # Query 3: Continue (should show last step)
    print(f"\n3. User: tiếp tục (should show Bước {total_steps})")
    print("-" * 80)
    r3 = chatbot.chat("tiếp tục")
    answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))

    if f"bước {total_steps}" in answer3.lower():
        print(f"✅ Hiển thị Bước {total_steps} (bước cuối)")
    else:
        print(f"⚠️ Không rõ bước nào")

    # Query 4: Continue (should show completion)
    print(f"\n4. User: tiếp tục (should show COMPLETION)")
    print("-" * 80)
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    is_completion = False
    if "hotline" in answer4.lower() and "1900" in answer4:
        print(f"✅ SUCCESS: Hiển thị completion (có Hotline)")
        is_completion = True
    elif "hoàn thành" in answer4.lower():
        print(f"✅ SUCCESS: Hiển thị completion (có 'hoàn thành')")
        is_completion = True
    else:
        print(f"❌ FAIL: Không hiển thị completion")
        print(f"   Got: {answer4[:150]}...")

    return is_completion

def main():
    print("=" * 80)
    print("TEST COMPLETION DETECTION - MULTIPLE PROCESSES")
    print("=" * 80)

    test_cases = [
        {
            "question": "Làm sao rút tiền từ ví VNPT Pay về ngân hàng?",
            "completed_steps": 4,
            "total_steps": 5,
            "name": "Rút tiền từ ví VNPT Pay"
        },
        {
            "question": "Làm sao chuyển tiền từ VNPT Money đến ngân hàng?",
            "completed_steps": 8,
            "total_steps": 9,
            "name": "Chuyển tiền đến ngân hàng"
        },
        {
            "question": "Làm sao nạp tiền từ ngân hàng vào VNPT Money?",
            "completed_steps": 4,
            "total_steps": 5,
            "name": "Nạp tiền từ ngân hàng"
        },
        {
            "question": "Làm sao mua vé máy bay trên VNPT Money?",
            "completed_steps": 2,
            "total_steps": 3,
            "name": "Mua vé máy bay"
        },
        {
            "question": "Làm sao thanh toán hóa đơn viễn thông?",
            "completed_steps": 5,
            "total_steps": 6,
            "name": "Thanh toán hóa đơn viễn thông"
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#' * 80}")
        print(f"# TEST CASE {i}/{len(test_cases)}")
        print(f"{'#' * 80}")

        # Create FRESH chatbot instance for each test to avoid context pollution
        chatbot = GraphRAGChatbot()

        success = test_process(
            chatbot,
            test_case["question"],
            test_case["completed_steps"],
            test_case["total_steps"],
            test_case["name"]
        )

        results.append({
            "name": test_case["name"],
            "success": success
        })

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{i}. {result['name']}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ {total - passed} tests failed")

    print("=" * 80)

if __name__ == "__main__":
    main()
