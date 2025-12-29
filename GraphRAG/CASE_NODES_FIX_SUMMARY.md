# Case Nodes - Tổng Hợp Fix & Kế Hoạch Rebuild Neo4j

## 📋 Tóm Tắt Tình Huống

### Vấn Đề Ban Đầu
- Chatbot trả về **CẢ 2 cases** thay vì chỉ 1 case phù hợp khi user hỏi về phương thức cụ thể
- Ví dụ: "nạp tiền **bằng chuyển khoản**" → Trả về cả "Chuyển khoản" + "Liên kết ngân hàng"

### Root Causes Đã Tìm Ra
1. ❌ LLM extract sai Feature entity
2. ❌ Variant FAQs không có Case nodes → fallback trả full answer
3. ❌ Case.description bị truncate tại 200 chars
4. ❌ 29/31 FAQs có Case.name = NULL
5. ❌ Chỉ có Feature-based matching, thiếu Status và Conditional matching

### Kết Quả Test Toàn Diện
- **Tổng test cases:** 20 (từ 10 FAQs đầu tiên)
- **Pass rate:** 55% (11/20)
- **Pattern:** FAQ_0 (100%), FAQs khác chỉ Case 1 pass, Case 2 fail

---

## ✅ Đã Hoàn Thành - Phase 1: Fix Code

### 1. Fix LLM Entity Extraction

**File:** [llm_entity_extractor.py](llm_entity_extractor.py:165-183)

**Changes:**
- Thêm instruction rõ ràng: **LUÔN LUÔN** extract Feature khi có "bằng", "qua", "thông qua"
- Ví dụ cụ thể: "nạp tiền **bằng chuyển khoản**" → Feature: "Chuyển khoản ngân hàng"

**Result:**
```python
# BEFORE
Query: "tôi thực hiện bằng chuyển khoản ngân hàng"
Extracted: {'Feature': ['Liên kết ngân hàng']}  # ❌ WRONG

# AFTER
Query: "tôi thực hiện bằng chuyển khoản ngân hàng"
Extracted: {'Feature': ['Chuyển khoản ngân hàng']}  # ✅ CORRECT
```

---

### 2. Fix Variant FAQs - Fallback Parser

**File:** [neo4j_rag_engine.py](neo4j_rag_engine.py:1216-1344)

**Changes:**
- Thêm fallback khi variant FAQ không có Case nodes
- Parse multi-case answer và chỉ trả về case match với Feature

**New Method:** `_extract_matching_case_from_answer()`

**Result:**
```python
# BEFORE
FAQ_132 (variant) có cases: [] → Trả về full answer (cả 2 cases)

# AFTER
FAQ_132 (variant) có cases: [] → Parse answer → Trả về chỉ case "Chuyển khoản"
```

---

### 3. Fix Case Description Truncation

**File:** [auto_create_case_nodes.py](auto_create_case_nodes.py:120)

**Changes:**
```python
# BEFORE (3 locations: lines 116, 140, 165)
'description': section[:200],  # ❌ Truncated

# AFTER
'description': section,  # ✅ Full text
```

**Impact:**
- Case "Nạp tiền từ ngân hàng liên kết" đã có đầy đủ 5 bước (trước bị cắt tại "Bước 4: Màn hì")

---

### 4. Add Proper Case Name Extraction

**File:** [auto_create_case_nodes.py](auto_create_case_nodes.py:114-179)

**New Features:**
- Extract case name từ first sentence
- Remove trailing colon
- Limit tối đa 80 chars
- Handle 3 patterns: method, condition, if-then

**Result:**
```python
# BEFORE
Case.name = NULL  (29/31 FAQs)

# AFTER
Case.name = "Nạp tiền từ ngân hàng liên kết"
Case.name = "Nếu giao dịch không thành công nhưng tài khoản ngân hàng đã bị trừ tiền"
```

---

### 5. Add Keywords & Status Values Fields

**File:** [auto_create_case_nodes.py](auto_create_case_nodes.py:191-253)

**New Methods:**
1. `_extract_case_keywords()` - Extract matching keywords
2. `_detect_case_type_and_status()` - Detect case type and status values

**New Case Node Structure:**
```python
{
    'case_id': 'faq_..._1',
    'name': 'Nạp tiền từ ngân hàng liên kết',  # ✅ NEW: Always populated
    'description': '...',  # ✅ FIXED: Full text (no truncation)
    'case_type': 'method',  # ✅ NEW: Auto-detected
    'keywords': ['liên kết', 'ngân hàng liên kết', 'tài khoản liên kết'],  # ✅ NEW
    'status_values': []  # ✅ NEW: For status-based cases
}
```

