# Kết Quả Test Case Matching

## Tóm Tắt

**Tổng số tests:** 5
**Pass:** 2 (40%)
**Fail:** 3 (60%)

## Chi Tiết Test Cases

### ✅ **PASS - FAQ_0/FAQ_50: Chuyển khoản ngân hàng**

**Query 1:** "Nạp tiền VNPT Money bằng chuyển khoản ngân hàng"
- ✅ Extracted Feature: `['Chuyển khoản ngân hàng']`
- ✅ Selected Case: "Nạp bằng Chuyển khoản ngân hàng"
- ✅ Answer: Chỉ trả về case "Chuyển khoản" (không có cả 2 cases)

**Query 2:** "Nạp tiền Mobile Money bằng chuyển khoản"
- ✅ Extracted Feature: `['Chuyển khoản ngân hàng']`
- ✅ Selected Case: "Nạp bằng Chuyển khoản ngân hàng"
- ✅ Answer: Single case

---

### ❌ **FAIL - FAQ_0/FAQ_50: Tài khoản liên kết**

**Query 3:** "Nạp tiền VNPT Money bằng tài khoản liên kết"
- ❌ **Wrong FAQ selected:** Trả về FAQ về giao dịch thất bại thay vì FAQ_0
- ❌ Answer: "Nếu giao dịch nạp tiền của bạn không thành công nhưng tài khoản..."

**Query 4:** "Nạp tiền Mobile Money qua liên kết ngân hàng"
- ❌ **Wrong FAQ selected:** Trả về FAQ về troubleshooting thay vì FAQ_50
- ❌ Answer: "Nếu giao dịch nạp tiền của bạn không thành công..."

**Root Cause:**
- Semantic search ưu tiên các FAQ troubleshooting có chứa từ "liên kết ngân hàng" trong context lỗi
- FAQ_0/FAQ_50 bị rank thấp hơn

---

### ❌ **FAIL - QR code**

**Query 5:** "Nạp tiền VNPT Money qua QR"
- ❌ **Wrong FAQ selected:** Trả về FAQ về giao dịch thất bại
- ❌ Answer: "Nếu giao dịch nạp tiền của bạn không thành công..."

**Root Cause:**
- Feature "QR" không đủ mạnh để boost FAQ_0/FAQ_50
- Các FAQ khác có điểm semantic cao hơn

---

## Phân Tích

### ✅ **Những gì hoạt động tốt:**

1. **Feature extraction với "bằng chuyển khoản"** - LLM extract chính xác 100%
2. **Case extraction fallback** - Parse multi-case answers thành công
3. **Single case filtering** - Khi match đúng FAQ, chỉ trả về 1 case

### ❌ **Vấn đề còn tồn tại:**

1. **FAQ ranking không tối ưu**
   - Queries về "liên kết" và "QR" select sai FAQ (troubleshooting thay vì HOW-TO)
   - Semantic search ưu tiên các FAQ có nhiều context tương tự

2. **Feature keywords chưa đủ mạnh**
   - "liên kết ngân hàng" và "QR" không boost FAQ_0/FAQ_50 đủ cao
   - Cần tăng trọng số cho Feature matching trong scoring

3. **Intent classification chưa phân biệt rõ**
   - HOW_TO vs TROUBLESHOOTING không được tách biệt trong scoring
   - Queries "làm sao nạp tiền" nên ưu tiên HOW-TO FAQs, không phải ERROR FAQs

---

## Khuyến Nghị

### Fix 1: Tăng Feature matching bonus
```python
# Trong neo4j_rag_engine.py
if 'liên kết' in feature_lower:
    score += 20  # Tăng từ 15 → 20

if 'qr' in feature_lower:
    score += 20  # Tăng từ 15 → 20
```

### Fix 2: Penalty cho troubleshooting FAQs khi query là HOW_TO
```python
# Nếu intent là HOW_TO nhưng FAQ chứa "thất bại", "lỗi", "không thành công"
if query_intent == "HOW_TO":
    if any(word in faq_answer for word in ["thất bại", "lỗi", "không thành công"]):
        relevance_score *= 0.5  # Penalty 50%
```

### Fix 3: Boost cho exact topic + feature match
```python
# Nếu query có cả Topic ("Nạp tiền") VÀ Feature ("liên kết")
# thì ưu tiên FAQ có cả 2
if topic_match and feature_match:
    relevance_score *= 1.5
```

---

## Test Results Summary

| Query Type | Feature Extracted | FAQ Selected | Case Selected | Result |
|-----------|------------------|--------------|---------------|--------|
| "bằng chuyển khoản" | ✅ Chuyển khoản ngân hàng | ✅ FAQ_0 | ✅ Chuyển khoản | ✅ PASS |
| "bằng tài khoản liên kết" | ⚠️ liên kết | ❌ FAQ_error | ❌ N/A | ❌ FAIL |
| "qua QR" | ⚠️ QR | ❌ FAQ_error | ❌ N/A | ❌ FAIL |

**Pass Rate:** 40% (2/5)

---

## Kết Luận

✅ **Case matching mechanism hoạt động tốt** khi FAQ đúng được chọn
❌ **FAQ selection cần cải thiện** để ưu tiên HOW-TO FAQs hơn troubleshooting FAQs

**Priority:** Cải thiện FAQ ranking trước khi tinh chỉnh Case matching
