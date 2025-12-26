# LLM-First Extraction Strategy (80% LLM, 20% Regex)
**Date**: 2025-12-26
**Goal**: Maximize extraction quality by prioritizing LLM over Regex

---

## 📊 Current Strategy (Regex-First)

### How It Works Now:
1. **Regex extraction** runs first (fast, cheap)
2. Calculate confidence score
3. If confidence < 45% → **LLM fallback** (slow, expensive)
4. Merge results

### Statistics:
- **LLM usage**: 13% of queries (low confidence cases)
- **Regex usage**: 87% of queries
- **Accuracy**: ~91% (good but not optimal)
- **Cost**: Very low
- **Speed**: Very fast

### Problems:
- Regex misses contextual understanding
- Generic extractions for edge cases
- Some queries need semantic understanding
- Conservative LLM threshold (45%) may miss opportunities

---

## 🎯 Proposed Strategy (LLM-First)

### How It Should Work:
1. **Always use LLM** for entity extraction (80% weight)
2. Run regex patterns in parallel (20% weight)
3. **Intelligent merge**: LLM takes priority, regex fills gaps
4. Use regex for validation/augmentation only

### Benefits:
- ✅ **Better context understanding**
- ✅ **More accurate entity extraction**
- ✅ **Handles edge cases naturally**
- ✅ **Consistent results across query variations**
- ✅ **Better multi-entity detection**

### Trade-offs:
- ❌ Higher API cost (100% queries use LLM vs 13%)
- ❌ Slower response time (~1-2s vs ~50ms)
- ✅ Much better accuracy (estimated 95%+ vs 91%)

---

## 🔧 Implementation Options

### Option 1: Always LLM (Simplest)
```python
# Remove confidence threshold completely
ENABLE_LLM_FALLBACK = True
LLM_FALLBACK_THRESHOLD = 1.0  # Always trigger LLM

# In extract_with_confidence():
# Skip regex-only path, always use LLM
llm_entities = self._extract_with_llm(query)
regex_entities = self._extract_with_regex(query)
entities = self._intelligent_merge(llm_entities, regex_entities, llm_weight=0.8)
```

**Pros**: Simple, guaranteed LLM usage
**Cons**: Wastes regex computation if not used

---

### Option 2: LLM-First with Regex Augmentation (Recommended)
```python
# New extraction flow
def extract_with_confidence(self, query: str):
    # Step 1: LLM extraction (PRIMARY - 80% weight)
    llm_entities = self._extract_with_llm(query)

    # Step 2: Regex extraction (SECONDARY - 20% weight)
    regex_entities = self._extract_with_regex(query)

    # Step 3: Intelligent merge (LLM priority)
    entities = self._merge_llm_priority(
        llm_entities,
        regex_entities,
        llm_weight=0.8
    )

    # Step 4: Regex validation (catch obvious errors)
    entities = self._validate_with_regex(query, entities)

    return entities, confidence=0.95
```

**Pros**:
- LLM provides semantic understanding
- Regex catches specific patterns LLM might miss
- Validation prevents hallucinations

**Cons**:
- 100% LLM calls (higher cost)

---

### Option 3: Hybrid with High LLM Usage (Balanced)
```python
# Lower threshold dramatically
LLM_FALLBACK_THRESHOLD = 0.10  # Use LLM if confidence < 10%

# Most queries will use LLM (~80%)
# Only very high-confidence regex patterns skip LLM
```

**Pros**:
- ~80% LLM usage (cost-effective)
- Fast path for obvious queries
- Balanced approach

**Cons**:
- Still some regex-only queries

---

## 📈 Expected Improvements

### Accuracy:
| Metric | Current (Regex-First) | Proposed (LLM-First) | Improvement |
|--------|----------------------|---------------------|-------------|
| **Topic extraction** | 91% | 97% | +6% |
| **Multi-entity queries** | 85% | 95% | +10% |
| **Edge cases** | 70% | 92% | +22% |
| **Overall accuracy** | 91% | 95-97% | **+4-6%** |

### Cost:
| Metric | Current | Proposed | Change |
|--------|---------|----------|--------|
| **LLM calls** | 13% | 100% | +670% |
| **Estimated monthly cost** | ~$5 | ~$35-40 | +$30-35 |

### Performance:
| Metric | Current | Proposed | Change |
|--------|---------|----------|--------|
| **Avg response time** | ~100ms | ~1.5s | +1.4s |
| **Cache hit rate** | N/A | ~30-40% | Improves over time |

---

## 🎯 Recommendation: Option 2 (LLM-First with Regex Augmentation)

### Why Option 2?
1. **Best accuracy** - LLM semantic understanding
2. **Regex adds value** - Catches specific patterns, validates results
3. **Prevents hallucinations** - Regex validation layer
4. **Cost is acceptable** - You stated cost is not important
5. **Scalable** - Can add caching later to reduce cost

### Implementation Plan:

#### Phase 1: Core Changes
1. ✅ Modify `extract_with_confidence()` to always use LLM first
2. ✅ Change merge strategy to prioritize LLM (80% weight)
3. ✅ Add regex validation layer
4. ✅ Update confidence calculation

#### Phase 2: Optimization
1. Add LRU cache for LLM results (reduce repeat queries)
2. Batch LLM requests where possible
3. Monitor accuracy vs baseline

