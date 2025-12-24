# Case Nodes Implementation Summary

## Overview
Successfully implemented Case nodes functionality to handle FAQs with multiple methods/conditions, allowing the chatbot to return only the relevant method based on user queries.

## Problem Solved

### Original Issue
When users asked about a specific method for depositing money to Mobile Money (e.g., "from linked bank"), the chatbot was returning ALL methods:
- 5 steps for "Nạp tiền từ ngân hàng liên kết trực tiếp"
- Additional note about "Nạp bằng Chuyển khoản ngân hàng (QR)"

### Root Cause
- FAQ answer contained both methods combined in a single text
- No separation between different methods/cases
- RAG engine retrieved the full FAQ answer without filtering

## Solution Implemented

### 1. Created Case Nodes Structure
Created 2 Case nodes for the Mobile Money deposit FAQ:

**Case 1: Nạp tiền từ ngân hàng liên kết trực tiếp**
- case_id: `mobile_money_deposit_case_1`
- case_type: `method`
- method: `bank_linked`
- 5 Step nodes (existing steps were linked to this Case)

**Case 2: Nạp bằng Chuyển khoản ngân hàng**
- case_id: `mobile_money_deposit_case_2`
- case_type: `method`
- method: `bank_transfer_qr`
- 1 Step node (QR transfer instructions)

### 2. Updated Neo4j RAG Engine
Modified [neo4j_rag_engine.py](neo4j_rag_engine.py) to:

**Retrieve Case nodes** (lines 611-645):
```python
# Separate query for Case nodes
case_cypher = """
MATCH (f:FAQ {id: $node_id})-[:HAS_CASE]->(case:Case)
OPTIONAL MATCH (case)-[:HAS_STEP]->(step:Step)
RETURN case.case_id, case.name, case.description, case.case_type, case.method,
       collect({number: step.number, text: step.text}) as steps
ORDER BY case.case_id
"""
```

**Select appropriate Case** based on query keywords (lines 671-719):
```python
# Keyword matching
if 'liên kết' in query_lower:
    if 'liên kết' in case_name or 'bank_linked' in case_method:
        score += 10

if 'chuyển khoản' in query_lower or 'qr' in query_lower:
    if 'chuyển khoản' in case_name or 'qr' in case_method:
        score += 10
```

**Format answer with Case steps** (lines 721-730):
```python
if case_steps and selected_case:
    steps_text = "\n".join([
        f'Bước {step["number"]}: {step["text"]}'
        for step in case_steps
    ])
    case_name = selected_case.get('name', '')
    case_based_answer = f"{case_name}:\n\n{steps_text}"
```

### 3. Updated FAQ Answer
Changed FAQ answer from detailed content to brief introduction:
```
Để thực hiện nạp tiền vào tài khoản Mobile Money có 2 hình thức:
Nạp tiền từ ngân hàng liên kết trực tiếp hoặc Nạp bằng Chuyển khoản ngân hàng (QR code).
```

## Testing Results

### Test 1: Query with "liên kết"
**Query**: "Tôi có thể nạp tiền từ ngân hàng liên kết vào tài khoản Mobile Money như thế nào"

**Result**: ✅ Returns only 5 steps for "Nạp tiền từ ngân hàng liên kết trực tiếp"

**Log**: `Selected Case: Nạp tiền từ ngân hàng liên kết trực tiếp (5 steps)`

### Test 2: Query with "chuyển khoản"
**Query**: "Tôi có thể nạp tiền vào Mobile Money bằng chuyển khoản ngân hàng như thế nào"

**Result**: ✅ Returns only steps for "Nạp bằng Chuyển khoản ngân hàng" (QR method)

**Log**: `Selected Case: Nạp bằng Chuyển khoản ngân hàng (1 steps)`

### Test 3: General query
**Query**: "Tôi có thể nạp tiền từ ngân hàng vào tài khoản Mobile Money như thế nào"

**Result**: ✅ Returns default method (linked bank, 5 steps)

