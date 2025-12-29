# Fix: Chitchat Detection False Positive

## Problem

The chatbot was incorrectly classifying technical questions as chitchat, causing it to respond with a generic introduction instead of answering the actual question.

### Example

**User Question:**
```
Tôi thực hiện sinh trắc học hệ thống báo lỗi "Họ tên bạn không trùng Khách khớp với định danh hiện tại"
```

**Incorrect Response (Before Fix):**
```
Tôi là VNPT Assistant - trợ lý ảo thông minh của VNPT Money...
```

**Expected Response:**
Should provide troubleshooting steps for the biometric error.

## Root Cause

The `_is_chitchat()` function in `chatbot.py` used **substring matching** without word boundaries:

```python
chitchat_patterns = [
    "xin chào", "chào bạn", "hello", "hi ", "chào",
    "bạn là ai", "bạn là gì", "tên bạn", "ai đây",  # ❌ Problem here!
    ...
]
return any(pattern in message_lower for pattern in chitchat_patterns)
```

The pattern `"tên bạn"` matched:
- ✅ **Intended:** "**tên bạn** là gì?" (chitchat - asking bot's name)
- ❌ **False positive:** "Họ **tên bạn** không trùng" (technical error about user's name)

## Solution

Replaced substring matching with **regex patterns using word boundaries** (`\b`):

### Before (Buggy)
```python
chitchat_patterns = ["tên bạn", ...]
return any(pattern in message_lower for pattern in chitchat_patterns)
```

### After (Fixed)
```python
identity_patterns = [
    r'\btên bạn là\b',   # "tên bạn là gì?"
    r'\btên bạn\?',      # "tên bạn?"
    r'^tên bạn\b',       # Only at start of message
    ...
]
```

## Changes Made

**File:** `GraphRAG/chatbot.py`

**Function:** `_is_chitchat()` (lines 59-106)

**Key Improvements:**

1. **Word Boundary Matching:** Use `\b` to match whole words only
2. **Context-Aware Patterns:**
   - `"tên bạn là"` instead of just `"tên bạn"`
   - `"tên bạn?"` to detect questions specifically
3. **Position-Based Matching:** `^tên bạn\b` only matches at message start
4. **Better Greeting Detection:**
   - `r'^chào\b'` matches "chào" at start
   - `r'\bchào$'` matches "chào" at end

## Test Results

### Test Cases (All Passing ✓)

| Message | Old Result | New Result | Expected | Status |
|---------|-----------|-----------|----------|--------|
| "Họ tên bạn không khớp với định danh" | True (❌ wrong) | False | False | ✓ FIXED |
| "Tôi thực hiện sinh trắc học hệ thống báo lỗi..." | True (❌ wrong) | False | False | ✓ FIXED |
| "Tên bạn là gì?" | True | True | True | ✓ Correct |
| "Bạn là ai?" | True | True | True | ✓ Correct |
| "Hi" | False (❌ wrong) | True | True | ✓ FIXED |

### End-to-End Test

**User:** "Tôi thực hiện sinh trắc học hệ thống báo lỗi 'Họ tên bạn không trùng Khách khớp với định danh hiện tại'"

**Bot Response (After Fix):**
```
Để giải quyết lỗi "Họ tên bạn không trùng Khách khớp với định danh hiện tại"
khi thực hiện sinh trắc học, bạn cần làm một số việc nhé:

Đầu tiên, hãy chuẩn bị các thông tin cần thiết như số ví của bạn.

Tiếp theo, chụp ảnh giấy tờ CCCD của bạn (2 mặt) và ảnh thông báo lỗi
mà hệ thống gửi cho bạn.

Sau đó, bạn gửi tất cả những thông tin này vào mục Trợ giúp trên ứng dụng
VNPT Money để được hỗ trợ.

Cuối cùng, sau khi tiếp nhận yêu cầu, VNPT Money sẽ kiểm tra và phản hồi
lại kết quả xử lý cho bạn.

💡 Đừng lo nhé, đội ngũ hỗ trợ sẽ giúp bạn nhanh chóng!
```

**Status:** ✅ **CORRECT - Bot now provides proper troubleshooting steps**

## Impact

- **Accuracy Improvement:** Technical questions are no longer misclassified as chitchat
- **User Experience:** Users receive relevant answers instead of generic greetings
- **No Regression:** All legitimate chitchat patterns still work correctly
- **Additional Fix:** "Hi" greeting now correctly detected (was broken before)

## Related Files

- `chatbot.py` - Main fix applied here
- `debug_chitchat_issue.py` - Debug script to identify the problem
- `test_chitchat_fix.py` - Test script to verify the solution
- `test_biometric_error.py` - End-to-end integration test

## Conclusion

The fix successfully resolves the false positive issue by using precise regex patterns
with word boundaries instead of naive substring matching. All test cases pass, and
the chatbot now correctly distinguishes between technical questions and chitchat.
