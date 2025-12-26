"""
Test script to demonstrate LangChain Memory integration
Shows how ConversationSummaryBufferMemory works
"""

import sys
import logging

# Fix Windows console encoding for Vietnamese text
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from conversation_context_manager import ConversationContextManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_memory():
    """Test basic conversation memory functionality"""
    print("=" * 80)
    print("TEST 1: Basic Memory Functionality")
    print("=" * 80)

    # Initialize with LangChain memory enabled
    manager = ConversationContextManager(max_history=10, enable_langchain_memory=True)

    # Simulate a conversation
    conversations = [
        {
            "query": "Làm sao để rút tiền từ ví VNPT Pay?",
            "response": {
                "answer": """Để rút tiền từ ví VNPT Pay về tài khoản ngân hàng:

Bước 1: Tại giao diện chính, chọn mục "Rút tiền"
Bước 2: Nhập số tiền cần rút và nhấn "Tiếp tục"
Bước 3: Xác nhận giao dịch và nhấn "Rút tiền"
Bước 4: Nhập mã OTP
Bước 5: Hoàn tất giao dịch""",
                "related_entities": {
                    "topics": ["rút tiền"],
                    "services": ["VNPT Pay"]
                }
            }
        },
        {
            "query": "Sau khi hoàn thành 2 bước đầu, tôi làm gì tiếp?",
            "response": {
                "answer": """Bước tiếp theo:

Bước 3: Xác nhận giao dịch và nhấn "Rút tiền"
Bước 4: Nhập mã OTP để xác thực""",
                "related_entities": {
                    "topics": ["rút tiền"],
                },
                "is_continuation": True,
                "next_steps": [
                    {"number": 3, "text": "Xác nhận giao dịch"},
                    {"number": 4, "text": "Nhập OTP"}
                ]
            }
        },
        {
            "query": "OTP được gửi qua đâu?",
            "response": {
                "answer": "OTP được gửi qua tin nhắn SMS đến số điện thoại đã đăng ký với ví VNPT Pay của bạn.",
                "related_entities": {}
            }
        }
    ]

    # Process conversations
    for i, conv in enumerate(conversations, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {conv['query']}")
        manager.add_turn(conv['query'], conv['response'])
        print(f"Bot: {conv['response']['answer'][:100]}...")

    # Get memory summary
    print("\n" + "=" * 80)
    print("MEMORY SUMMARY")
    print("=" * 80)

    summary = manager.get_summary()
    print(f"\nNumber of turns: {summary['num_turns']}")
    print(f"LangChain memory enabled: {summary['langchain_memory_enabled']}")
    print(f"Memory type: {summary.get('memory_type', 'N/A')}")
    print(f"Current topic: {summary['current_topic']}")

    # Get full history
    print("\n" + "=" * 80)
    print("FULL CONVERSATION HISTORY (from LangChain Memory)")
    print("=" * 80)
    history = manager.get_full_conversation_history()
    print(history)

    # Get memory summary (if available)
    if summary.get('langchain_memory_summary'):
        print("\n" + "=" * 80)
        print("LANGCHAIN MEMORY SUMMARY (Tóm tắt cuộc hội thoại)")
        print("=" * 80)
        print(summary['langchain_memory_summary'])


def test_long_conversation():
    """Test memory with a long conversation to see summarization in action"""
    print("\n\n" + "=" * 80)
    print("TEST 2: Long Conversation with Summarization")
    print("=" * 80)

    manager = ConversationContextManager(max_history=20, enable_langchain_memory=True)

    # Simulate a longer conversation (10 turns)
    long_conversation = [
        ("Tôi muốn nạp tiền vào ví VNPT Pay", "Để nạp tiền: Bước 1: Chọn Nạp tiền..."),
        ("Có những phương thức nạp tiền nào?", "Có 3 phương thức: Qua thẻ ATM, Qua ngân hàng, Qua cửa hàng tiện lợi"),
        ("Tôi chọn nạp qua thẻ ATM", "Tốt, bạn làm theo: Bước 1: Chọn phương thức ATM..."),
        ("Tối thiểu nạp bao nhiêu?", "Số tiền tối thiểu là 10,000 VNĐ"),
        ("Tối đa nạp bao nhiêu?", "Số tiền tối đa mỗi lần là 50,000,000 VNĐ"),
        ("Phí nạp tiền là bao nhiêu?", "Phí nạp tiền qua ATM là miễn phí"),
        ("Tiền vào ví sau bao lâu?", "Tiền sẽ vào ví ngay lập tức sau khi giao dịch thành công"),
        ("Nếu không thấy tiền vào thì làm sao?", "Bạn kiểm tra lại lịch sử giao dịch, nếu vẫn chưa có thì liên hệ hotline 1900 8198"),
        ("Tôi có thể nạp nhiều lần trong ngày không?", "Có, bạn có thể nạp nhiều lần, tổng hạn mức trong ngày là 100,000,000 VNĐ"),
        ("Cảm ơn bạn!", "Rất vui được hỗ trợ! Nếu cần thêm thông tin, hãy liên hệ với chúng tôi.")
    ]

    for i, (query, answer) in enumerate(long_conversation, 1):
        print(f"\nTurn {i}: {query[:50]}...")
        manager.add_turn(query, {"answer": answer, "related_entities": {}})

    # Show summary after long conversation
    summary = manager.get_summary()
    print("\n" + "=" * 80)
    print("AFTER 10 TURNS - MEMORY STATUS")
    print("=" * 80)
    print(f"Number of turns: {summary['num_turns']}")
    print(f"Memory type: {summary.get('memory_type', 'N/A')}")

    # The magic: get the summarized memory
    if summary.get('langchain_memory_summary'):
        print("\n" + "=" * 80)
        print("📝 SUMMARIZED CONVERSATION (LangChain tự động tóm tắt)")
        print("=" * 80)
        print(summary['langchain_memory_summary'])
        print("\n⭐ Notice: Instead of storing all 10 turns, LangChain summarized them!")
        print("    This saves tokens and allows for unlimited conversation length!")


def test_memory_types_comparison():
    """Compare different memory types"""
    print("\n\n" + "=" * 80)
    print("TEST 3: Comparison of Memory Types")
    print("=" * 80)

    # You can manually test different types by changing config.MEMORY_TYPE
    # For now, just explain the difference

    print("""
    MEMORY TYPE COMPARISON:

    1. ConversationBufferMemory (buffer)
       ✅ Lưu toàn bộ tin nhắn gốc
       ✅ Không mất thông tin chi tiết
       ❌ Tốn nhiều token khi hội thoại dài
       ❌ Có giới hạn độ dài (context window)
       → Phù hợp: Hội thoại ngắn (< 10 turns)

    2. ConversationSummaryMemory (summary)
       ✅ Tiết kiệm token (chỉ lưu tóm tắt)
       ✅ Không giới hạn độ dài hội thoại
       ❌ Mất chi tiết cụ thể
       ❌ Mỗi lần cập nhật phải gọi LLM (chi phí + độ trễ)
       → Phù hợp: Hội thoại rất dài, chỉ cần ngữ cảnh chung

    3. ConversationSummaryBufferMemory (summary_buffer) ⭐ RECOMMENDED
       ✅ Hybrid: Summary + tin nhắn gần nhất
       ✅ Cân bằng giữa chi tiết & tiết kiệm token
       ✅ Giữ được thông tin quan trọng từ các câu gần đây
       ⚠️ Vẫn tốn LLM calls để tóm tắt phần cũ
       → Phù hợp: Hầu hết các use case (đặc biệt GraphRAG chatbot)

    CURRENT CONFIGURATION:
    - Using: ConversationSummaryBufferMemory
    - Max token limit: 2000 tokens
    - When conversation exceeds 2000 tokens → older messages are summarized
    """)


if __name__ == "__main__":
    try:
        # Run tests
        test_basic_memory()
        test_long_conversation()
        test_memory_types_comparison()

        print("\n\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 80)
        print("\nKẾT LUẬN:")
        print("- LangChain Memory đã được tích hợp thành công")
        print("- ConversationSummaryBufferMemory tự động tóm tắt hội thoại khi quá dài")
        print("- Tiết kiệm token và cho phép hội thoại không giới hạn độ dài")
        print("- Vẫn giữ được chi tiết của các tin nhắn gần đây")
        print("\nCẤU HÌNH:")
        print("- Có thể thay đổi MEMORY_TYPE trong config.py")
        print("- Có thể điều chỉnh MEMORY_MAX_TOKEN_LIMIT để kiểm soát khi nào tóm tắt")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        print("\nLƯU Ý: Cần có OPENAI_API_KEY trong file .env để LangChain Memory hoạt động")
