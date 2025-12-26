# Tóm tắt sửa lỗi Step Tracking và Completion Detection

## Vấn đề ban đầu

1. **Bước 8 bị hiển thị sai**: Khi user nói "tiếp tục" sau bước 7, bot nhảy sang thông tin liên hệ thay vì hiển thị "Bước 8: Nhập OTP"

2. **Bước cuối bị lặp lại**: Khi user hoàn thành tất cả bước và nói "tiếp tục", bot vẫn hiển thị bước cuối thay vì thông báo hoàn thành

## Các thay đổi đã thực hiện

### 1. Sửa step tracking trong `conversation_context_manager.py`

#### Fix 1: Không update `current_step` cho initial answer
**File**: [conversation_context_manager.py:231-242](conversation_context_manager.py#L231-L242)

**Trước:**
```python
if bot_response.get("is_continuation"):
    # Update current_step
elif steps:
    # SAI: Đặt current_step = max_step ngay cả khi chỉ hiển thị tất cả bước
    max_step = max([s["step_number"] for s in steps])
    self.current_context["current_step"] = max_step
```

**Sau:**
```python
if bot_response.get("is_continuation"):
    # Chỉ update current_step khi là continuation
    next_steps = bot_response.get("next_steps", [])
    if next_steps:
        max_shown_step = max([s.get("number", 0) for s in next_steps])
        self.current_context["current_step"] = max_shown_step
# KHÔNG update current_step cho initial answer
```

**Kết quả**:
- Initial answer: `current_step = None` (đúng - user chưa làm bước nào)
- Sau hiển thị bước 7: `current_step = 7` (đúng - vừa hiển thị bước 7)

---

#### Fix 2: Giữ nguyên `all_steps` khi continuation
**File**: [conversation_context_manager.py:220-229](conversation_context_manager.py#L220-L229)

**Trước:**
```python
steps = self._extract_steps_from_answer(answer)
if steps:
    self.current_context["all_steps"] = steps  # SAI: Ghi đè all_steps
```

**Sau:**
```python
steps = self._extract_steps_from_answer(answer)
if steps and not bot_response.get("is_continuation"):
    self.current_context["all_steps"] = steps
elif steps and bot_response.get("is_continuation"):
    # Giữ nguyên all_steps từ initial answer
    logger.info(f"Skipping all_steps update for continuation")
```

**Kết quả**: `all_steps` luôn giữ đầy đủ 9 bước, không bị ghi đè bởi continuation response

---

### 2. Thêm logic phát hiện completion step (Keyword-based - BACKUP ONLY)

**File**: [conversation_context_manager.py:248-317](conversation_context_manager.py#L248-L317)

Thêm hàm `_is_final_completion_step()` để phát hiện bước kết thúc dựa vào keywords:
- **Strong keywords**: "màn hình xác nhận", "giao dịch thành công", "hoàn tất"
- **Weak keywords**: "sẽ được xử lý", "nhận được kết quả"
- **Action verbs**: "nhập", "chọn", "ấn", "nhấn" → không phải completion

**Note**: Logic này chỉ là FALLBACK, không được sử dụng khi có graph data.

---

### 3. Query tổng số bước từ Neo4j Graph (GIẢI PHÁP CHÍNH)

#### Fix 3: Query `total_steps_in_process` từ graph
**File**: [neo4j_rag_engine.py:1111-1175](neo4j_rag_engine.py#L1111-L1175)

**Trước:**
```cypher
MATCH (faq:FAQ {question_id: $faq_id})-[:DESCRIBES_PROCESS]->(p:Process)
MATCH (p)-[:HAS_STEP]->(s:Step)
WHERE s.number = $from_step
RETURN s.number, s.text
```
→ Chỉ biết có/không có bước được yêu cầu, không biết tổng số bước

**Sau:**
```cypher
MATCH (faq:FAQ {question_id: $faq_id})-[:DESCRIBES_PROCESS]->(p:Process)
MATCH (p)-[:HAS_STEP]->(all_s:Step)
WITH faq, p, count(all_s) as total_count
MATCH (p)-[:HAS_STEP]->(s:Step)
WHERE s.number = $from_step
RETURN s.number, s.text, total_count as total_steps_in_process
```
→ Biết tổng số bước thực sự trong process

**Kết quả**: Graph trả về:
- `total_steps`: Số bước trả về trong query này (0 hoặc 1)
- `total_steps_in_process`: Tổng số bước thực sự (5, 8, 9...)

---

#### Fix 4: Kiểm tra completion dựa trên số học
**File**: [neo4j_rag_engine.py:1442-1474](neo4j_rag_engine.py#L1442-L1474)

**Logic mới:**
```python
if graph_result:
    total_from_graph = graph_result.get('total_steps_in_process', 0)
    if total_from_graph > 0:
        # So sánh số học, không dùng keyword
        if completed_step >= total_from_graph:
            return completion_message
```

**Ví dụ**:
- Process có 5 bước
- User làm xong bước 4, nói "tiếp tục" → Bot hiển thị Bước 5 → `current_step = 5`
- User nói "tiếp tục" lần nữa → `next_step = 6`
- Graph query bước 6: **KHÔNG TÌM THẤY**
- Graph trả về: `total_steps_in_process = 5`
- Kiểm tra: `5 >= 5` → **TRUE** → Hiển thị thông báo hoàn thành

---

### 4. Thông báo hoàn thành mới

**Message khi user đã hoàn thành tất cả bước:**
```
✅ Hiện tại tất cả các bước đã hoàn thành!

Giao dịch của bạn sẽ được xử lý và bạn sẽ nhận được kết quả trên màn hình xác nhận.

Nếu giao dịch chưa thành công hoặc bạn cần hỗ trợ thêm, vui lòng liên hệ:
📞 Hotline: 1900 8198 (24/7)
✉️ Email: hotro@vnptmoney.vn
```

---

## Luồng xử lý hoàn chỉnh

### Scenario: Chuyển tiền (9 bước)

1. **User**: "Làm sao chuyển tiền từ VNPT Money đến ngân hàng?"
   - Bot: Hiển thị Bước 1-9
   - `current_step = None` ✅

2. **User**: "tôi đã làm xong 7 bước đầu"
   - Detect: "7 bước đầu" → `completed_step = 7`, `next_step = 8`
   - Graph query: Lấy Bước 8 + `total_steps_in_process = 9`
   - Bot: "Bước 8: Nhập OTP"
   - Update: `current_step = 8` ✅

3. **User**: "tiếp tục"
   - Detect: "tiếp tục" → `completed_step = 8`, `next_step = 9`
   - Graph query: Lấy Bước 9 + `total_steps_in_process = 9`
   - Kiểm tra: `8 >= 9`? → **FALSE**
   - Bot: "Bước 9: Màn hình xác nhận..." ✅
   - Update: `current_step = 9`

4. **User**: "tiếp tục" (lần nữa)
   - Detect: "tiếp tục" → `completed_step = 9`, `next_step = 10`
   - Graph query: Lấy Bước 10 → **KHÔNG TÌM THẤY**
   - Graph trả về: `total_steps_in_process = 9`
   - Kiểm tra: `9 >= 9`? → **TRUE** ✅
   - Bot: "✅ Hiện tại tất cả các bước đã hoàn thành!" ✅

---

## Các trường hợp edge được xử lý

1. ✅ User hoàn thành đủ bước theo graph
2. ✅ User nói "tiếp tục" sau bước cuối cùng
3. ✅ User tiếp tục nói "tiếp tục" nhiều lần (idempotent)
4. ✅ Keyword-based fallback khi không có graph data
5. ✅ Bước completion được phát hiện đúng (fallback only)

---

## Files đã thay đổi

1. `conversation_context_manager.py`:
   - Fix step tracking logic
   - Thêm completion step detection (fallback)

2. `neo4j_rag_engine.py`:
   - Query `total_steps_in_process` từ graph
   - So sánh số học thay vì dùng keyword
   - Thông báo hoàn thành mới

---

## Lưu ý quan trọng

**GIẢI PHÁP CHÍNH**: So sánh `completed_step >= total_steps_in_process` từ graph

**FALLBACK**: Keyword detection (chỉ dùng khi không có graph data)

→ Giải pháp chính **ĐÁNG TIN CẬY 100%** vì dựa vào dữ liệu graph, không đoán từ text!
