# LangChain Memory Integration Guide

## Tổng quan

Hệ thống GraphRAG Chatbot đã được tích hợp với **LangChain Memory** để quản lý lịch sử hội thoại một cách thông minh, tự động tóm tắt khi cuộc hội thoại quá dài.

## Cách hoạt động

### 1. **ConversationSummaryBufferMemory** (Khuyến nghị - Đang sử dụng)

Đây là chế độ **hybrid** kết hợp giữa:
- **Summary**: Tóm tắt các tin nhắn cũ để tiết kiệm token
- **Buffer**: Giữ nguyên các tin nhắn gần đây để bảo toàn chi tiết

**Cơ chế**:
1. Khi số token vượt quá `MEMORY_MAX_TOKEN_LIMIT` (mặc định: 2000)
2. Hệ thống tự động gọi LLM để tóm tắt các tin nhắn cũ (trừ 4 tin nhắn gần nhất)
3. Giữ lại summary + tin nhắn gần đây
4. Tiết kiệm token nhưng vẫn giữ được ngữ cảnh quan trọng

### 2. **Buffer Mode** (Tùy chọn)

Lưu toàn bộ tin nhắn gốc, không tóm tắt.

**Ưu điểm**:
- Giữ nguyên 100% thông tin chi tiết
- Không cần gọi LLM để tóm tắt

**Nhược điểm**:
- Tốn nhiều token khi hội thoại dài
- Có giới hạn độ dài (context window limit)

**Phù hợp**: Hội thoại ngắn (< 10 lượt)

### 3. **Summary Only Mode** (Tùy chọn)

Chỉ lưu tóm tắt, không giữ tin nhắn gốc.

**Ưu điểm**:
- Tiết kiệm token tối đa
- Không giới hạn độ dài hội thoại

**Nhược điểm**:
- Mất chi tiết cụ thể
- Mỗi lần cập nhật phải gọi LLM (chi phí + độ trễ)

**Phù hợp**: Hội thoại rất dài, chỉ cần ngữ cảnh chung

## Cấu hình

### File `config.py`

```python
# Conversation Memory Configuration (LangChain)
ENABLE_LANGCHAIN_MEMORY = True  # Bật/tắt LangChain Memory
MEMORY_TYPE = "summary_buffer"  # Options: "buffer", "summary", "summary_buffer"
MEMORY_MAX_TOKEN_LIMIT = 2000   # Max tokens trước khi tóm tắt
MEMORY_RETURN_MESSAGES = True   # Return as message objects
MEMORY_AI_PREFIX = "VNPT Assistant"
MEMORY_HUMAN_PREFIX = "Khách hàng"
```

### Thay đổi chế độ Memory

**Để sử dụng Buffer Mode** (giữ toàn bộ tin nhắn):
```python
MEMORY_TYPE = "buffer"
```

**Để sử dụng Summary Only**:
```python
MEMORY_TYPE = "summary"
```

**Để sử dụng Summary Buffer** (khuyến nghị):
```python
MEMORY_TYPE = "summary_buffer"
MEMORY_MAX_TOKEN_LIMIT = 2000  # Điều chỉnh để kiểm soát khi nào tóm tắt
```

## Sử dụng trong Code

### Khởi tạo

```python
from conversation_context_manager import ConversationContextManager

# Sử dụng cấu hình từ config.py
manager = ConversationContextManager(max_history=10)

# Hoặc override cấu hình
manager = ConversationContextManager(
    max_history=10,
    enable_langchain_memory=True
)
```

### Thêm cuộc hội thoại

```python
# Thêm một lượt hội thoại
manager.add_turn(
    user_query="Làm sao để rút tiền?",
    bot_response={
        "answer": "Để rút tiền: Bước 1...",
        "related_entities": {...}
    }
)
```

### Lấy lịch sử hội thoại

```python
# Lấy full history (bao gồm summary + tin nhắn gần đây)
history = manager.get_full_conversation_history()
print(history)

# Output:
# === TÓM TẮT CUỘC HỘI THOẠI TRƯỚC ĐÓ ===
# Khách hàng đã hỏi về cách nạp tiền, rút tiền...
#
# === CÁC TIN NHẮN GẦN ĐÂY ===
# 👤 Khách hàng: OTP được gửi qua đâu?
# 🤖 VNPT Assistant: OTP được gửi qua SMS...
```

### Lấy summary

```python
# Chỉ lấy phần tóm tắt
summary = manager.get_memory_summary()
print(summary)
```

### Kiểm tra thông tin Memory

```python
# Lấy thống kê
summary = manager.get_summary()
print(f"LangChain enabled: {summary['langchain_memory_enabled']}")
print(f"Memory type: {summary.get('memory_type')}")
print(f"Number of turns: {summary['num_turns']}")
```

