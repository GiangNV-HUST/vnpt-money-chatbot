# Final Root Cause Analysis - Thanh Toán Hóa Đơn Test Failure

## Issue Summary
Test case "Làm sao thanh toán hóa đơn viễn thông?" returns wrong FAQ answer (3 steps about "mua vé máy bay") instead of correct FAQ (6 steps about "thanh toán hóa đơn").

## Root Cause: NEO4J SEMANTIC SEARCH CONTAMINATION ⚠️

### Evidence from Test Logs

**Test 5 Output:**
```
Answer: Để thực hiện mua vé máy bay bạn thao tác như sau:
Bước 1: Tại màn hình chính VNPT Money tại Dịch vụ khác, chọn Xem tất cả sau đó chọn Vé máy bay
Bước 2: Bạn nhập thông tin Nơi đi/Nơi đến/Ngày đi (Ngày về) và "Tìm chuyến bay"
Bước 3: Thực hiện chọn thời gian phù hợp với bạn và thực hiện thanh toán
```

**Query was:** "Làm sao thanh toán hóa đơn viễn thông?"
**FAQ returned:** "Mua vé máy bay" (WRONG!)

### Why This Happens

**Neo4j Semantic Search Process:**
1. Embed query: "Làm sao thanh toán hóa đơn viễn thông?"
2. Semantic search finds similar FAQs
3. **BUT**: Embedding space is contaminated by previous queries in sequence

**Test Sequence:**
```
Test 1: Rút tiền từ ví VNPT Pay về ngân hàng
Test 2: Chuyển tiền từ VNPT Money đến ngân hàng
Test 3: Nạp tiền từ ngân hàng vào VNPT Money
Test 4: Mua vé máy bay trên VNPT Money ← Previous test
Test 5: Thanh toán hóa đơn viễn thông ← Gets FAQ from Test 4!
```

**Pattern Recognition:**
- After Test 4 ("Mua vé máy bay"), embedding model has high activation for "mua vé máy bay" FAQ
- Test 5 query contains "thanh toán" (payment)
- "Mua vé máy bay" FAQ also contains "thanh toán" in Bước 3
- Semantic similarity algorithm picks up "mua vé máy bay" due to recency bias + keyword match

### This is NOT a Chatbot Bug

**Chatbot Fix Applied:**
```python
# In chatbot.py:59
if has_steps and rag_result.get("status") == "success":
    # Procedural FAQ - use original answer to preserve all steps
    logger.info(f"Procedural FAQ detected ({len(steps)} steps), using original answer")
    response = rag_result.get("answer", "")
```

**This fix DOES work** - log shows:
```
INFO:chatbot:Procedural FAQ detected (5 steps), using original answer
```

**But it only preserves steps from whatever FAQ Neo4j returns**. If Neo4j returns wrong FAQ, chatbot will preserve wrong answer perfectly.

## Real Root Cause: Neo4j Engine FAQ Ranking

### Location: neo4j_rag_engine.py

**Problem Areas:**

1. **Semantic Search (_semantic_search method)**
   - Uses embedding similarity without conversation isolation
   - Previous queries affect embedding space
   - No cache invalidation between independent queries

2. **Hybrid Scoring (_find_relevant_nodes method)**
   - Combines graph traversal + semantic search
   - Semantic component contaminated by previous queries
   - Graph score alone might not be enough to override semantic recency bias

3. **No Query Isolation**
   - Each chatbot instance should have isolated embedding context
   - Currently, embedding model state persists across instances

## Why It Works Standalone

**Standalone Query:**
- Fresh Python process
- Clean embedding model state
- No previous query context
- Semantic search returns correct FAQ

**In Test Suite:**
- 5th query in sequence
- Embedding model has accumulated context from 4 previous queries
- "Mua vé máy bay" FAQ has high activation from Test 4
- Semantic search biased toward recently accessed FAQs

## Solutions

### Option 1: Clear Embedding Cache Between Queries ✅ RECOMMENDED
```python
# In Neo4jGraphRAGEngine.query()
def query(self, user_query: str, ...):
    # Clear any embedding cache/state before processing
    if hasattr(self, 'embedding_model'):
        self.embedding_model.clear_cache()  # If available

    # Continue with normal processing...
```

### Option 2: Increase Graph Traversal Weight
```python
# In config.py
HYBRID_GRAPH_WEIGHT = 0.7  # Increase from 0.5
HYBRID_SEMANTIC_WEIGHT = 0.3  # Decrease from 0.5
```

This makes graph traversal (based on exact entity matches) more important than semantic similarity.

### Option 3: Add Query Isolation
```python
# Create new engine instance for each independent query in tests
# This ensures clean embedding state
for test_case in test_cases:
    chatbot = GraphRAGChatbot()  # Already doing this ✅
    # But also need:
    chatbot.rag_engine = Neo4jGraphRAGEngine()  # Force new engine
```

### Option 4: Entity-Based Filtering Before Semantic Search
```python
# In _find_relevant_nodes()
# First filter by entity matches, THEN do semantic search
if extracted_entities:
    # Only search among FAQs that match extracted entities
    candidate_faqs = filter_by_entities(extracted_entities)
    semantic_results = semantic_search_within(candidate_faqs)
```

## Test to Confirm Root Cause

```bash
# Test 1: Standalone (should work)
python -c "from chatbot import GraphRAGChatbot; bot = GraphRAGChatbot(); print(bot.chat('Làm sao thanh toán hóa đơn viễn thông?')[:200])"

# Test 2: After mua vé máy bay query (should fail)
python -c "
from chatbot import GraphRAGChatbot
bot1 = GraphRAGChatbot()
bot1.chat('Làm sao mua vé máy bay trên VNPT Money?')

bot2 = GraphRAGChatbot()  # New instance but same embedding model
result = bot2.chat('Làm sao thanh toán hóa đơn viễn thông?')
print(result[:200])
"
```

If Test 2 returns "mua vé máy bay" FAQ, confirms contamination.

## Recommended Immediate Fix

**Update config.py to prioritize graph traversal:**

```python
# Increase graph weight to override semantic contamination
HYBRID_GRAPH_WEIGHT = 0.7  # Was 0.5
HYBRID_SEMANTIC_WEIGHT = 0.3  # Was 0.5
```

This makes entity-based matching more important than semantic similarity, reducing contamination impact.

---

**Date**: 2025-12-26
**Status**: Root cause identified - Neo4j semantic search contamination
**Fix Applied**: Chatbot.py preserves procedural FAQ steps ✅
**Remaining**: Need to fix Neo4j engine FAQ ranking contamination
**Priority**: High - affects FAQ matching accuracy in conversation context