#### Phase 3: Fine-tuning
1. Adjust LLM vs Regex weights based on results
2. Add specific regex validators for critical entities
3. Optimize prompt for better extraction

---

## 💰 Cost Analysis

### Current Costs (Regex-First):
- Queries per day: ~1000
- LLM calls: 130 (13%)
- Cost per 1M tokens: $0.15 (input) + $0.60 (output)
- Average tokens per call: ~500 input, ~200 output
- **Daily cost**: ~$0.15
- **Monthly cost**: ~$5

### Proposed Costs (LLM-First):
- Queries per day: ~1000
- LLM calls: 1000 (100%)
- **Daily cost**: ~$1.15
- **Monthly cost**: ~$35

### With Caching (30% hit rate):
- Unique queries per day: ~700
- **Daily cost**: ~$0.80
- **Monthly cost**: ~$24

**Conclusion**: Cost increase of ~$20-30/month is negligible for 4-6% accuracy improvement

---

## 🚀 Next Steps

### Immediate Actions:
1. ✅ Implement Option 2 (LLM-First with Regex Augmentation)
2. ✅ Update `extract_with_confidence()` method
3. ✅ Test with existing test suite
4. ✅ Compare accuracy before/after

### Future Enhancements:
1. Add LRU cache for LLM responses
2. Implement request batching
3. Add confidence-based fallback (for truly obvious cases)
4. Monitor and optimize prompt engineering

---

## 📝 Code Changes Required

### File: `enhanced_entity_extractor.py`

#### Change 1: New extraction method
```python
def extract_with_confidence_llm_first(self, query: str) -> Tuple[Dict[str, List[str]], float]:
    """
    LLM-FIRST extraction: Always use LLM for semantic understanding
    Regex provides validation and augmentation
    """
    import config

    # Step 1: LLM extraction (PRIMARY)
    try:
        llm_entities = self._extract_with_llm(query)
        llm_success = True
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        llm_entities = {}
        llm_success = False

    # Step 2: Regex extraction (SECONDARY - for validation/augmentation)
    regex_entities = self._extract_with_regex(query)

    # Step 3: Intelligent merge (LLM priority 80%, Regex 20%)
    if llm_success:
        entities = self._merge_llm_priority(llm_entities, regex_entities, llm_weight=0.8)
        confidence = 0.95
    else:
        # Fallback to regex-only if LLM fails
        entities = regex_entities
        confidence = self._calculate_confidence(query, entities)

    # Step 4: Validate results
    entities = self._validate_entities(query, entities)

    return entities, confidence
```

#### Change 2: Intelligent merge method
```python
def _merge_llm_priority(
    self,
    llm_entities: Dict[str, List[str]],
    regex_entities: Dict[str, List[str]],
    llm_weight: float = 0.8
) -> Dict[str, List[str]]:
    """
    Merge LLM and Regex results with LLM priority

    Strategy:
    - Take all LLM entities (80% weight)
    - Add regex entities only if:
      1. LLM didn't extract that entity type
      2. Regex entity is very specific (e.g., Bank, Document)
      3. Regex entity validates/augments LLM result
    """
    merged = {}

    # Start with all entity types
    all_types = set(llm_entities.keys()) | set(regex_entities.keys())

    for entity_type in all_types:
        llm_vals = llm_entities.get(entity_type, [])
        regex_vals = regex_entities.get(entity_type, [])

        # Priority 1: LLM values (always include)
        merged[entity_type] = llm_vals.copy()

        # Priority 2: Add regex values if:
        # - High-value entity types (Bank, Document, Error)
        # - LLM missed but regex found
        # - Regex value is more specific than LLM

        if entity_type in ['Bank', 'Document', 'Error', 'Status']:
            # These are factual entities - trust regex
            for rv in regex_vals:
                if rv not in merged[entity_type]:
                    merged[entity_type].append(rv)

        elif not llm_vals and regex_vals:
            # LLM missed, use regex
            merged[entity_type].extend(regex_vals)

        elif regex_vals:
            # Add regex if it provides additional detail
            for rv in regex_vals:
                # Check if regex value is more specific
                is_more_specific = any(
                    rv.lower() in lv.lower() and len(rv) > len(lv)
                    for lv in llm_vals
                )
                if is_more_specific and rv not in merged[entity_type]:
                    merged[entity_type].append(rv)

    return merged
```

#### Change 3: Configuration
```python
# In config.py
ENABLE_LLM_FALLBACK = True
USE_LLM_FIRST_STRATEGY = True  # NEW: Enable LLM-first mode
LLM_FIRST_REGEX_WEIGHT = 0.2  # Regex contributes 20%
```

---

## ✅ Testing Plan

### Test Suite:
1. Run all existing tests (should pass)
2. Compare LLM-first vs Regex-first accuracy
3. Measure response time impact
4. Monitor LLM API costs

### Success Criteria:
- ✅ Accuracy improvement: +4% or more
- ✅ No regressions in existing tests
- ✅ Response time: < 2s average
- ✅ Cost: < $50/month

---

**Status**: Ready for implementation
**Estimated time**: 1-2 hours
**Risk**: Low (can rollback to regex-first anytime)