**Keyword Categories:**
- **Method:** chuyển khoản, liên kết, qr, ví điện tử, thẻ
- **Status:** thành công, thất bại, đang xử lý
- **Conditional:** đã nhận tiền, chưa nhận tiền

---

## 🔄 Chuẩn Bị Rebuild Neo4j - Phase 2

### FAQs Cần Rebuild

**Total:** 7 original FAQs (118 FAQs trong Neo4j là bao gồm cả variants)

| FAQ ID | Topic | Cases | Type |
|--------|-------|-------|------|
| FAQ_0 | Nạp tiền VNPT Money | 2 | method |
| FAQ_2 | Nạp tiền thất bại nhưng bank đã trừ | 3 | if_then |
| FAQ_8 | Nạp tiền đang xử lý nhưng bank đã trừ | 3 | if_then |
| FAQ_50 | Nạp tiền Mobile Money | 2 | method |
| FAQ_51 | Nạp tiền thất bại (Mobile Money) | 3 | if_then |
| FAQ_72 | Nạp tiền điện thoại thành công nhưng không nhận | 2 | condition |
| FAQ_110 | Thanh toán hóa đơn bị trừ tiền | 1 | if_then |

**Tổng:** ~18 Case nodes sẽ được rebuild với structure mới

---

### Lệnh Rebuild

#### Bước 1: Backup (Khuyến nghị)
```bash
cd GraphRAG
python -c "
from neo4j_connector import Neo4jConnector
import json
conn = Neo4jConnector()
result = conn.execute_query('''
MATCH (faq:FAQ)-[:HAS_CASE]->(c:Case)
RETURN faq.id as faq_id, faq.question as question,
       collect({name: c.name, description: c.description}) as cases
''')
with open('case_nodes_backup.json', 'w', encoding='utf-8') as f:
    json.dump([dict(r) for r in result], f, ensure_ascii=False, indent=2)
conn.close()
print('✅ Backup saved to case_nodes_backup.json')
"
```

#### Bước 2: Execute Rebuild
```bash
cd GraphRAG
python auto_create_case_nodes.py --execute
```

#### Bước 3: Verify
```bash
cd GraphRAG
python -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector

conn = Neo4jConnector()

# Check Case.name NULL count
result = conn.execute_query('MATCH (c:Case) WHERE c.name IS NULL RETURN count(c)')
print(f'Cases with NULL names: {result[0][0]} (should be ~0)')

# Check FAQ_0 Cases
result = conn.execute_query('''
MATCH (faq:FAQ {id: \"FAQ_0\"})-[:HAS_CASE]->(c:Case)
RETURN c.name, length(c.description) as len, size(c.keywords) as kw_count
''')

print('\nFAQ_0 Cases:')
for r in result:
    print(f'  ✅ {r[0]}')
    print(f'     Desc: {r[1]} chars (was 200), Keywords: {r[2]}')

conn.close()
"
```

---

## 🚀 Code Enhancements - Phase 3

Sau khi rebuild Neo4j xong, cần update `neo4j_rag_engine.py` để sử dụng các fields mới.

### Enhancement 1: Status-Based Matching

**Target FAQs:** FAQ_139-143, FAQ_169-173 (status: thành công, thất bại, đang xử lý)

**Add to `_match_specific_case()` method:**

```python
# Status matching
extracted_status = query_entities.get('Status', [])
case_status_values = case.get('status_values', [])

if extracted_status and case_status_values:
    for status in extracted_status:
        if 'thành công' in status.lower() and 'thành công' in case_status_values:
            score += 20
        elif 'thất bại' in status.lower() and 'thất bại' in case_status_values:
            score += 20
        elif 'đang xử lý' in status.lower() and 'đang xử lý' in case_status_values:
            score += 20
```

### Enhancement 2: Conditional Matching

**Target FAQs:** FAQ_2, FAQ_8, FAQ_51 ("đã nhận tiền" vs "chưa nhận tiền")

```python
# Conditional matching
query_lower = user_query.lower()

if 'đã nhận tiền' in query_lower or 'đã nhận được tiền' in query_lower:
    if 'đã nhận tiền' in case.get('status_values', []):
        score += 25

elif 'chưa nhận tiền' in query_lower or 'chưa nhận được tiền' in query_lower:
    if 'chưa nhận tiền' in case.get('status_values', []):
        score += 25
```

### Enhancement 3: Keyword Fallback

```python
# Keyword-based matching (fallback)
if score < 10:
    case_keywords = case.get('keywords', [])
    for keyword in case_keywords:
        if keyword in query_lower:
            score += 5
```

---

