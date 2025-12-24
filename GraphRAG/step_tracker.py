"""
Step Tracker for Multi-Step Processes
Extracts, tracks, and retrieves specific steps from FAQ answers
"""

import logging
import re
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StepTracker:
    """
    Tracks and manages multi-step processes from FAQ answers

    Features:
    - Extracts steps from answer text
    - Retrieves specific steps by number
    - Generates step-specific responses
    - Identifies step relationships from graph
    """

    def __init__(self):
        """Initialize StepTracker"""
        self.current_steps = []
        self.current_faq_id = None

    def extract_steps(self, answer: str, faq_id: Optional[str] = None) -> List[Dict]:
        """
        Extract steps from answer text

        Args:
            answer: FAQ answer text
            faq_id: FAQ identifier

        Returns:
            List of {step_number, step_text, step_title}
        """
        steps = []

        # Pattern 1: "Bước 1:", "Bước 2:", etc.
        step_pattern = r'Bước\s+(\d+):\s*(.+?)(?=Bước\s+\d+:|$)'
        matches = re.finditer(step_pattern, answer, re.IGNORECASE | re.DOTALL)

        for match in matches:
            step_num = int(match.group(1))
            step_full_text = match.group(2).strip()

            # Try to split into title and details
            # Pattern: "Action - Details" or just "Action"
            parts = step_full_text.split('\n', 1)
            step_title = parts[0].strip()
            step_details = parts[1].strip() if len(parts) > 1 else ""

            steps.append({
                "step_number": step_num,
                "step_text": step_full_text,
                "step_title": step_title,
                "step_details": step_details
            })

        if steps:
            logger.info(f"Extracted {len(steps)} steps from answer")

        self.current_steps = steps
        self.current_faq_id = faq_id

        return steps

    def get_step(self, step_number: int) -> Optional[Dict]:
        """
        Get specific step by number

        Args:
            step_number: Step number (1-based)

        Returns:
            Step dict or None
        """
        for step in self.current_steps:
            if step["step_number"] == step_number:
                return step
        return None

    def get_steps_from(self, start_step: int) -> List[Dict]:
        """
        Get all steps starting from a specific step number

        Args:
            start_step: Starting step number (1-based)

        Returns:
            List of steps
        """
        return [
            step for step in self.current_steps
            if step["step_number"] >= start_step
        ]

    def get_next_steps(self, current_step: int, count: int = 3) -> List[Dict]:
        """
        Get next N steps after current step

        Args:
            current_step: Current step number
            count: Number of steps to retrieve

        Returns:
            List of next steps
        """
        next_steps = []
        for step in self.current_steps:
            if step["step_number"] > current_step:
                next_steps.append(step)
                if len(next_steps) >= count:
                    break

        return next_steps

    def format_step_response(
        self,
        step: Dict,
        include_context: bool = True,
        total_steps: Optional[int] = None
    ) -> str:
        """
        Format a step into a user-friendly response

        Args:
            step: Step dictionary
            include_context: Whether to include progress context
            total_steps: Total number of steps (for progress indicator)

        Returns:
            Formatted response string
        """
        response_parts = []

        # Progress indicator
        if include_context and total_steps:
            response_parts.append(f"📍 Bước {step['step_number']}/{total_steps}")
        else:
            response_parts.append(f"📍 Bước {step['step_number']}:")

        # Step content
        response_parts.append(step['step_text'])

        return "\n".join(response_parts)

    def format_continuation_response(
        self,
        current_step: int,
        next_steps: Optional[List[Dict]] = None,
        include_all_remaining: bool = False
    ) -> str:
        """
        Format response for step continuation

        Args:
            current_step: Completed step number
            next_steps: List of next steps (will auto-retrieve if None)
            include_all_remaining: Whether to include all remaining steps

        Returns:
            Formatted response
        """
        if next_steps is None:
            if include_all_remaining:
                next_steps = self.get_steps_from(current_step + 1)
            else:
                next_steps = self.get_next_steps(current_step, count=3)

        if not next_steps:
            return "✅ Bạn đã hoàn thành tất cả các bước!"

        response_parts = []

        # CRITICAL FIX: Keep original step numbers instead of renumbering
        # User expects "Bước 3" after completing "Bước 2", not "Bước 1" again
        for step in next_steps:
            step_num = step["step_number"]
            step_text = step["step_text"]
            response_parts.append(f"Bước {step_num}: {step_text}")

        return "\n".join(response_parts)

    def has_steps(self) -> bool:
        """Check if steps are currently tracked"""
        return len(self.current_steps) > 0

    def get_total_steps(self) -> int:
        """Get total number of steps"""
        return len(self.current_steps)

    def clear(self):
        """Clear tracked steps"""
        self.current_steps = []
        self.current_faq_id = None


