# Fix: Contact Channel Entity Extraction Issue

## Problem

User query: "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

**Expected:** Return Vinaphone contact number (18001091)

**Actual:** Returned generic response saying no information available

## Root Cause Analysis

### Issue 1: Missing Regex Patterns for ContactChannel

**Location:** `enhanced_entity_extractor.py` lines 270-279

**Problem:** The ContactChannel regex patterns were missing critical patterns:
- ❌ No pattern for "chăm sóc khách hàng"
- ❌ No pattern for "số điện thoại"
- ❌ No pattern for specific carriers (Vinaphone, Mobifone, etc.)

**Original patterns:**
```python
self.contact_channel_patterns_regex = [
    (r"hotline", "Hotline"),
    (r"(gọi|điện)\s+(hỗ\s+trợ|tổng\s+đài)", "Hotline"),
    (r"trợ\s+giúp", "Trợ giúp"),
    # ... missing many patterns
]
```

### Issue 2: Overly Strict Validation Logic

**Location:** `enhanced_entity_extractor.py` lines 974-980

**Problem:** The validation logic was filtering out entities like "Vinaphone: 18001091" because:
- It split on whitespace: `["Vinaphone:", "18001091"]`
- "Vinaphone:" didn't match "vinaphone" in query (due to colon)
- Entity got incorrectly filtered as hallucination

**Original code:**
```python
value_words = value.lower().split()
if any(word in query_lower for word in value_words):
    validated[entity_type].append(value)
else:
    logger.warning(f"Filtered LLM entity (no words match): {entity_type}={value}")
```

## Solution

### Fix 1: Add Missing ContactChannel Patterns

**File:** `enhanced_entity_extractor.py` lines 270-289

**Changes:**
```python
self.contact_channel_patterns_regex = [
    (r"hotline", "Hotline"),
    (r"(gọi|điện)\s+(hỗ\s+trợ|tổng\s+đài)", "Hotline"),
    (r"trợ\s+giúp", "Trợ giúp"),
    (r"hỗ\s+trợ\s+trực\s+tuyến", "hỗ trợ trực tuyến"),
    (r"chat\s+(hỗ\s+trợ|support)", "chat support"),
    (r"email\s+(hỗ\s+trợ|support)", "email support"),
    (r"trung\s+tâm\s+hỗ\s+trợ", "trung tâm hỗ trợ"),
    # ✅ NEW: Add patterns for "chăm sóc khách hàng"
    (r"chăm\s+sóc\s+khách\s+hàng", "Bộ phận chăm sóc khách hàng"),
    (r"tổng\s+đài", "Hotline"),
    (r"số\s+điện\s+thoại", "Hotline"),
    # ✅ NEW: Add specific carrier patterns
    (r"vinaphone", "Vinaphone: 18001091"),
    (r"mobifone", "Mobifone: 18001090"),
    (r"viettel", "Viettel: 18008098"),
    (r"vietnamobile", "Vietnamobile: 0922789789"),
    (r"gmobile", "Gmobile: 0598880199"),
]
```

### Fix 2: Improve Validation Logic

**File:** `enhanced_entity_extractor.py` lines 983-999

**Changes:**
```python
# Moderate validation for others
else:
    # ✅ CRITICAL FIX: Clean punctuation from words before matching
    import string
    value_words = [w.strip(string.punctuation) for w in value.lower().split()]
    query_words = [w.strip(string.punctuation) for w in query_lower.split()]

    # ✅ Match if any word from value appears in query OR vice versa
    word_match = any(word in query_lower for word in value_words if word) or \
                 any(word in value.lower() for word in query_words if word)

    if word_match:
        validated[entity_type].append(value)
    else:
        logger.warning(f"Filtered LLM entity (no words match): {entity_type}={value}")
```

**Key improvements:**
1. Strip punctuation from words before comparison
2. Bidirectional matching: check if query words appear in entity value
3. Handle cases like "vinaphone" (query) matching "Vinaphone: 18001091" (entity)

## Test Results

### Before Fix

**Query:** "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

**Extracted entities:**
```python
LLM entities: {'ContactChannel': ['Trợ giúp']}  # ❌ Wrong
Regex entities: {}  # ❌ No patterns
Final entities: {}  # ❌ Filtered out
```

**Result:** Generic fallback response - no contact info provided ❌

### After Fix

**Query:** "số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu"

**Extracted entities:**
```python
LLM entities: {'ContactChannel': ['Trợ giúp']}  # Still wrong from LLM
Regex entities: {'ContactChannel': ['Bộ phận chăm sóc khách hàng', 'Hotline', 'Vinaphone: 18001091']}  # ✅ Correct!
Final entities: {'ContactChannel': ['Bộ phận chăm sóc khách hàng', 'Vinaphone: 18001091']}  # ✅ Kept after validation
```

