# -*- coding: utf-8 -*-
"""
Comprehensive test for completion detection across all major process types
Tests multiple processes with different step counts (2-9 steps)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from chatbot import GraphRAGChatbot

def test_process(chatbot, question, completed_steps, total_steps, name):
    """Test a single process completion"""
    print(f"\n{'=' * 80}")
    print(f"TEST: {name} ({total_steps} bước)")
    print(f"{'=' * 80}")

    # Query 1: Initial question
    print(f"\n1. User: {question}")
    print("-" * 80)
    r1 = chatbot.chat(question)
    answer1 = r1 if isinstance(r1, str) else r1.get('answer', str(r1))
    # Count steps in response
    step_count = answer1.count("Bước")
    print(f"Bot trả lời với {step_count} bước")

    # Query 2: Complete N-1 steps
    print(f"\n2. User: Tôi đã làm xong {completed_steps} bước đầu")
    print("-" * 80)
    r2 = chatbot.chat(f"Tôi đã làm xong {completed_steps} bước đầu")

    # Query 3: Continue (should show next step)
    print(f"\n3. User: tiếp tục (should show Bước {completed_steps + 1})")
    print("-" * 80)
    r3 = chatbot.chat("tiếp tục")
    answer3 = r3 if isinstance(r3, str) else r3.get('answer', str(r3))
    if f"bước {completed_steps + 1}" in answer3.lower() or f"bước tiếp theo" in answer3.lower():
        print(f"✅ Showing step {completed_steps + 1}")
    else:
        print(f"⚠️ Expected step {completed_steps + 1}")

    # Query 4: Continue again (should show COMPLETION)
    print(f"\n4. User: tiếp tục (should show COMPLETION)")
    print("-" * 80)
    r4 = chatbot.chat("tiếp tục")
    answer4 = r4 if isinstance(r4, str) else r4.get('answer', str(r4))

    # Check for completion message
    has_completion = (
        ("hotline" in answer4.lower() and "1900" in answer4) or
        "hoàn thành" in answer4.lower() or
        "✅" in answer4
    )

    if has_completion:
        print(f"✅ SUCCESS: Hiển thị completion (có Hotline)")
        return True
    else:
        print(f"❌ FAIL: Không hiển thị completion")
        print(f"   Got: {answer4[:150]}...")
        return False

def main():
    print("=" * 80)
    print("COMPREHENSIVE COMPLETION TEST - TẤT CẢ CÁC LOẠI QUY TRÌNH")
    print("=" * 80)

    # Test cases covering different step counts and process types
    test_cases = [
        # 9 steps - Transfer processes
        {
            "question": "Làm sao chuyển tiền từ VNPT Money đến ngân hàng?",
            "completed_steps": 8,
            "total_steps": 9,
            "name": "Chuyển tiền đến ngân hàng",
            "category": "Transfer (9 bước)"
        },

        # 6 steps - Payment & Deposit processes
        {
            "question": "Làm sao thanh toán hóa đơn viễn thông?",
            "completed_steps": 5,
            "total_steps": 6,
            "name": "Thanh toán hóa đơn viễn thông",
            "category": "Payment (6 bước)"
        },
        {
            "question": "Tôi muốn hủy dịch vụ nạp tiền tự động thì vào mục nào?",
            "completed_steps": 5,
            "total_steps": 6,
            "name": "Hủy nạp tiền tự động",
            "category": "Deposit (6 bước)"
        },

        # 5 steps - Deposit & Withdrawal processes
        {
            "question": "Làm sao nạp tiền từ ngân hàng vào VNPT Money?",
            "completed_steps": 4,
            "total_steps": 5,
            "name": "Nạp tiền từ ngân hàng",
            "category": "Deposit (5 bước)"
        },
        {
            "question": "Làm sao rút tiền từ ví VNPT Pay về ngân hàng?",
            "completed_steps": 4,
            "total_steps": 5,
            "name": "Rút tiền về ngân hàng",
            "category": "Withdrawal (5 bước)"
        },
        {
            "question": "Tôi muốn đăng ký thanh toán hóa đơn VNPT tự động hàng tháng",
            "completed_steps": 4,
            "total_steps": 5,
            "name": "Đăng ký thanh toán tự động",
            "category": "Register (5 bước)"
        },

        # 4 steps - Deposit & Payment processes
        {
            "question": "Hướng dẫn tôi cách nạp tiền điện thoại trên VNPT Money",
            "completed_steps": 3,
            "total_steps": 4,
            "name": "Nạp tiền điện thoại",
            "category": "Deposit (4 bước)"
        },
        {
            "question": "Cách mua mã thẻ điện thoại",
            "completed_steps": 3,
            "total_steps": 4,
            "name": "Mua mã thẻ điện thoại",
            "category": "Payment (4 bước)"
        },

        # 3 steps - Buy Ticket & Withdrawal processes
        {
            "question": "Làm sao mua vé máy bay trên VNPT Money?",
            "completed_steps": 2,
            "total_steps": 3,
            "name": "Mua vé máy bay",
            "category": "Buy Ticket (3 bước)"
        },
        {
            "question": "Tôi có thể mua vé tàu ở đâu?",
            "completed_steps": 2,
            "total_steps": 3,
            "name": "Mua vé tàu",
            "category": "Buy Ticket (3 bước)"
        },
        {
            "question": "Làm sao để kiểm tra đặt chỗ vé máy bay?",
            "completed_steps": 2,
            "total_steps": 3,
            "name": "Kiểm tra đặt chỗ",
            "category": "Payment (3 bước)"
        },

        # 2 steps - History check processes
        {
            "question": "Tôi có thể xem các giao dịch nạp tiền trong tháng như thế nào?",
            "completed_steps": 1,
            "total_steps": 2,
            "name": "Xem lịch sử nạp tiền",
            "category": "Deposit (2 bước)"
        },
    ]

    results = []
    categories = {}

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

        category = test_case["category"]
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0}

        if success:
            categories[category]["passed"] += 1
        else:
            categories[category]["failed"] += 1

        results.append({
            "name": test_case["name"],
            "category": category,
            "success": success
        })

    # Print summary
    print(f"\n\n{'=' * 80}")
    print("SUMMARY BY CATEGORY")
    print(f"{'=' * 80}")

    for category in sorted(categories.keys()):
        stats = categories[category]
        total = stats["passed"] + stats["failed"]
        status = "✅ ALL PASS" if stats["failed"] == 0 else f"⚠️ {stats['failed']}/{total} FAILED"
        print(f"\n{category}:")
        print(f"   Passed: {stats['passed']}/{total}")
        print(f"   Status: {status}")

    print(f"\n{'=' * 80}")
    print("DETAILED RESULTS")
    print(f"{'=' * 80}")

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{i}. {result['name']} ({result['category']}): {status}")

    print(f"\n{'=' * 80}")
    print(f"Total: {passed}/{total} tests passed ({100*passed//total}%)")
    print(f"{'=' * 80}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