class StepExtractor:
    """
    Advanced step extractor with graph support

    Extracts steps from:
    1. FAQ answer text (regex-based)
    2. Neo4j graph (NEXT_STEP relationships)
    """

    def __init__(self, neo4j_connector=None):
        """
        Initialize StepExtractor

        Args:
            neo4j_connector: Optional Neo4j connector for graph-based extraction
        """
        self.connector = neo4j_connector

    def extract_from_answer(self, answer: str) -> List[Dict]:
        """Extract steps from answer text using regex"""
        tracker = StepTracker()
        return tracker.extract_steps(answer)

    def extract_from_graph(self, faq_id: str) -> List[Dict]:
        """
        Extract steps from Neo4j graph using NEXT_STEP relationships

        Args:
            faq_id: FAQ identifier

        Returns:
            List of steps in order
        """
        if not self.connector:
            logger.warning("No Neo4j connector available for graph extraction")
            return []

        # Query to get all actions with NEXT_STEP relationships
        cypher = """
        MATCH (f:FAQ {id: $faq_id})-[:SUGGESTS_ACTION]->(a:Action)
        OPTIONAL MATCH path = (a)-[:NEXT_STEP*]->(next:Action)
        WITH a, path, length(path) as step_order
        ORDER BY step_order
        RETURN DISTINCT a.name as action_name, step_order
        ORDER BY step_order
        """

        try:
            results = self.connector.execute_query(cypher, {"faq_id": faq_id})

            steps = []
            for i, result in enumerate(results, 1):
                steps.append({
                    "step_number": i,
                    "step_text": result["action_name"],
                    "step_title": result["action_name"],
                    "step_details": "",
                    "source": "graph"
                })

            if steps:
                logger.info(f"Extracted {len(steps)} steps from graph for FAQ {faq_id}")

            return steps

        except Exception as e:
            logger.error(f"Failed to extract steps from graph: {e}")
            return []

    def extract_hybrid(self, answer: str, faq_id: str) -> List[Dict]:
        """
        Extract steps using both text and graph

        Priority: Text-based (more detailed) > Graph-based

        Args:
            answer: FAQ answer text
            faq_id: FAQ identifier

        Returns:
            Combined list of steps
        """
        # Try text extraction first
        text_steps = self.extract_from_answer(answer)

        if text_steps:
            logger.info(f"Using {len(text_steps)} text-based steps")
            return text_steps

        # Fallback to graph extraction
        graph_steps = self.extract_from_graph(faq_id)

        if graph_steps:
            logger.info(f"Using {len(graph_steps)} graph-based steps (fallback)")
            return graph_steps

        logger.warning("No steps found in text or graph")
        return []


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test step extraction
    test_answer = """
    Để rút tiền từ ví VNPT Pay về tài khoản ngân hàng, bạn làm theo các bước sau:

    Bước 1: Tại giao diện chính, chọn mục "Rút tiền"

    Bước 2: Nhập số tiền cần rút và nhấn "Tiếp tục"

    Bước 3: Màn hình Xác nhận giao dịch và nhấn "Rút tiền"

    Bước 4: Màn hình nhập OTP để xác thực giao dịch

    Bước 5: Màn hình xác nhận giao dịch Rút tiền thành công

    Ngoài ra bạn có thể thực hiện tính năng Chuyển tiền để chuyển về tài khoản ngân hàng
    """

    print("=" * 60)
    print("Testing StepTracker")
    print("=" * 60)

    tracker = StepTracker()
    steps = tracker.extract_steps(test_answer, faq_id="FAQ_183")

    print(f"\nExtracted {len(steps)} steps:")
    for step in steps:
        print(f"\nStep {step['step_number']}:")
        print(f"  Title: {step['step_title']}")
        print(f"  Text: {step['step_text'][:80]}...")

    # Test get_step
    print("\n" + "=" * 60)
    print("Testing get_step(2):")
    print("=" * 60)
    step_2 = tracker.get_step(2)
    if step_2:
        print(f"\n{tracker.format_step_response(step_2, include_context=True, total_steps=5)}")

    # Test continuation response
    print("\n" + "=" * 60)
    print("Testing continuation response (completed step 1):")
    print("=" * 60)
    continuation = tracker.format_continuation_response(current_step=1, include_all_remaining=False)
    print(f"\n{continuation}")

    # Test get all remaining
    print("\n" + "=" * 60)
    print("Testing continuation response (completed step 1, show all remaining):")
    print("=" * 60)
    continuation_all = tracker.format_continuation_response(current_step=1, include_all_remaining=True)
    print(f"\n{continuation_all}")