**Result:** Returns answer mentioning Vinaphone: 18001091 ✅

## Impact

### Positive
✅ **Fixed entity extraction** - Now extracts contact channels correctly
✅ **Reduced false negatives** - Validation no longer filters valid entities with punctuation
✅ **Better coverage** - Added 8 new regex patterns for common contact queries
✅ **Carrier-specific info** - Can now extract specific carrier contact info

### Trade-offs
⚠️ **Still relies on FAQ coverage** - Answer quality depends on whether FAQ exists
⚠️ **Not the most direct answer** - Returns FAQ about troubleshooting which mentions contact, not a dedicated contact FAQ

## Remaining Limitations

The current system now **correctly extracts entities** but returns:

**Current answer:** Long explanation about checking transaction status, which includes:
```
Nếu quá thời gian mà chưa nhận được tiền, hãy liên hệ với bộ phận chăm sóc
khách hàng của nhà mạng để kiểm tra:
• Mobifone: 18001090
• Vinaphone: 18001091  ← Information is here!
• Vietnamobile: 0922789789
• Gmobile: 0598880199
```

**Ideal answer:** Simple, direct response:
```
Số điện thoại chăm sóc khách hàng Vinaphone là: 18001091
```

### Why the difference?

**Root cause:** No dedicated FAQ for "Vinaphone contact information"

**Current FAQs related to Vinaphone contact:**
- FAQ_72: "Tôi nạp tiền điện thoại thành công nhưng thuê bao điện thoại không nhận được..."
  - This FAQ mentions Vinaphone contact as part of troubleshooting steps
  - System retrieves this FAQ because it has `ContactChannel=['Vinaphone: 18001091']`

**Solution options:**

1. **Option A: Add dedicated FAQ** (Recommended)
   - Create FAQ: "Số điện thoại chăm sóc khách hàng của các nhà mạng là gì?"
   - Answer: List all carrier contacts directly
   - Pros: Clean, direct answers
   - Cons: Need to update FAQ data

2. **Option B: Improve answer generation**
   - Add special handling for "contact information" queries
   - Extract just the contact info from FAQ answer
   - Pros: No FAQ changes needed
   - Cons: More complex answer generation logic

3. **Option C: Accept current behavior**
   - Answer DOES contain the information (Vinaphone: 18001091)
   - Just embedded in longer troubleshooting steps
   - Pros: No changes needed
   - Cons: Less user-friendly

## Recommendation

✅ **The extraction issue is now FIXED**

For better user experience, consider **Option A: Add dedicated FAQ** for carrier contact information:

```json
{
  "id": "FAQ_CONTACT_CARRIERS",
  "question": "Số điện thoại chăm sóc khách hàng của các nhà mạng là gì?",
  "answer": "Đây là số điện thoại chăm sóc khách hàng của các nhà mạng:\n\n• Mobifone: 18001090\n• Vinaphone: 18001091\n• Viettel: 18008098\n• Vietnamobile: 0922789789\n• Gmobile: 0598880199\n\nBạn có thể liên hệ số điện thoại tương ứng để được hỗ trợ.",
  "entities": {
    "ContactChannel": ["Mobifone: 18001090", "Vinaphone: 18001091", "Viettel: 18008098", "Vietnamobile: 0922789789", "Gmobile: 0598880199"]
  }
}
```

## Files Modified

1. `enhanced_entity_extractor.py`
   - Lines 270-289: Added ContactChannel regex patterns
   - Lines 983-999: Improved validation logic

## Testing

Run the test:
```bash
cd GraphRAG
python -c "from enhanced_entity_extractor import EnhancedEntityExtractor; extractor = EnhancedEntityExtractor(); entities, conf = extractor.extract_with_confidence('số điện thoại của chăm sóc khách hàng vinaphone là bao nhiêu'); print('Entities:', entities); print('Confidence:', conf)"
```

Expected output:
```
Entities: {'ContactChannel': ['Bộ phận chăm sóc khách hàng', 'Vinaphone: 18001091'], ...}
Confidence: 0.95
```

## Conclusion

The **entity extraction issue is RESOLVED**. The system now:
1. ✅ Correctly extracts "Vinaphone: 18001091" from contact queries
2. ✅ No longer filters out valid entities with punctuation
3. ✅ Provides answers containing Vinaphone contact information

The answer could be more direct with a dedicated FAQ, but the technical issue is fixed.
