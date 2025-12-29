# Next Steps: Neo4j Rebuild & Code Enhancements

## ✅ Phase 1: COMPLETED - auto_create_case_nodes.py Fixed

### Changes Made:
1. ✅ Removed description[:200] truncation (lines 120, 151, 183)
2. ✅ Added proper Case.name extraction with 80-char limit
3. ✅ Added `_extract_case_keywords()` method (191-224)
4. ✅ Added `_detect_case_type_and_status()` method (226-253)
5. ✅ Updated Neo4j Case creation with new fields: keywords, status_values (298-328)

### Current Status:
- Script ready to rebuild Cases with proper structure
- Dry-run verified: 7 original FAQs will be updated
- New fields: name, description (full), keywords, case_type, status_values

---

## 🔄 Phase 2: Neo4j Rebuild (READY TO EXECUTE)

### Why Only 7 FAQs?

**Current Database:**
- 118 FAQs have Case nodes (original + variant FAQs)
- But `auto_create_case_nodes.py` only processes **original FAQs** from paraphrase_documents.json
- Variant FAQs reference the original FAQ's answer (no separate Case nodes needed)

**7 Original FAQs to be rebuilt:**
1. FAQ_0: Nạp tiền từ ngân hàng (VNPT Money) - 2 cases
2. FAQ_2: Nạp tiền thất bại nhưng bank đã trừ - 3 cases
3. FAQ_8: Nạp tiền đang xử lý nhưng bank đã trừ - 3 cases
4. FAQ_50: Nạp tiền từ ngân hàng (Mobile Money) - 2 cases
5. FAQ_51: Nạp tiền thất bại (Mobile Money) - 3 cases
6. FAQ_72: Nạp tiền điện thoại thành công nhưng không nhận - 2 cases
7. FAQ_110: Thanh toán hóa đơn bị trừ tiền nhưng chưa gạch nợ - 1 case

### Rebuild Steps:

#### Step 1: Backup Current Database (RECOMMENDED)
```bash
# Export current Case nodes for rollback if needed
cd GraphRAG
python -c "
from neo4j_connector import Neo4jConnector
import json
conn = Neo4jConnector()
result = conn.execute_query('''
MATCH (faq:FAQ)-[:HAS_CASE]->(c:Case)
RETURN faq.id as faq_id, faq.question as question,
       collect({name: c.name, description: c.description, case_type: c.case_type}) as cases
''')
with open('case_nodes_backup.json', 'w', encoding='utf-8') as f:
    json.dump([dict(r) for r in result], f, ensure_ascii=False, indent=2)
conn.close()
print('Backup saved to case_nodes_backup.json')
"
```

#### Step 2: Execute Rebuild
```bash
cd GraphRAG
python auto_create_case_nodes.py --execute
```

**Expected Output:**
- ✅ 7 FAQs processed
- ✅ ~18 Case nodes created (2+3+3+2+3+2+1 = 16+)
- ✅ All Cases have proper names
- ✅ All descriptions are complete (no truncation)
- ✅ All Cases have keywords and status_values

#### Step 3: Verify Rebuild
```bash
cd GraphRAG
python -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from neo4j_connector import Neo4jConnector

conn = Neo4jConnector()

# Check all Cases have names
result = conn.execute_query('''
MATCH (c:Case)
WHERE c.name IS NULL
RETURN count(c) as null_names
''')
print(f'Cases with NULL names: {result[0][\"null_names\"]}')  # Should be 0 or close to 0

# Check description lengths
result = conn.execute_query('''
MATCH (faq:FAQ {id: \"FAQ_0\"})-[:HAS_CASE]->(c:Case)
RETURN c.name as name, length(c.description) as desc_len,
       size(c.keywords) as keyword_count,
       size(c.status_values) as status_count
''')

print('\nFAQ_0 Cases (Should show full descriptions):')
for r in result:
    print(f'  {r[\"name\"]}')
    print(f'    Description length: {r[\"desc_len\"]} chars (was 200)')
    print(f'    Keywords: {r[\"keyword_count\"]}')
    print(f'    Status values: {r[\"status_count\"]}')

conn.close()
"
```

---

## 🔜 Phase 3: Code Enhancements (NEXT)

After Neo4j rebuild is successful, update `neo4j_rag_engine.py` to use the new Case fields.

### Enhancement 1: Status-Based Matching

**File:** [neo4j_rag_engine.py](neo4j_rag_engine.py)

**Location:** Lines ~1130-1180 (in `_match_specific_case()` method)

**Add after Feature matching:**

```python
# Status-based matching (NEW)
extracted_status = query_entities.get('Status', [])
case_status_values = case.get('status_values', [])

if extracted_status and case_status_values:
    for status in extracted_status:
        status_lower = status.lower()

        # Match "thành công"
        if 'thành công' in status_lower:
            if 'thành công' in case_status_values:
                score += 20
                logger.info(f"  ✅ Status match 'thành công': {case_name}")

        # Match "thất bại" or "không thành công"
        elif any(word in status_lower for word in ['thất bại', 'không thành công', 'lỗi']):
            if 'thất bại' in case_status_values:
                score += 20
                logger.info(f"  ✅ Status match 'thất bại': {case_name}")

        # Match "đang xử lý"
        elif 'đang xử lý' in status_lower:
            if 'đang xử lý' in case_status_values:
                score += 20
                logger.info(f"  ✅ Status match 'đang xử lý': {case_name}")
```

### Enhancement 2: Conditional Matching (đã nhận / chưa nhận tiền)

**Add after Status matching:**

