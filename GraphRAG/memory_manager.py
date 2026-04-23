"""
Memory Manager - Wrapper cho Mem0
Quản lý conversation memory với semantic search và fact extraction
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Mem0
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
    logger.info("Mem0 available - using Mem0 for memory management")
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 not available. Install with: pip install mem0ai")

import config


class MemoryManager:
    """
    Memory Manager using Mem0 for intelligent conversation memory

    Features:
    - Semantic memory search
    - Automatic fact extraction
    - Memory deduplication (ADD/UPDATE/DELETE/NOOP)
    - Support for user/session scopes
    """

    def __init__(self,
                 use_cloud: bool = None,
                 api_key: str = None,
                 config_override: Dict = None):
        """
        Initialize Memory Manager

        Args:
            use_cloud: Use Mem0 Cloud (True) or local (False). Default from config.
            api_key: Mem0 API key for cloud mode
            config_override: Override Mem0 configuration
        """
        self.use_cloud = use_cloud if use_cloud is not None else getattr(config, 'MEM0_USE_CLOUD', False)
        self.api_key = api_key or getattr(config, 'MEM0_API_KEY', '')
        self.memory = None
        self.fallback_memory = {}  # Simple dict fallback if Mem0 not available

        if MEM0_AVAILABLE:
            self._initialize_mem0(config_override)
        else:
            logger.warning("Using fallback in-memory storage (no semantic search)")

    def _initialize_mem0(self, config_override: Dict = None):
        """Initialize Mem0 with configuration"""
        try:
            if self.use_cloud and self.api_key:
                # Cloud mode
                from mem0 import MemoryClient
                self.memory = MemoryClient(api_key=self.api_key)
                self.is_cloud = True
                logger.info("Mem0 Cloud initialized")
            else:
                # Local mode with custom config
                mem0_config = config_override or self._get_default_config()
                self.memory = Memory.from_config(mem0_config)
                self.is_cloud = False
                logger.info("Mem0 Local initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.memory = None

    def _get_default_config(self) -> Dict:
        """Get default Mem0 configuration for local mode"""
        return {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": getattr(config, 'LLM_MODEL', 'gpt-4o-mini'),
                    "temperature": 0.1,
                    "api_key": config.OPENAI_API_KEY
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": config.OPENAI_API_KEY
                }
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "vnpt_money_memories",
                    "path": str(config.DATA_DIR / "mem0_chroma")
                }
            },
            "version": "v1.1"
        }

    def add(self,
            messages: List[Dict[str, str]],
            user_id: str = "default",
            session_id: str = None,
            metadata: Dict = None) -> Dict:
        """
        Add conversation to memory

        Args:
            messages: List of messages in OpenAI format
                      [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            user_id: User identifier
            session_id: Session identifier (optional)
            metadata: Additional metadata to store

        Returns:
            Result dict with status and extracted memories
        """
        if not messages:
            return {"status": "error", "message": "No messages provided"}

        # Prepare metadata
        meta = metadata or {}
        meta["timestamp"] = datetime.now().isoformat()

        if self.memory and MEM0_AVAILABLE:
            try:
                # Add to Mem0
                result = self.memory.add(
                    messages=messages,
                    user_id=user_id,
                    metadata=meta
                )

                logger.info(f"Added to Mem0 for user {user_id}: {len(messages)} messages")
                logger.debug(f"Mem0 result: {result}")

                return {
                    "status": "success",
                    "memories": result.get("results", []) if isinstance(result, dict) else result,
                    "source": "mem0"
                }

            except Exception as e:
                logger.error(f"Mem0 add failed: {e}")
                # Fallback to simple storage
                return self._fallback_add(messages, user_id, meta)
        else:
            return self._fallback_add(messages, user_id, meta)

    def _fallback_add(self, messages: List[Dict], user_id: str, metadata: Dict) -> Dict:
        """Fallback: Simple in-memory storage"""
        if user_id not in self.fallback_memory:
            self.fallback_memory[user_id] = []

        # Extract simple facts
        facts = []
        for msg in messages:
            content = msg.get("content", "")
            if content:
                facts.append({
                    "role": msg.get("role"),
                    "content": content[:500],  # Truncate long content
                    "metadata": metadata
                })

        self.fallback_memory[user_id].extend(facts)

        # Keep only last 50 entries per user
        if len(self.fallback_memory[user_id]) > 50:
            self.fallback_memory[user_id] = self.fallback_memory[user_id][-50:]

        logger.info(f"Added to fallback memory for user {user_id}")
        return {"status": "success", "memories": facts, "source": "fallback"}

    def search(self,
               query: str,
               user_id: str = "default",
               limit: int = 5,
               threshold: float = 0.0) -> List[Dict]:
        """
        Search for relevant memories

        Args:
            query: Search query
            user_id: User identifier
            limit: Maximum results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of relevant memories with scores
        """
        if not query:
            return []

        if self.memory and MEM0_AVAILABLE:
            try:
                # Search in Mem0
                results = self.memory.search(
                    query=query,
                    user_id=user_id,
                    limit=limit
                )

                # Normalize results format
                memories = []
                result_list = results.get("results", []) if isinstance(results, dict) else results

                for item in result_list:
                    memory = {
                        "id": item.get("id", ""),
                        "memory": item.get("memory", ""),
                        "score": item.get("score", 0.0),
                        "metadata": item.get("metadata", {}),
                        "source": "mem0"
                    }

                    # Filter by threshold
                    if memory["score"] >= threshold:
                        memories.append(memory)

                logger.info(f"Mem0 search for '{query[:50]}...': found {len(memories)} memories")
                return memories

            except Exception as e:
                logger.error(f"Mem0 search failed: {e}")
                return self._fallback_search(query, user_id, limit)
        else:
            return self._fallback_search(query, user_id, limit)

    def _fallback_search(self, query: str, user_id: str, limit: int) -> List[Dict]:
        """Fallback: Simple keyword-based search"""
        if user_id not in self.fallback_memory:
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for item in self.fallback_memory[user_id]:
            content = item.get("content", "").lower()
            content_words = set(content.split())

            # Calculate simple overlap score
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                results.append({
                    "id": str(hash(content)),
                    "memory": item.get("content", ""),
                    "score": min(score, 1.0),
                    "metadata": item.get("metadata", {}),
                    "source": "fallback"
                })

        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_all(self, user_id: str = "default") -> List[Dict]:
        """
        Get all memories for a user

        Args:
            user_id: User identifier

        Returns:
            List of all memories
        """
        if self.memory and MEM0_AVAILABLE:
            try:
                results = self.memory.get_all(user_id=user_id)
                return results.get("results", []) if isinstance(results, dict) else results
            except Exception as e:
                logger.error(f"Mem0 get_all failed: {e}")
                return self.fallback_memory.get(user_id, [])
        else:
            return self.fallback_memory.get(user_id, [])

    def delete(self, memory_id: str, user_id: str = "default") -> bool:
        """
        Delete a specific memory

        Args:
            memory_id: Memory identifier
            user_id: User identifier

        Returns:
            True if deleted successfully
        """
        if self.memory and MEM0_AVAILABLE:
            try:
                self.memory.delete(memory_id=memory_id)
                logger.info(f"Deleted memory {memory_id}")
                return True
            except Exception as e:
                logger.error(f"Mem0 delete failed: {e}")
                return False
        return False

    def clear(self, user_id: str = "default") -> bool:
        """
        Clear all memories for a user

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        if self.memory and MEM0_AVAILABLE:
            try:
                # Get all memories and delete them
                all_memories = self.get_all(user_id)
                for mem in all_memories:
                    self.delete(mem.get("id"), user_id)
                logger.info(f"Cleared all memories for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Mem0 clear failed: {e}")

        # Clear fallback
        if user_id in self.fallback_memory:
            self.fallback_memory[user_id] = []
        return True

    def get_context_for_query(self,
                              query: str,
                              user_id: str = "default",
                              min_score: float = 0.5,
                              limit: int = 5) -> Dict:
        """
        Get relevant context for a query (high-level method)

        Args:
            query: User's current query
            user_id: User identifier
            min_score: Minimum relevance score
            limit: Maximum memories to return

        Returns:
            Dict with:
            - memories: List of relevant memories
            - has_context: True if relevant memories found
            - top_score: Highest relevance score
            - suggested_topic: Extracted topic from memories
        """
        memories = self.search(query, user_id, limit)

        # Filter by minimum score
        relevant = [m for m in memories if m.get("score", 0) >= min_score]

        # Extract topic from top memory
        suggested_topic = None
        if relevant:
            top_memory = relevant[0]
            metadata = top_memory.get("metadata", {})
            suggested_topic = metadata.get("topic") or metadata.get("faq_id")

        return {
            "memories": relevant,
            "has_context": len(relevant) > 0,
            "top_score": relevant[0]["score"] if relevant else 0.0,
            "suggested_topic": suggested_topic,
            "all_memories": memories  # Include all for debugging
        }

    def get_statistics(self, user_id: str = "default") -> Dict:
        """Get memory statistics for a user"""
        all_memories = self.get_all(user_id)

        return {
            "total_memories": len(all_memories),
            "user_id": user_id,
            "mem0_available": MEM0_AVAILABLE,
            "using_cloud": self.use_cloud if self.memory else False
        }


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Memory Manager")
    print("=" * 60)

    # Initialize
    manager = MemoryManager()
    user_id = "test_user"

    # Test 1: Add conversation
    print("\n1. Adding conversation...")
    result = manager.add(
        messages=[
            {"role": "user", "content": "Tôi chuyển tiền đến ngân hàng nhưng người nhận chưa nhận được"},
            {"role": "assistant", "content": "Bạn hãy kiểm tra trạng thái giao dịch. Có 2 trạng thái: Thành công hoặc Đang xử lý."}
        ],
        user_id=user_id,
        metadata={"topic": "chuyển tiền", "faq_id": "FAQ_61"}
    )
    print(f"   Result: {result['status']} (source: {result.get('source')})")

    # Test 2: Search
    print("\n2. Searching for related memory...")
    query = "nếu trạng thái đang xử lý thì thời gian bao lâu?"
    memories = manager.search(query, user_id, limit=3)
    print(f"   Query: {query}")
    print(f"   Found {len(memories)} memories:")
    for mem in memories:
        print(f"   - Score: {mem['score']:.2f} | {mem['memory'][:50]}...")

    # Test 3: Get context
    print("\n3. Getting context for query...")
    context = manager.get_context_for_query(query, user_id, min_score=0.3)
    print(f"   Has context: {context['has_context']}")
    print(f"   Top score: {context['top_score']:.2f}")
    print(f"   Suggested topic: {context['suggested_topic']}")

    # Test 4: Statistics
    print("\n4. Statistics...")
    stats = manager.get_statistics(user_id)
    print(f"   {stats}")

    print("\n" + "=" * 60)
    print("Testing complete!")