**Log**: `Selected Case: Nạp tiền từ ngân hàng liên kết trực tiếp (5 steps)`

## Graph Structure

```
(FAQ: "Tôi có thể nạp tiền từ ngân hàng vào tài khoản Mobile Money như thế nào?")
  |
  ├── [:HAS_CASE] → (Case 1: "Nạp tiền từ ngân hàng liên kết trực tiếp")
  |                    |
  |                    ├── [:HAS_STEP] → (Step 1: Tại giao diện chính...)
  |                    ├── [:HAS_STEP] → (Step 2: Chọn nguồn tiền...)
  |                    ├── [:HAS_STEP] → (Step 3: Màn hình xác nhận...)
  |                    ├── [:HAS_STEP] → (Step 4: Màn hình nhập OTP...)
  |                    └── [:HAS_STEP] → (Step 5: Màn hình xác nhận thành công...)
  |
  └── [:HAS_CASE] → (Case 2: "Nạp bằng Chuyển khoản ngân hàng")
                       |
                       └── [:HAS_STEP] → (Step 1: Bạn chọn ngân hàng, lưu QR...)
```

## Automation for Other FAQs

Created [auto_create_case_nodes.py](auto_create_case_nodes.py) to automatically analyze and create Case nodes for other FAQs.

### Patterns Detected
1. **Method pattern**: "có X hình thức/cách"
2. **Condition pattern**: Numbered "Trường hợp 1, 2, 3..."
3. **If-then pattern**: "Nếu...thì" structures

### Analysis Results
- Total documents analyzed: 803
- FAQs needing Case nodes: 6 identified with clear patterns
- Pattern distribution:
  - method: 2 FAQs
  - if_then: 3 FAQs
  - condition: 1 FAQ

### Example FAQs Identified
1. "Tôi có thể nạp tiền từ ngân hàng vào ứng dụng VNPT Money như thế nào?" (2 methods)
2. "Tôi thực hiện giao dịch nạp tiền thất bại nhưng ngân hàng đã trừ tiền" (3 if-then cases)
3. "Tôi nạp tiền điện thoại thành công nhưng thuê bao điện thoại không nhận được..." (2 conditions)

## Files Modified/Created

### Modified
1. [neo4j_rag_engine.py](neo4j_rag_engine.py) - Added Case node retrieval and selection logic
2. Neo4j database - Added 2 Case nodes with relationships

### Created
1. [fix_mobile_money_cases.py](fix_mobile_money_cases.py) - Script to create Mobile Money Case nodes
2. [test_case_nodes.py](test_case_nodes.py) - Test script for Case nodes functionality
3. [auto_create_case_nodes.py](auto_create_case_nodes.py) - Automated analyzer for other FAQs
4. [check_faq_answer.py](check_faq_answer.py) - Utility to check FAQ answers

## Next Steps (Optional)

1. Run `auto_create_case_nodes.py --execute` to create Case nodes for the 6 identified FAQs
2. Expand pattern matching to find more FAQs that could benefit from Case nodes
3. Monitor chatbot responses to ensure Case selection accuracy
4. Consider adding more sophisticated keyword matching or semantic similarity for Case selection

## Technical Notes

### Case Node Properties
- `case_id`: Unique identifier
- `name`: Display name of the case
- `description`: Brief description
- `case_type`: Type (method, condition, if_then, scenario)
- `method` (optional): Method identifier for keyword matching

### Case Selection Algorithm
1. Extract keywords from user query
2. Score each Case based on keyword matches
3. Select Case with highest score
4. Format answer using selected Case's steps
5. Fall back to full FAQ answer if no Cases exist

## Benefits

1. **Precision**: Users get exactly what they asked for
2. **Clarity**: Responses are focused and not overwhelming
3. **Scalability**: Pattern-based automation can handle hundreds of FAQs
4. **Maintainability**: Case nodes are separate entities, easy to update
5. **Flexibility**: Can add new Cases without modifying FAQ structure