```python
# Conditional matching (NEW)
query_lower = user_query.lower()

# Match "đã nhận được tiền" vs "chưa nhận được tiền"
if 'đã nhận được tiền' in query_lower or 'đã nhận tiền' in query_lower:
    if 'đã nhận tiền' in case_status_values:
        score += 25
        logger.info(f"  ✅ Condition match 'đã nhận tiền': {case_name}")

elif 'chưa nhận được tiền' in query_lower or 'chưa nhận tiền' in query_lower:
    if 'chưa nhận tiền' in case_status_values:
        score += 25
        logger.info(f"  ✅ Condition match 'chưa nhận tiền': {case_name}")
```

### Enhancement 3: Keyword-Based Matching

**Add as fallback:**

```python
# Keyword-based matching (NEW - fallback when no entity match)
if score < 10:  # No strong match yet
    case_keywords = case.get('keywords', [])

    for keyword in case_keywords:
        if keyword in query_lower:
            score += 5
            logger.info(f"  ⚡ Keyword match '{keyword}': {case_name}")
```

### Enhancement 4: Update Fallback Parser

**File:** [neo4j_rag_engine.py](neo4j_rag_engine.py)

**Location:** `_extract_matching_case_from_answer()` method (lines ~1261-1344)

**Add status/conditional matching:**

```python
# Add after Feature matching block (around line 1330)

# Match status-based cases
if extracted_status := query_entities.get('Status', []):
    for status in extracted_status:
        status_lower = status.lower()

        for case_name, case_content in cases:
            case_lower = case_content.lower()

            if 'thành công' in status_lower and 'thành công' in case_lower:
                if 'không thành công' not in case_lower:
                    logger.info(f"  📌 Matched case by status 'thành công': {case_name[:50]}...")
                    return case_content

            elif 'thất bại' in status_lower and 'thất bại' in case_lower:
                logger.info(f"  📌 Matched case by status 'thất bại': {case_name[:50]}...")
                return case_content

# Match conditional cases (đã nhận / chưa nhận tiền)
if 'đã nhận được tiền' in query_lower or 'đã nhận tiền' in query_lower:
    for case_name, case_content in cases:
        if 'đã nhận được tiền' in case_content.lower():
            logger.info(f"  📌 Matched case by condition 'đã nhận tiền': {case_name[:50]}...")
            return case_content

elif 'chưa nhận được tiền' in query_lower or 'chưa nhận tiền' in query_lower:
    for case_name, case_content in cases:
        if 'chưa nhận được tiền' in case_content.lower():
            logger.info(f"  📌 Matched case by condition 'chưa nhận tiền': {case_name[:50]}...")
            return case_content
```

---

## 🧪 Phase 4: Testing & Validation

### Test 1: Feature-Based Matching (Should Still Work)
```bash
cd GraphRAG
python test_all_case_nodes.py --faq FAQ_0
```

**Expected:**
- ✅ Query "bằng chuyển khoản" → Returns "Nạp bằng Chuyển khoản ngân hàng"
- ✅ Query "bằng liên kết" → Returns "Nạp tiền từ ngân hàng liên kết"
- ✅ 100% pass rate maintained

### Test 2: Status-Based Matching (NEW)
```bash
cd GraphRAG
python test_all_case_nodes.py --faq FAQ_139 --faq FAQ_140
```

**Expected:**
- ✅ Both cases now match (not just first case)
- ✅ Pass rate improves from 50% → 90%+

### Test 3: Conditional Matching (NEW)
```bash
cd GraphRAG
python test_all_case_nodes.py --faq FAQ_2
```

**Expected:**
- ✅ Query "đã nhận được tiền" → Returns case about "số tiền sẽ được cộng vào số dư"
- ✅ Query "chưa nhận được tiền" → Returns case about "số tiền sẽ được tra soát và hoàn"

### Test 4: Comprehensive Test
```bash
cd GraphRAG
python test_all_case_nodes.py
```

**Expected:**
- ✅ Overall pass rate: 90%+ (was 55%)
- ✅ All Case types work: method, status, if_then

---

## 📊 Success Metrics

### Before Rebuild:
- ❌ Case.name = NULL for 29/31 original FAQs
- ❌ Case.description truncated at 200 chars
- ❌ No keywords or status_values
- ❌ Only Feature-based matching works
- ❌ Pass rate: 55% (11/20)

### After Rebuild + Code Enhancements:
- ✅ All Cases have proper names
- ✅ Complete descriptions (full text)
- ✅ Rich metadata (keywords, status_values)
- ✅ Method, Status, and Conditional matching
- ✅ Target pass rate: 90%+ (18/20+)

---

## 🚀 Execution Checklist

### Ready to Execute:
- [x] auto_create_case_nodes.py fixed and tested (dry-run successful)
- [ ] Backup current Neo4j Case nodes (recommended)
- [ ] Run rebuild: `python auto_create_case_nodes.py --execute`
- [ ] Verify rebuild with queries
- [ ] Update neo4j_rag_engine.py with Status matching
- [ ] Update neo4j_rag_engine.py with Conditional matching
- [ ] Update fallback parser
- [ ] Run comprehensive tests
- [ ] Validate 90%+ pass rate
- [ ] Update documentation

---

## 📝 Notes

1. **Variants are OK**: Variant FAQs don't need separate Case nodes - they reference the original FAQ's answer
2. **7 FAQs is correct**: Only original FAQs need Case nodes (not 118)
3. **Backward compatible**: Feature-based matching (FAQ_0) will continue to work
4. **Incremental improvement**: Can rebuild and test one enhancement at a time

---

## 🎯 Expected Timeline

- **Phase 2 (Rebuild)**: 10-15 minutes
- **Phase 3 (Code Enhancement)**: 1-2 hours
- **Phase 4 (Testing)**: 30-60 minutes
- **Total**: 2-3 hours to completion

Ready to proceed with Phase 2: Neo4j Rebuild! 🚀
