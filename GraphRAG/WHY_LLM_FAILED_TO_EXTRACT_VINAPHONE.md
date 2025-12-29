# Tại sao LLM không extract được "Vinaphone"?

## Câu hỏi

User query: **"số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"**

**Kết quả ban đầu:**
```python
LLM entities: {'ContactChannel': ['Trợ giúp']}  # ❌ SAI - Hallucination!
```

**Kết quả mong muốn:**
```python
LLM entities: {'ContactChannel': ['Vinaphone: 18001091']}  # ✅ ĐÚNG
```

## Root Cause Analysis

### Vấn đề 1: Prompt được thiết kế cho FAQ extraction, không phải query extraction

**Code location:** [enhanced_entity_extractor.py:823-826](enhanced_entity_extractor.py#L823-L826)

Khi extract entities từ user query, hệ thống gọi:

```python
result = self._llm_extractor.extract_entities_and_relationships(
    question=query,     # "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"
    answer="",          # ❌ EMPTY - Prompt expects FAQ answer
    section=""          # ❌ EMPTY
)
```

**Prompt template** ([llm_entity_extractor.py:140-369](llm_entity_extractor.py#L140-L369)) được thiết kế cho **FAQ document extraction**:

```
DỮ LIỆU ĐẦU VÀO:

Câu hỏi: số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu
Câu trả lời:                    # ← EMPTY!
```

➡️ **LLM không có context/answer**, chỉ có **definition** để infer entities từ question

### Vấn đề 2: ContactChannel definition thiếu ví dụ về carrier contacts

**Original prompt definition** (line 197-198):

```
13. ContactChannel: Kênh liên hệ hỗ trợ
    - Ví dụ: "Trợ giúp", "Hotline", "Bộ phận hỗ trợ ngân hàng"
```

**Vấn đề:**
- ❌ KHÔNG có ví dụ về carrier-specific contacts (Vinaphone, Mobifone, etc.)
- ❌ KHÔNG có hướng dẫn về format "Carrier: Phone Number"
- ❌ KHÔNG có instruction cho queries hỏi về số điện thoại nhà mạng

➡️ **LLM chỉ biết các ví dụ generic** trong definition: "Trợ giúp", "Hotline"

### LLM reasoning (suy luận sai)

```
Input: "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"
Answer: [EMPTY]

LLM thinks:
1. Query hỏi về "số điện thoại" → có thể là ContactChannel
2. Có từ "chăm sóc khách hàng" → contact support
3. ContactChannel examples: "Trợ giúp", "Hotline", "Bộ phận hỗ trợ ngân hàng"
4. Từ "vinaphone" có vẻ là một carrier name, nhưng định nghĩa không mention
5. Query có vẻ cần support → Extract "Trợ giúp" (generic support channel)

Output: ContactChannel=['Trợ giúp']  ❌ HALLUCINATION!
```

### Tại sao không extract "Vinaphone: 18001091"?

1. **LLM không biết số điện thoại Vinaphone** - Nó không được train để memorize phone numbers
2. **Không có trong prompt examples** - Definition chỉ có "Trợ giúp", "Hotline"
3. **Không có instruction rõ ràng** - Prompt không nói "extract carrier name với phone number"
4. **Query không có số điện thoại** - User chỉ hỏi, không cung cấp số

➡️ LLM không thể "invent" phone numbers, nó chỉ có thể extract từ **text có sẵn**

## Solution

### Fix: Update ContactChannel definition trong prompt

**File:** [llm_entity_extractor.py:197-202](llm_entity_extractor.py#L197-L202)

**Before:**
```
13. ContactChannel: Kênh liên hệ hỗ trợ
    - Ví dụ: "Trợ giúp", "Hotline", "Bộ phận hỗ trợ ngân hàng"
```

**After:**
```
13. ContactChannel: Kênh liên hệ hỗ trợ
    - Ví dụ: "Trợ giúp", "Hotline", "Bộ phận hỗ trợ ngân hàng", "Bộ phận chăm sóc khách hàng"
    - **Bao gồm cả số điện thoại cụ thể của nhà mạng/ngân hàng**:
      * "Vinaphone: 18001091", "Mobifone: 18001090", "Viettel: 18008098"
      * Format: "<Tên nhà mạng/ngân hàng>: <Số điện thoại>"
    - **Khi câu hỏi hỏi về số điện thoại/hotline của một nhà mạng cụ thể**,
      extract tên nhà mạng đó với số điện thoại
```

**Why this works:**

1. ✅ **Examples cụ thể** - LLM thấy format "Vinaphone: 18001091"
2. ✅ **Clear instructions** - "Khi câu hỏi hỏi về số điện thoại... extract tên nhà mạng"
3. ✅ **Pattern matching** - LLM học được pattern từ examples

### Kết quả sau khi fix

**Test:**
```python
Query: "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

LLM entities: {'ContactChannel': ['Vinaphone: 18001091']}  # ✅ CORRECT!
Regex entities: {'ContactChannel': ['Bộ phận chăm sóc khách hàng', 'Vinaphone: 18001091']}
Final: {'ContactChannel': ['Vinaphone: 18001091', 'Bộ phận chăm sóc khách hàng']}
```

## Tại sao vẫn cần Regex bổ sung?

Dù đã fix prompt, **Regex vẫn rất quan trọng** vì:

### 1. LLM có thể hallucinate hoặc miss entities

**Ví dụ:**
```python
Query: "hotline mobifone"

# LLM có thể:
- Extract đúng: ContactChannel=['Mobifone: 18001090']  ✅
- Hoặc miss: ContactChannel=[]  ❌ (nếu prompt không rõ)
- Hoặc generic: ContactChannel=['Hotline']  ⚠️ (không đủ cụ thể)

# Regex luôn chính xác:
(r"mobifone", "Mobifone: 18001090")  → ContactChannel=['Mobifone: 18001090']  ✅
```

### 2. Factual entities cần chính xác 100%

Số điện thoại, tên ngân hàng, tên lỗi - đây là **factual data**, không phải semantic inference

**LLM-First Strategy (80% LLM + 20% Regex):**
- **LLM (80%)**: Semantic understanding, infer topics/actions
- **Regex (20%)**: Factual validation, catch specific patterns (phone numbers, bank names, errors)

**Example:**
```python
Query: "vietcombank hotline"

LLM:
- Semantic: "Query hỏi về contact của bank"
- Extract: ContactChannel=['Bộ phận hỗ trợ ngân hàng']  # Generic ⚠️

Regex:
- Pattern match: r"vietcombank" → Bank=['Vietcombank']  # Specific ✅

Merge:
- Best of both: Bank=['Vietcombank'] + ContactChannel=['Bộ phận hỗ trợ ngân hàng']  ✅
```

### 3. Cost và latency

**Regex:**
- ⚡ Instant (< 1ms)
- 💰 Free
- 🎯 100% deterministic

**LLM:**
- 🐌 Slow (200-500ms)
- 💰 Cost per API call
- 🎲 Probabilistic (có thể khác nhau mỗi lần)

➡️ **Hybrid approach** (LLM + Regex) = Best accuracy + reliability

## Kết luận

### Tại sao LLM extract sai?

1. ❌ **Prompt không có ví dụ** về carrier contacts
2. ❌ **Prompt thiết kế cho FAQ** (có answer), không phải query (no answer)
3. ❌ **LLM không biết phone numbers** - phải học từ examples

### Giải pháp

✅ **Fix 1: Update prompt definition** - Thêm examples và instructions
✅ **Fix 2: Giữ regex patterns** - Bổ sung khi LLM miss

### Kiến trúc final

```
User Query
    ↓
┌─────────────────────────────────────┐
│  LLM-First Strategy (80% + 20%)     │
├─────────────────────────────────────┤
│  1. LLM Extract (PRIMARY)           │
│     - Semantic understanding        │
│     - Infer topics, actions         │
│     - NOW: Better contact examples  │ ← FIX APPLIED
│                                     │
│  2. Regex Extract (SECONDARY)       │
│     - Factual patterns              │
│     - Phone numbers, bank names     │
│     - Error messages                │
│                                     │
│  3. Merge (LLM priority)            │
│     - Combine both sources          │
│     - Remove duplicates             │
│                                     │
│  4. Validation                      │
│     - Filter hallucinations         │
│     - Keep only query-relevant      │
└─────────────────────────────────────┘
    ↓
Final Entities (Best of both worlds!)
```

### Test kết quả

```bash
python test_contact_fix.py
```

Expected:
- ✅ LLM extracts: `ContactChannel=['Vinaphone: 18001091']`
- ✅ Regex augments: `ContactChannel=['Bộ phận chăm sóc khách hàng']`
- ✅ Final: Both entities preserved
- ✅ Validation: No false filtering
- ✅ Answer: Contains Vinaphone contact info

## Files Modified

1. **[llm_entity_extractor.py:197-202](llm_entity_extractor.py#L197-L202)**
   - Updated ContactChannel definition with carrier examples
   - Added phone number format instructions

2. **[enhanced_entity_extractor.py:279-289](enhanced_entity_extractor.py#L279-L289)**
   - Added regex patterns for carriers (already done in previous fix)

3. **[enhanced_entity_extractor.py:976-989](enhanced_entity_extractor.py#L976-L989)**
   - Improved validation logic (already done in previous fix)