## 📊 Kỳ Vọng Sau Khi Hoàn Thành

### Current State (Before Rebuild)
| Metric | Value |
|--------|-------|
| Pass Rate | 55% (11/20) |
| FAQ_0 (method) | ✅ 100% |
| FAQs 139-173 (status) | ❌ 50% (chỉ Case 1) |
| Case.name = NULL | 29/31 FAQs |
| Description truncated | Yes (200 chars) |

### Target State (After Rebuild + Enhancements)
| Metric | Value |
|--------|-------|
| Pass Rate | **90%+** (18/20+) |
| FAQ_0 (method) | ✅ 100% (maintained) |
| FAQs 139-173 (status) | ✅ 90%+ (both cases work) |
| FAQ_2, FAQ_8, FAQ_51 (conditional) | ✅ 90%+ |
| Case.name = NULL | **~0** (all have names) |
| Description truncated | **No** (full text) |

---

## 📝 Files Modified

### Phase 1 - Completed ✅
1. **llm_entity_extractor.py** (lines 165-183)
   - Strengthen Feature extraction prompt

2. **neo4j_rag_engine.py** (lines 1216-1344)
   - Add fallback parser for variant FAQs

3. **auto_create_case_nodes.py** (multiple lines)
   - Remove [:200] truncation
   - Add Case.name extraction
   - Add keywords extraction
   - Add status_values detection
   - Update Neo4j Case creation

4. **fix_truncated_case_descriptions.py**
   - Manual fix for FAQ_0 (temporary solution)

### Phase 2 - Ready to Execute 🔄
5. **Neo4j Database**
   - Run: `python auto_create_case_nodes.py --execute`

### Phase 3 - Pending 🔜
6. **neo4j_rag_engine.py** (enhancements)
   - Add Status matching
   - Add Conditional matching
   - Add Keyword fallback
   - Update fallback parser

---

## ✅ Implementation Checklist

### Phase 1: Data Creation Script ✅
- [x] Remove description truncation
- [x] Add Case.name extraction
- [x] Add keywords field
- [x] Add case_type detection
- [x] Add status_values field
- [x] Dry-run verified

### Phase 2: Neo4j Rebuild 🔄
- [ ] Backup current Case nodes
- [ ] Run rebuild: `python auto_create_case_nodes.py --execute`
- [ ] Verify all Cases have names
- [ ] Verify descriptions complete
- [ ] Check keywords populated

### Phase 3: Code Enhancements 🔜
- [ ] Add Status matching in neo4j_rag_engine.py
- [ ] Add Conditional matching
- [ ] Update fallback parser
- [ ] Add Keyword matching

### Phase 4: Testing 🔜
- [ ] Test FAQ_0 (Feature matching - should still work)
- [ ] Test FAQ_139-143 (Status matching - should improve)
- [ ] Test FAQ_2, FAQ_8, FAQ_51 (Conditional - should work)
- [ ] Run comprehensive test suite
- [ ] Validate 90%+ pass rate

---

## 🎯 Next Action

**Bạn có thể chạy rebuild ngay:**

```bash
cd GraphRAG
python auto_create_case_nodes.py --execute
```

Sau khi rebuild xong, chúng ta sẽ tiếp tục Phase 3 để implement Status và Conditional matching trong code.

---

## 📚 Documentation

- **Comprehensive Analysis:** [CASE_NODES_COMPREHENSIVE_ANALYSIS.md](CASE_NODES_COMPREHENSIVE_ANALYSIS.md)
- **Improvements Summary:** [AUTO_CREATE_CASE_NODES_IMPROVEMENTS.md](AUTO_CREATE_CASE_NODES_IMPROVEMENTS.md)
- **Next Steps Guide:** [NEXT_STEPS_NEO4J_REBUILD.md](NEXT_STEPS_NEO4J_REBUILD.md)
- **Case Matching Test Results:** [CASE_MATCHING_TEST_RESULTS.md](CASE_MATCHING_TEST_RESULTS.md)
- **This Summary:** [CASE_NODES_FIX_SUMMARY.md](CASE_NODES_FIX_SUMMARY.md)

---

## 💡 Key Insights

1. **7 FAQs, not 31:** Only original FAQs cần rebuild, variants tự động inherit
2. **3 Case Types:** method (Feature), status (Status), if_then (Conditional)
3. **Incremental Improvement:** Có thể test từng enhancement một
4. **Backward Compatible:** Feature matching (FAQ_0) vẫn hoạt động 100%
5. **Rich Metadata:** keywords + status_values enable flexible matching

---

**Status:** ✅ Phase 1 Complete, Ready for Phase 2 Rebuild 🚀
