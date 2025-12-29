# Case Nodes trong Neo4j - Hướng dẫn Sử dụng

## 📋 Case Nodes là gì?

**Case nodes** là các node đại diện cho **trường hợp cụ thể/điều kiện** trong một FAQ có nhiều tình huống khác nhau.

### Cấu trúc Graph

```
FAQ Node: "Tôi nạp tiền thất bại nhưng bank đã trừ tiền"
  │
  ├─ HAS_CASE → Case 1: "VNPT Money đã nhận được tiền"
  │               ├─ case_type: "if_then"
  │               ├─ description: "Nếu VNPT Money đã nhận được tiền..."
  │               └─ HAS_STEP → Step 1, Step 2, Step 3...
  │
  └─ HAS_CASE → Case 2: "VNPT Money chưa nhận được tiền"
                  ├─ case_type: "if_then"
                  ├─ description: "Nếu VNPT Money chưa nhận được tiền..."
                  └─ HAS_STEP → Step 1, Step 2...
```

## 🎯 Tác dụng của Case Nodes

### 1. **Trả lời CHÍNH XÁC hơn cho queries có điều kiện**

#### ❌ KHÔNG có Case nodes:

```
User: "Tôi nạp tiền thất bại, bank đã trừ nhưng VNPT Money chưa nhận được"

Bot returns:
"Nếu VNPT Money đã nhận được tiền: Số tiền sẽ được cộng vào số dư...
 Nếu VNPT Money chưa nhận được tiền: Số tiền sẽ được tra soát và hoàn..."

→ User phải TỰ ĐỌC và chọn case phù hợp ⚠️
```

#### ✅ CÓ Case nodes:

```
User: "Tôi nạp tiền thất bại, bank đã trừ nhưng VNPT Money chưa nhận được"

Entity extraction:
  - Status: ['Thất bại']
  - Situation: "VNPT Money chưa nhận được"

Case matching:
  - Match Case 2: condition="VNPT Money chưa nhận được tiền" ✓

Bot returns:
"Số tiền sẽ được tra soát và hoàn về tài khoản ngân hàng của bạn.
 Thời gian hoàn tiền sẽ tùy thuộc vào quy định của ngân hàng."

→ CHỈ trả về steps của case PHÙ HỢP! ✅
```

### 2. **Context-aware conversation flow**

```python
# Case nodes cho phép chatbot hỏi follow-up questions

User: "Tôi nạp tiền thất bại nhưng đã bị trừ tiền"

Bot: "Mình hiểu rồi! Để hỗ trợ bạn chính xác hơn, cho mình hỏi:
      VNPT Money đã nhận được tiền chưa?
      A) Đã nhận được
      B) Chưa nhận được"

User: "B - Chưa nhận được"

Bot: → Match Case 2 based on user selection
     → Return case-specific answer

→ Interactive conversation! ✅
```

### 3. **Structured data cho multi-turn conversation**

Case nodes cung cấp metadata để chatbot có thể:
- Theo dõi user đang ở case nào
- Hỏi thêm thông tin để xác định đúng case
- Lưu context trong conversation history

---

## 🎪 Case Nodes được sử dụng trong trường hợp nào?

### ✅ Case Type 1: **if_then** (Điều kiện nếu-thì)

**Khi nào cần:**
- FAQ có câu trả lời phụ thuộc vào **điều kiện cụ thể**
- Câu trả lời có dạng: "**Nếu** X **thì** làm Y"

**Ví dụ thực tế:**

```json
{
  "question": "Tôi nạp tiền thất bại nhưng ngân hàng đã trừ tiền",
  "cases": [
    {
      "case_type": "if_then",
      "condition": "VNPT Money đã nhận được tiền",
      "consequence": "Số tiền sẽ được cộng vào số dư VNPT Money"
    },
    {
      "case_type": "if_then",
      "condition": "VNPT Money chưa nhận được tiền",
      "consequence": "Số tiền sẽ được tra soát và hoàn về ngân hàng"
    }
  ]
}
```

**Queries phù hợp:**

```python
# Generic query (không chỉ rõ case)
"Tôi nạp tiền thất bại nhưng đã trừ tiền thì sao?"
→ Bot returns: ALL cases hoặc hỏi user chọn

# Specific query (chỉ rõ case)
"Tôi nạp tiền thất bại, bank trừ tiền nhưng VNPT Money chưa nhận được"
→ Bot matches Case 2 → Returns specific answer ✓

# With entity context
"Giao dịch nạp tiền có trạng thái Đang xử lý, bank đã trừ tiền"
→ Match case by Status entity ✓
```

**Code implementation:**

```python
# File: neo4j_rag_engine.py:1086-1095

case_cypher = """
MATCH (f:FAQ {id: $node_id})-[:HAS_CASE]->(case:Case)
WHERE case.case_type = 'if_then'
OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
RETURN case.case_id, case.description,
       case.condition, case.consequence,
       collect(step) as steps
"""
```

### ✅ Case Type 2: **method** (Nhiều phương thức)

**Khi nào cần:**
- FAQ có nhiều cách thực hiện khác nhau
- Câu trả lời có dạng: "Có **X hình thức/cách**..."