### Xóa lịch sử

```python
# Xóa toàn bộ (bao gồm cả LangChain memory)
manager.clear_context()
```

## Ví dụ thực tế

### Ví dụ 1: Hội thoại ngắn (không trigger summarization)

```python
manager = ConversationContextManager()

# Turn 1
manager.add_turn("Làm sao để rút tiền?", {"answer": "Bước 1: ...", ...})

# Turn 2
manager.add_turn("Sau bước 1 thì sao?", {"answer": "Bước 2: ...", ...})

# Lấy history - vẫn giữ nguyên chi tiết
history = manager.get_full_conversation_history()
# → Trả về 2 turns đầy đủ
```

### Ví dụ 2: Hội thoại dài (trigger summarization)

```python
manager = ConversationContextManager()

# Giả sử có 20 lượt hội thoại dài
for i in range(20):
    manager.add_turn(
        f"Câu hỏi {i}",
        {"answer": f"Câu trả lời dài {i}...", ...}
    )

# Khi vượt quá MEMORY_MAX_TOKEN_LIMIT (2000 tokens)
# → Tự động tóm tắt các tin nhắn cũ

# Lấy summary
summary = manager.get_memory_summary()
# → Trả về tóm tắt các tin nhắn cũ + 4 tin nhắn gần nhất
```

## Test và Demo

Chạy test script để xem LangChain Memory hoạt động:

```bash
cd GraphRAG
python test_langchain_memory.py
```

Test script sẽ demo:
1. **Test 1**: Hội thoại cơ bản (3 turns)
2. **Test 2**: Hội thoại dài (10 turns) - xem summarization
3. **Test 3**: So sánh các chế độ Memory

## Lợi ích

### 1. **Tiết kiệm Token**
- Hội thoại dài không còn tốn quá nhiều token
- Giảm chi phí API calls

### 2. **Không giới hạn độ dài**
- Có thể hội thoại liên tục không lo vượt context limit
- Phù hợp cho chatbot customer service

### 3. **Giữ ngữ cảnh quan trọng**
- Summary buffer giữ lại chi tiết của tin nhắn gần đây
- Vẫn có overview của toàn bộ cuộc hội thoại

### 4. **Tự động hóa**
- Không cần quản lý manual việc cắt bỏ tin nhắn cũ
- LLM tự động tóm tắt thông minh

## Lưu ý

### Yêu cầu
- Cần có `OPENAI_API_KEY` trong file `.env`
- Cần cài đặt: `pip install langchain langchain-openai langchain-community`

### Chi phí
- Chế độ `summary_buffer` sẽ gọi LLM để tóm tắt khi cần
- Chi phí phụ thuộc vào:
  - Số lần summarize
  - Model sử dụng (mặc định: gpt-4o-mini - rẻ)
  - Độ dài tin nhắn cần tóm tắt

### Performance
- Summarization tốn thời gian (gọi LLM)
- Nên điều chỉnh `MEMORY_MAX_TOKEN_LIMIT` hợp lý:
  - Quá thấp (< 1000): Tóm tắt quá thường xuyên
  - Quá cao (> 5000): Ít tóm tắt, tốn token

## Troubleshooting

### LangChain không khả dụng
Nếu thấy warning: "LangChain not available"
```bash
pip install langchain langchain-openai langchain-community
```

### Lỗi OpenAI API Key
Đảm bảo có file `.env` với:
```
OPENAI_API_KEY=sk-...
```

### Disable LangChain Memory
Trong `config.py`:
```python
ENABLE_LANGCHAIN_MEMORY = False
```

## Tích hợp với Chatbot

LangChain Memory đã được tích hợp vào [chatbot.py](chatbot.py:27) và hoạt động tự động:

```python
# Trong GraphRAGChatbot.__init__()
self.context_manager = ConversationContextManager(max_history=5)
# → Tự động sử dụng LangChain memory nếu ENABLE_LANGCHAIN_MEMORY=True

# Mỗi lần chat
response = chatbot.chat("Làm sao để rút tiền?")
# → Tự động lưu vào LangChain memory
# → Tự động tóm tắt nếu cần
```

## Kết luận

LangChain Memory giúp chatbot:
- ✅ Quản lý hội thoại dài hiệu quả
- ✅ Tiết kiệm token và chi phí
- ✅ Giữ ngữ cảnh quan trọng
- ✅ Hoạt động tự động, không cần can thiệp

**Khuyến nghị**: Sử dụng chế độ `summary_buffer` với `MEMORY_MAX_TOKEN_LIMIT=2000` cho hầu hết các use case.
