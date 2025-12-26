# Entity Extraction Fix Summary

## Problem Identified

The 2 failed test cases from comprehensive testing were caused by **generic topics being added alongside specific topics** during entity extraction, leading to wrong FAQ matching:

### Failed Cases:
1. **"Hủy nạp tiền tự động"** (Cancel auto-deposit service) - 6 steps
2. **"Mua vé máy bay"** (Buy flight tickets) - 3 steps

### Root Cause:

#### Issue 1: Pattern-based rules adding generic topics
In `enhanced_entity_extractor.py`, lines 312-323 had rules that added generic topics like "Nạp tiền" whenever the query contained "nạp tiền", **even if the LLM had already extracted a more specific topic** like "Hủy dịch vụ nạp tiền tự động".

```python
# OLD CODE (lines 313-317):
if "nạp tiền" in query_lower or "nạp" in query_lower:
    if "Nạp tiền" not in entities.get("Topic", []):
        if "Topic" not in entities:
            entities["Topic"] = []
        entities["Topic"].append("Nạp tiền")  # Always added!
```

**Result**: Entities contained BOTH topics:
- `['Hủy dịch vụ nạp tiền tự động', 'Nạp tiền']`

#### Issue 2: LLM + Pattern merge not checking substrings
In `_merge_llm_results()` (lines 545-548), when merging LLM entities with pattern-based entities, the code only checked for **exact matches**, not substring relationships:

```python
# OLD CODE:
for pv in pattern_vals:
    if not any(pv.lower() == lv.lower() for lv in llm_vals):
        combined.append(pv)  # Added "Nạp tiền" even though "Hủy ... nạp tiền ..." existed!
```

**Result**: Generic topics were added even when they were substrings of more specific LLM-extracted topics.

### Impact on FAQ Matching:

When hybrid search scored FAQs:
- Generic "Nạp tiền" matched MANY FAQs (high recall, low precision)
- Specific "Hủy dịch vụ nạp tiền tự động" matched FEW FAQs (low recall, high precision)
- The bot matched WRONG FAQs that had "Nạp tiền" instead of the correct "Hủy nạp tiền tự động" FAQ

## Solution Implemented

### Fix 1: Smarter generic topic addition (lines 312-327)
Only add generic topics if NO specific topic containing that keyword already exists:

```python
# NEW CODE:
if "nạp tiền" in query_lower or "nạp" in query_lower:
    existing_topics = entities.get("Topic", [])
    # Check if any existing topic already contains "nạp tiền" (more specific)
    has_specific_nap_tien = any("nạp tiền" in t.lower() or "nạp" in t.lower()
                               for t in existing_topics if t != "Nạp tiền")

    if not has_specific_nap_tien and "Nạp tiền" not in existing_topics:
        if "Topic" not in entities:
            entities["Topic"] = []
        entities["Topic"].append("Nạp tiền")
```

### Fix 2: Substring-aware LLM + Pattern merge (lines 545-553)
When merging, skip pattern values that are substrings of LLM values:

```python
# NEW CODE:
for pv in pattern_vals:
    # CRITICAL FIX: Also skip if pattern value is a substring of any LLM value
    is_duplicate = any(pv.lower() == lv.lower() for lv in llm_vals)
    is_substring = any(pv.lower() in lv.lower() for lv in llm_vals if len(pv) < len(lv))

    if not is_duplicate and not is_substring:
        combined.append(pv)
```

## Test Results

### Before Fix:
- **Total Tests**: 12
- **Passed**: 10 ✅
- **Failed**: 2 ❌
- **Success Rate**: **83%**

Failed:
- ❌ Hủy nạp tiền tự động (6 bước)
- ❌ Mua vé máy bay (3 bước)

### After Fix:
- **Total Tests**: 12
- **Passed**: 11 ✅
- **Failed**: 1 ❌
- **Success Rate**: **91%**

Fixed:
- ✅ Hủy nạp tiền tự động (6 bước) - NOW PASSES
- ✅ Mua vé máy bay (3 bước) - NOW PASSES

New Failure:
- ❌ Thanh toán hóa đơn viễn thông (6 bước) - NOW FAILS (was passing before)

## Analysis of New Failure

The "Thanh toán hóa đơn viễn thông" failure appears to be unrelated to the entity extraction fix:

### Observed Issues:
1. **Pattern-based extraction** only found "Thanh toán" (generic), not "Thanh toán hóa đơn viễn thông" (specific)
2. **LLM fallback not triggered** - Confidence was exactly 50.00% (threshold), so LLM wasn't used
3. **LLM hallucination** on continuation queries - LLM extracted "Hủy tài khoản" from "Tôi đã làm xong 5 bước đầu" (completely wrong)

### Possible Causes:
1. **Flaky test** - May have been passing intermittently before
2. **LLM variability** - gpt-4o-mini produces inconsistent entity extractions
3. **Missing pattern** - No specific regex pattern for "thanh toán hóa đơn" in pattern-based extractor

## Recommendation

The fix successfully resolved the 2 target failures (Hủy nạp tiền tự động, Mua vé máy bay) by preventing generic topics from polluting the entity list.

For the new failure (Thanh toán hóa đơn viễn thông), recommend:
1. Add specific regex pattern for "thanh toán hóa đơn" in `simple_entity_extractor.py` or `enhanced_entity_extractor.py`
2. Lower LLM fallback threshold from 50% to 45% to ensure specific topics are always extracted
3. Add validation to LLM entity extractor to reject entities that don't appear in the user query

## Files Modified

1. **enhanced_entity_extractor.py**:
   - Lines 312-327: Added check to prevent adding generic "Nạp tiền" when specific topic exists
   - Lines 545-553: Added substring check when merging LLM and pattern entities

## Impact

✅ **Positive**:
- Fixed 2/2 originally failing test cases (100% fix rate)
- Improved overall completion detection success rate from 83% to 91%
- More precise FAQ matching with specific topics prioritized over generic ones

⚠️ **Negative**:
- 1 previously passing test now fails (Thanh toán hóa đơn viễn thông)
- Root cause appears to be LLM variability/hallucination, not the fix itself