**Ví dụ thực tế:**

```json
{
  "question": "Làm thế nào để rút tiền từ VNPT Money?",
  "answer": "Có 2 hình thức rút tiền...",
  "cases": [
    {
      "case_type": "method",
      "method": "Phương thức 1",
      "name": "Rút về ngân hàng liên kết",
      "description": "Rút tiền về tài khoản ngân hàng đã liên kết với VNPT Money",
      "steps": [
        "Bước 1: Chọn 'Rút tiền'",
        "Bước 2: Chọn ngân hàng liên kết",
        "Bước 3: Nhập số tiền cần rút",
        "Bước 4: Xác nhận giao dịch"
      ]
    },
    {
      "case_type": "method",
      "method": "Phương thức 2",
      "name": "Rút qua mã QR",
      "description": "Rút tiền bằng cách quét mã QR tại điểm giao dịch",
      "steps": [
        "Bước 1: Chọn 'Rút tiền QR'",
        "Bước 2: Quét mã QR tại điểm rút tiền",
        "Bước 3: Nhập số tiền",
        "Bước 4: Nhập mã PIN"
      ]
    }
  ]
}
```

**Queries phù hợp:**

```python
# Generic query
"Làm sao để rút tiền?"
→ Bot returns: "Có 2 phương thức: 1) Rút về ngân hàng, 2) Rút qua QR"

# Specific method query
"Làm sao để rút tiền qua ngân hàng liên kết?"
→ Entity: Feature=['liên kết ngân hàng']
→ Match Case 1 (method: "Rút về ngân hàng liên kết") ✓
→ Return: Steps for Method 1 only

# Feature-based query
"Rút tiền bằng QR code"
→ Entity: Feature=['QR code']
→ Match Case 2 (method: "Rút qua mã QR") ✓
```

### ✅ Case Type 3: **condition** (Nhiều trường hợp)

**Khi nào cần:**
- FAQ có nhiều tình huống khác nhau
- Câu trả lời có dạng: "**Trường hợp 1:**..., **Trường hợp 2:**..."

**Ví dụ thực tế:**

```json
{
  "question": "Giao dịch đang xử lý thì làm sao?",
  "cases": [
    {
      "case_type": "condition",
      "name": "Trường hợp 1: Giao dịch dưới 24h",
      "condition": "Giao dịch đang xử lý dưới 24 giờ",
      "actions": [
        "Chờ thêm thời gian vì hệ thống đang xử lý",
        "Kiểm tra lại sau 1-2 giờ"
      ]
    },
    {
      "case_type": "condition",
      "name": "Trường hợp 2: Giao dịch quá 3 ngày",
      "condition": "Giao dịch đang xử lý quá 3 ngày làm việc",
      "actions": [
        "Liên hệ CSKH qua mục Trợ giúp",
        "Yêu cầu tra soát giao dịch"
      ]
    }
  ]
}
```

**Queries phù hợp:**

```python
# Time-based query
"Giao dịch nạp tiền đang xử lý được 5 ngày rồi"
→ Entity: TimeFrame=['5 ngày'], Status=['Đang xử lý']
→ Match Case 2 (condition: "quá 3 ngày") ✓

# Status-based query
"Giao dịch báo đang xử lý từ sáng nay"
→ Entity: TimeFrame=['từ sáng nay'], Status=['Đang xử lý']
→ Match Case 1 (condition: "dưới 24 giờ") ✓
```

---

## 🔧 Hệ thống hiện tại

### Thống kê

```
✅ Số lượng Case nodes: 157
✅ Số lượng HAS_CASE relationships: 157
✅ Case types:
   - if_then: ~120 cases (phổ biến nhất)
   - method: ~25 cases
   - condition: ~12 cases
```

### Ví dụ FAQs có Case nodes

```
1. "Tôi nạp tiền thất bại nhưng ngân hàng đã trừ tiền"
   → 2 cases (if_then)

2. "Tôi chuyển tiền nhầm thì làm sao?"
   → 2 cases (if_then): quen biết vs không quen biết

3. "Giao dịch nạp tiền báo Đang xử lý nhưng đã trừ tiền"
   → 2 cases (if_then): VNPT Money nhận được vs chưa nhận được

4. "Làm sao để rút tiền?"
   → 2 cases (method): Rút về bank vs Rút qua QR

5. "Tài khoản không đủ số dư khi nạp tiền"
   → Multiple cases (condition): Nhiều nguyên nhân khác nhau
```

---

## 🚀 Khi nào Case Nodes được sử dụng?

### Scenario 1: Direct FAQ match với specific case

```python
Query: "Tôi nạp tiền thất bại, bank trừ tiền nhưng VNPT Money chưa nhận được"

Step 1: Extract entities
  - Status: ['Thất bại']
  - Error: ['giao dịch thất bại']
  - Topic: ['Nạp tiền']

Step 2: Find relevant FAQ
  - Match FAQ: "Tôi nạp tiền thất bại nhưng ngân hàng đã trừ tiền"

Step 3: Get cases for this FAQ
  - Case 1: "VNPT Money đã nhận được tiền"
  - Case 2: "VNPT Money chưa nhận được tiền"

Step 4: Match case based on query
  - Query contains "chưa nhận được"
  - → Match Case 2 ✓

Step 5: Return case-specific answer
  - Return: Steps for Case 2 only
```

