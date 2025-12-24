// ============================================================================
// NEO4J QUERIES - Visualize nhiều FAQs có Steps
// ============================================================================
// Copy các query này vào Neo4j Browser để xem graph visualization
// ============================================================================


// ----------------------------------------------------------------------------
// 1. FAQ VỀ CHUYỂN TIỀN (Transfer) - FAQ_226
// ----------------------------------------------------------------------------

// Query: Visualize full graph FAQ_226
MATCH path = (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;

// Query: Chỉ xem Steps text
MATCH (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
RETURN s.number, s.text
ORDER BY s.number;


// ----------------------------------------------------------------------------
// 2. FAQ VỀ NẠP TIỀN (Deposit) - FAQ_0
// ----------------------------------------------------------------------------

// Query: Visualize full graph FAQ_0
MATCH path = (faq:FAQ {id: "FAQ_0"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;

// Query: Xem Steps của FAQ nạp tiền
MATCH (faq:FAQ {id: "FAQ_0"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
RETURN s.number, s.text
ORDER BY s.number;


// ----------------------------------------------------------------------------
// 3. FAQ VỀ RÚT TIỀN (Withdrawal)
// ----------------------------------------------------------------------------

// Tìm FAQ về rút tiền
MATCH (faq:FAQ)
WHERE faq.question CONTAINS "rút tiền" AND faq.answer CONTAINS "Bước"
RETURN faq.id, faq.question
LIMIT 3;

// Sau khi có faq.id (ví dụ: FAQ_XXX), visualize:
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE faq.question CONTAINS "rút tiền về ngân hàng"
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;


// ----------------------------------------------------------------------------
// 4. FAQ VỀ THANH TOÁN (Payment)
// ----------------------------------------------------------------------------

// Tìm FAQ về thanh toán hóa đơn
MATCH (faq:FAQ)
WHERE faq.question CONTAINS "thanh toán" AND faq.answer CONTAINS "Bước"
RETURN faq.id, faq.question
LIMIT 3;

// Visualize FAQ thanh toán (thay FAQ_XXX bằng ID tìm được)
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE faq.question CONTAINS "thanh toán hóa đơn"
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;


// ----------------------------------------------------------------------------
// 5. FAQ VỀ LIÊN KẾT NGÂN HÀNG (Link Bank)
// ----------------------------------------------------------------------------

// Tìm FAQ về liên kết ngân hàng
MATCH (faq:FAQ)
WHERE faq.question CONTAINS "liên kết" AND faq.answer CONTAINS "Bước"
RETURN faq.id, faq.question
LIMIT 3;

// Visualize
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE faq.question CONTAINS "liên kết ngân hàng"
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain
LIMIT 100;


// ----------------------------------------------------------------------------
// 6. SO SÁNH NHIỀU FAQs CÙNG LOẠI PROCESS
// ----------------------------------------------------------------------------

// So sánh tất cả FAQs về chuyển tiền
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {name: "transfer"})-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as num_steps
RETURN faq.id,
       substring(faq.question, 0, 60) as question,
       num_steps
ORDER BY num_steps DESC;

// Visualize tất cả FAQs transfer cùng lúc (có thể phức tạp)
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {name: "transfer"})-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain
LIMIT 200;


// ----------------------------------------------------------------------------
// 7. VISUALIZE NHIỀU PROCESS TYPES
// ----------------------------------------------------------------------------

// Xem 1 FAQ của mỗi loại process
MATCH (p:Process)
WITH p.name as process_type, collect(p)[0] as sample_process
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(sample_process)-[:HAS_STEP]->(s:Step)
RETURN process_type, faq.id, substring(faq.question, 0, 60) as question, count(s) as steps
ORDER BY steps DESC;

// Visualize từng process type (chạy từng cái một)
// Transfer
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {name: "transfer"})-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain
LIMIT 50;

// Deposit
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {name: "deposit"})-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain
LIMIT 50;

// Payment
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process {name: "payment"})-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain
LIMIT 50;


// ----------------------------------------------------------------------------
// 8. TÌM VÀ VISUALIZE TOP 5 FAQs CÓ NHIỀU STEPS NHẤT
// ----------------------------------------------------------------------------

// Bước 1: Tìm top 5 FAQs
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WITH faq, p, count(s) as num_steps
WHERE num_steps >= 5
RETURN faq.id, substring(faq.question, 0, 60) as question, num_steps
ORDER BY num_steps DESC
LIMIT 5;

// Bước 2: Visualize từng FAQ (thay FAQ_ID)
// FAQ #1
MATCH path = (faq:FAQ {id: "FAQ_0"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain;

// FAQ #2
MATCH path = (faq:FAQ {id: "FAQ_6"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain;


// ----------------------------------------------------------------------------
// 9. VISUALIZE STEP CHAIN CHO MỘT FAQ CỤ THỂ
// ----------------------------------------------------------------------------

// Chỉ show step chain (không show FAQ và Process nodes)
MATCH (faq:FAQ {id: "FAQ_226"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(first:Step)
WHERE NOT ()-[:NEXT_STEP]->(first)  // First step
MATCH path = (first)-[:NEXT_STEP*0..]->(s:Step)
RETURN path;


// ----------------------------------------------------------------------------
// 10. INTERACTIVE QUERY - TÌM FAQ THEO KEYWORD VÀ VISUALIZE
// ----------------------------------------------------------------------------

// Bước 1: Search FAQs
MATCH (faq:FAQ)
WHERE toLower(faq.question) CONTAINS "mua vé máy bay"
  AND faq.answer CONTAINS "Bước"
RETURN faq.id, faq.question;

// Bước 2: Lấy ID từ kết quả trên và visualize
// (Thay "FAQ_XXX" bằng ID tìm được)
MATCH path = (faq:FAQ {id: "FAQ_XXX"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain;


// ----------------------------------------------------------------------------
// 11. SO SÁNH 2 FAQs TƯƠNG TỰ
// ----------------------------------------------------------------------------

// Visualize 2 FAQs về chuyển tiền cạnh nhau
MATCH path = (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE faq.id IN ["FAQ_19", "FAQ_226"]
OPTIONAL MATCH chain = (s)-[:NEXT_STEP]->(next:Step)
RETURN path, chain;


// ----------------------------------------------------------------------------
// 12. SHOW FULL GRAPH: FAQ + TOPICS + PROCESS + STEPS
// ----------------------------------------------------------------------------

// Visualize FAQ với tất cả relationships
MATCH (faq:FAQ {id: "FAQ_226"})
OPTIONAL MATCH path1 = (faq)-[:HAS_TOPIC]->(t:Topic)
OPTIONAL MATCH path2 = (faq)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH path3 = (s)-[:NEXT_STEP]->(next:Step)
RETURN faq, path1, path2, path3;


// ----------------------------------------------------------------------------
// 13. TÌM STEP CỤ THỂ TRONG TẤT CẢ FAQs
// ----------------------------------------------------------------------------

// Tìm tất cả steps có chứa "Nhập OTP"
MATCH (s:Step)
WHERE s.text CONTAINS "Nhập OTP"
RETURN s.process_id, s.number, s.text
LIMIT 10;

// Visualize FAQs có step "Nhập OTP"
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WHERE s.text CONTAINS "Nhập OTP"
WITH faq
LIMIT 3
MATCH path = (faq)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(step:Step)
OPTIONAL MATCH chain = (step)-[:NEXT_STEP]->(next:Step)
RETURN path, chain;


// ----------------------------------------------------------------------------
// 14. GENERIC QUERY - TÌM BẤT KỲ FAQ CÓ STEPS
// ----------------------------------------------------------------------------

// Lấy random 1 FAQ có steps
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
WITH faq, count(s) as num_steps
WHERE num_steps >= 3
RETURN faq.id, faq.question, num_steps
ORDER BY rand()
LIMIT 1;

// Sau đó visualize FAQ đó (copy faq.id vào đây)
MATCH path = (faq:FAQ {id: "COPY_FAQ_ID_HERE"})-[:DESCRIBES_PROCESS]->(p:Process)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH chain = (s)-[:NEXT_STEP*]->(next:Step)
RETURN path, chain;


// ============================================================================
// BONUS: QUERIES CHO DEBUGGING
// ============================================================================

// Check xem Process nào có nhiều FAQs nhất
MATCH (faq:FAQ)-[:DESCRIBES_PROCESS]->(p:Process)
WITH p.name as process_type, count(faq) as num_faqs
RETURN process_type, num_faqs
ORDER BY num_faqs DESC;

// Check xem có Step nào bị missing NEXT_STEP không
MATCH (p:Process)-[:HAS_STEP]->(s:Step)
WITH p, max(s.number) as max_step
MATCH (p)-[:HAS_STEP]->(s:Step)
WHERE s.number < max_step AND NOT (s)-[:NEXT_STEP]->()
RETURN p.id, s.number, s.text
LIMIT 10;

// Count steps per process
MATCH (p:Process)-[:HAS_STEP]->(s:Step)
RETURN p.name, p.id, count(s) as num_steps
ORDER BY num_steps DESC
LIMIT 20;


// ============================================================================
// HƯỚNG DẪN SỬ DỤNG:
// ============================================================================
//
// 1. Copy query vào Neo4j Browser (http://localhost:7474)
// 2. Click biểu tượng "Play" hoặc nhấn Ctrl+Enter
// 3. Xem visualization graph hoặc table results
// 4. Click vào nodes/relationships để xem properties
// 5. Zoom in/out bằng scroll wheel
// 6. Drag nodes để sắp xếp graph
//
// Tips:
// - Bắt đầu với queries đơn giản (section 1-5)
// - LIMIT để tránh query quá nhiều nodes
// - Dùng OPTIONAL MATCH khi không chắc relationship tồn tại
// - Visualize từng FAQ một để dễ quan sát
//
// ============================================================================
