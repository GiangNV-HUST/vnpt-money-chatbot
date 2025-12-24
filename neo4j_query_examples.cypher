// ============================================================================
// NEO4J CYPHER QUERIES - Quan sát cấu trúc Graph
// ============================================================================
// Copy các query này vào Neo4j Browser (http://localhost:7474)
// hoặc Neo4j Desktop Query tab để chạy
// ============================================================================


// ----------------------------------------------------------------------------
// 1. KIỂM TRA CÁC NODE TYPES VÀ SỐ LƯỢNG
// ----------------------------------------------------------------------------

// Đếm tất cả node types
MATCH (n)
RETURN labels(n) as NodeType, count(n) as Count
ORDER BY Count DESC;

// Kết quả mong đợi:
// NodeType     | Count
// ["FAQ"]      | ~500
// ["Topic"]    | ~50
// ["Service"]  | ~10
// ["Process"]  | ~50
// ["Step"]     | ~300-400
// ["Bank"]     | ~30


// ----------------------------------------------------------------------------
// 2. XEM CẤU TRÚC FAQ CÓ PROCESS VÀ STEPS
// ----------------------------------------------------------------------------

// Tìm 1 FAQ có Process và Steps (VD: FAQ về chuyển tiền)
MATCH (faq:FAQ)
WHERE faq.question CONTAINS "chuyển tiền" AND faq.question CONTAINS "như thế nào"
OPTIONAL MATCH (faq)-[:DESCRIBES_PROCESS]->(p:Process)
OPTIONAL MATCH (p)-[:HAS_STEP]->(s:Step)
RETURN faq.id, faq.question,
       p.name as process_name,
       count(s) as num_steps
LIMIT 5;


// ----------------------------------------------------------------------------
// 3. VISUALIZE FULL GRAPH: FAQ → PROCESS → STEPS
// ----------------------------------------------------------------------------