### Scenario 2: Multi-turn conversation

```python
Turn 1:
User: "Tôi nạp tiền thất bại nhưng đã trừ tiền"
Bot: "Mình hiểu rồi. VNPT Money đã nhận được tiền chưa?"

Turn 2:
User: "Chưa nhận được"
Bot: → Save context: user_case = "Case 2"
     → Return answer for Case 2

Turn 3:
User: "Bao lâu thì được hoàn tiền?"
Bot: → Use context: user đang ở Case 2
     → Return: "Thời gian hoàn tiền tùy thuộc vào quy định của ngân hàng..."
```

### Scenario 3: Feature-based filtering

```python
Query: "Làm sao để rút tiền bằng QR code?"

Entities:
  - Topic: ['Rút tiền']
  - Feature: ['QR code']

FAQ match: "Làm thế nào để rút tiền từ VNPT Money?"

Case filtering by Feature:
  - Case 1: "Rút về ngân hàng liên kết" (Feature: 'liên kết ngân hàng') ❌
  - Case 2: "Rút qua mã QR" (Feature: 'QR code') ✅

Return: Steps for Case 2 (QR method) only
```

---

## 💡 Best Practices

### 1. **Case naming convention**

```python
# Good ✓
case.name = "VNPT Money đã nhận được tiền"
case.name = "Phương thức 1: Rút về ngân hàng"
case.name = "Trường hợp 1: Giao dịch dưới 24h"

# Bad ❌
case.name = "Case 1"
case.name = "A"
case.name = "TH1"
```

### 2. **Case description**

```python
# Good ✓
case.description = "Nếu VNPT Money đã nhận được tiền, số tiền sẽ được cộng..."

# Bad ❌
case.description = "Đã nhận được"
```

### 3. **Entity matching**

```python
# Ensure case conditions can be matched with entities
Case condition: "VNPT Money chưa nhận được tiền"
↓
Extractable entities:
  - Status: ['Chưa nhận được']
  - Account: ['VNPT Money']
↓
Query: "Bank trừ tiền nhưng VNPT Money chưa nhận được"
→ Match! ✓
```

---

## 📊 Current Implementation

### Code locations

1. **Case node creation:**
   - [auto_create_case_nodes.py](auto_create_case_nodes.py) - Auto-detect and create cases
   - [extract_case_nodes.py](extract_case_nodes.py) - Extract from FAQs

2. **Case node retrieval:**
   - [neo4j_rag_engine.py:1086-1095](neo4j_rag_engine.py#L1086-L1095) - Cypher query
   - [neo4j_rag_engine.py:1187-1192](neo4j_rag_engine.py#L1187-L1192) - Case selection

3. **Case matching logic:**
   - Currently: Returns ALL cases, chatbot selects best one
   - Future: Can add entity-based case filtering

### Example Cypher query

```cypher
// Get all cases for a FAQ
MATCH (f:FAQ {id: $node_id})-[:HAS_CASE]->(case:Case)
OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
RETURN
  case.case_id as case_id,
  case.name as case_name,
  case.description as case_description,
  case.case_type as case_type,
  case.method as case_method,
  collect({number: step.number, text: step.text}) as steps
ORDER BY case.case_id
```

---

## 🎯 Kết luận

### Case Nodes có tác dụng trong trường hợp:

1. ✅ **FAQ có nhiều điều kiện if-then**
   - Query: "Nạp tiền thất bại, bank đã trừ nhưng VNPT Money chưa nhận được"
   - → Match case dựa trên condition

2. ✅ **FAQ có nhiều phương thức/cách làm**
   - Query: "Rút tiền bằng QR code"
   - → Match case dựa trên Feature entity

3. ✅ **FAQ có nhiều trường hợp khác nhau**
   - Query: "Giao dịch đang xử lý được 5 ngày rồi"
   - → Match case dựa trên TimeFrame entity

4. ✅ **Multi-turn conversation cần context**
   - Turn 1: "Nạp tiền thất bại đã trừ tiền"
   - Bot: "VNPT Money nhận được chưa?"
   - Turn 2: "Chưa" → Save case context

5. ✅ **Cần trả lời CHÍNH XÁC cho specific situation**
   - Thay vì trả về ALL cases → Chỉ trả về case PHÙ HỢP

### Lợi ích:

- 🎯 **Accuracy**: Trả lời đúng case, không dài dòng
- 💬 **Context**: Hỗ trợ multi-turn conversation
- 🧠 **Intelligence**: Entity-based case matching
- 📊 **Structure**: Dữ liệu có cấu trúc, dễ maintain

### Status hiện tại:

- ✅ **157 Case nodes** đã được tạo trong Neo4j
- ✅ **Code infrastructure** đã sẵn sàng (Cypher queries, retrieval logic)
- ⚠️ **Case matching logic** có thể cải thiện (hiện tại return all cases, có thể add entity-based filtering)