// Query này sẽ show visual graph trong Neo4j Browser
// Chọn 1 FAQ cụ thể (thay FAQ_226 bằng ID bạn tìm được ở query trên)
MATCH path = (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;

// Hoặc tìm bất kỳ FAQ nào có Process
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain
LIMIT 1;


// ----------------------------------------------------------------------------
// 4. XEM CHI TIẾT TẤT CẢ STEPS CỦA 1 FAQ
// ----------------------------------------------------------------------------

// Lấy tất cả steps theo thứ tự
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE faq.question CONTAINS "chuyển tiền đến ngân hàng"
RETURN s.number, s.text
ORDER BY s.number;


// ----------------------------------------------------------------------------
// 5. FIND FIRST STEP (không có step nào trỏ đến)
// ----------------------------------------------------------------------------

MATCH (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(first:Step)
WHERE NOT ()-[:NEXT_STEP]->(first)  // No incoming NEXT_STEP
RETURN first.number, first.text;


// ----------------------------------------------------------------------------
// 6. TRACE STEP CHAIN (từ đầu đến cuối)
// ----------------------------------------------------------------------------

// Tìm first step và follow NEXT_STEP chain
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(first:Step)
WHERE faq.question CONTAINS "chuyển tiền đến ngân hàng"
  AND NOT ()-[:NEXT_STEP]->(first)
MATCH path = (first)-[:NEXT_STEP*0..]->(s:Step)
RETURN [node in nodes(path) | node.number] as step_numbers,
       [node in nodes(path) | node.text] as step_texts;


// ----------------------------------------------------------------------------
// 7. TÌM TẤT CẢ PROCESSES VÀ SỐ BƯỚC
// ----------------------------------------------------------------------------

MATCH (p:Process)-[:HAS_STEP]->(s:Step)
RETURN p.name as process_type,
       p.description as example_faq,
       count(s) as num_steps
ORDER BY num_steps DESC
LIMIT 20;


// ----------------------------------------------------------------------------
// 8. TÌM FAQs KHÔNG CÓ PROCESS (FAQs thông thường)
// ----------------------------------------------------------------------------

MATCH (faq:FAQ)
WHERE NOT (faq)-[:DESCRIBES_PROCESS]->()
RETURN faq.id, faq.question
LIMIT 10;


// ----------------------------------------------------------------------------
// 9. TÌM FAQs CÓ NHIỀU STEPS NHẤT
// ----------------------------------------------------------------------------

MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as num_steps
WHERE num_steps >= 5
RETURN faq.id,
       faq.question,
       p.name as process_type,
       num_steps
ORDER BY num_steps DESC
LIMIT 10;


// ----------------------------------------------------------------------------
// 10. CHECK SPECIFIC STEP
// ----------------------------------------------------------------------------

// Tìm step cụ thể (VD: step 3 của process transfer)
MATCH (s:Step)
WHERE s.process_id CONTAINS "transfer" AND s.number = 3
RETURN s.id, s.number, s.text, s.process_id
LIMIT 5;


// ----------------------------------------------------------------------------
// 11. VERIFY NEXT_STEP RELATIONSHIPS
// ----------------------------------------------------------------------------

// Check xem có bao nhiêu steps có NEXT_STEP
MATCH (s1:Step)-[:NEXT_STEP]->(s2:Step)
RETURN count(*) as total_next_step_relationships;

// Xem các NEXT_STEP relationships
MATCH (s1:Step)-[:NEXT_STEP]->(s2:Step)
WHERE s1.process_id CONTAINS "transfer"
RETURN s1.number, s1.text, s2.number, s2.text
ORDER BY s1.number
LIMIT 10;


// ----------------------------------------------------------------------------
// 12. FIND BROKEN CHAINS (Steps không có NEXT_STEP nhưng không phải cuối)
// ----------------------------------------------------------------------------

MATCH (p:Process)-[:HAS_STEP]->(s:Step)
WITH p, max(s.number) as max_step
MATCH (p)-[:HAS_STEP]->(s:Step)
WHERE NOT (s)-[:NEXT_STEP]->()
  AND s.number < max_step
RETURN p.name, s.number, s.text
LIMIT 10;


// ----------------------------------------------------------------------------
// 13. COMPARE FAQ WITH/WITHOUT PROCESSES
// ----------------------------------------------------------------------------

// Count FAQs có Process
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->()
WITH count(faq) as with_process

// Count tất cả FAQs
MATCH (faq:FAQ)
WITH with_process, count(faq) as total

RETURN total as total_faqs,
       with_process as faqs_with_process,
       total - with_process as faqs_without_process,
       round(100.0 * with_process / total, 2) as percentage_with_process;


// ----------------------------------------------------------------------------
// 14. FULL EXAMPLE: Query như Bot làm
// ----------------------------------------------------------------------------

// Giả sử bot tìm được FAQ_226, lấy steps để trả lời
MATCH (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)

// Tìm first step
MATCH (p)-[:HAS_STEP]->(first:Step)
WHERE NOT ()-[:NEXT_STEP]->(first)

// Follow chain
MATCH path = (first)-[:NEXT_STEP*0..]->(s:Step)

// Extract steps theo thứ tự
WITH nodes(path) as steps_chain
UNWIND steps_chain as step

RETURN step.number as step_num,
       step.text as step_text
ORDER BY step.number;


// ----------------------------------------------------------------------------
// 15. SEARCH BY USER CONTEXT
// ----------------------------------------------------------------------------

// User nói: "Tôi đã chọn mục Chuyển tiền rồi, tiếp theo làm gì?"
// Bot tìm step có text match "Chuyển tiền", rồi lấy next step

MATCH (s:Step)
WHERE s.text CONTAINS "chọn mục" AND s.text CONTAINS "Chuyển tiền"
MATCH (s)-[:NEXT_STEP]->(next:Step)
RETURN s.number as current_step,
       s.text as current_action,
       next.number as next_step_number,
       next.text as next_action
LIMIT 3;


// ----------------------------------------------------------------------------
// 16. STATISTICS: Process Types Distribution
// ----------------------------------------------------------------------------

MATCH (p:Process)
WITH p.name as process_type, count(*) as count
RETURN process_type, count
ORDER BY count DESC;


// ----------------------------------------------------------------------------
// 17. EXAMPLE: Complex Query - Find Related FAQs in Same Process
// ----------------------------------------------------------------------------

// Tìm các FAQs khác cùng loại process
MATCH (faq1:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p1:Process)
MATCH (faq2:FAQ)-[:DESCRIBES_PROCESS]->(p2:Process)
WHERE p1.name = p2.name AND faq1 <> faq2
RETURN faq2.id, faq2.question, p2.name
LIMIT 5;


// ============================================================================
// HELPFUL DEBUGGING QUERIES
// ============================================================================

// Check if Process nodes exist
MATCH (p:Process) RETURN count(p);

// Check if Step nodes exist
MATCH (s:Step) RETURN count(s);

// Check if DESCRIBES_PROCESS relationship exists
MATCH ()-[r:DESCRIBES_PROCESS]->() RETURN count(r);

// Check if HAS_STEP relationship exists
MATCH ()-[r:HAS_STEP]->() RETURN count(r);

// Check if NEXT_STEP relationship exists
MATCH ()-[r:NEXT_STEP]->() RETURN count(r);


// ============================================================================
// NOTE: Nếu các queries trả về 0 results cho Process/Step nodes
// → Có thể Step nodes chưa được migrate
// → Chạy: python graphRAGChatBot/migrate_steps_to_neo4j.py
// ============================================================================
