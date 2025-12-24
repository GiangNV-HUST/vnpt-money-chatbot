"""
Neo4j Knowledge Graph Builder for VNPT Money Chatbot (LLM-based)
Builds graph in Neo4j from documents using LLM for entity and relationship extraction
"""

import json
import logging
from typing import Dict, List
from tqdm import tqdm
import time

from neo4j_connector import Neo4jConnector
from llm_entity_extractor import LLMEntityExtractor
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jKnowledgeGraphBuilderLLM:
    """Build Knowledge Graph in Neo4j using LLM for entity extraction"""

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize builder with Neo4j connection

        Args:
            use_embeddings: Whether to generate embeddings for semantic similarity
        """
        self.connector = Neo4jConnector()
        self.entity_extractor = LLMEntityExtractor()
        self.embeddings_model = None
        self.use_embeddings = use_embeddings

        # Initialize embeddings if needed
        if use_embeddings and config.EMBEDDING_MODEL:
            self._initialize_embeddings()

        # Create schema
        self.connector.create_schema()

        logger.info("Initialized Neo4j Knowledge Graph Builder (LLM-based)")

    def _initialize_embeddings(self):
        """Initialize sentence embeddings model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embeddings_model = SentenceTransformer(config.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning(f"Failed to load embeddings model: {e}")
            self.use_embeddings = False

    def build_graph_from_documents(self, documents_path: str, limit: int = None):
        """
        Build knowledge graph from JSON documents using LLM

        Args:
            documents_path: Path to paraphrase_documents.json
            limit: Maximum number of documents to process (for testing)
        """
        logger.info(f"Loading documents from: {documents_path}")

        # Load documents
        with open(documents_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        if limit:
            documents = documents[:limit]
            logger.info(f"Processing first {limit} documents (test mode)")

        logger.info(f"Loaded {len(documents)} documents")

        # Process each document
        processed_count = 0
        failed_count = 0

        for i, doc in enumerate(tqdm(documents, desc="Building Neo4j graph with LLM")):
            try:
                self._process_document(doc, doc_index=i)
                processed_count += 1

                # Add delay to avoid rate limiting
                if (i + 1) % 10 == 0:
                    time.sleep(1)  # Sleep 1 second every 10 requests

            except Exception as e:
                logger.error(f"Failed to process document {i}: {e}")
                failed_count += 1

        logger.info(f"✅ Processed {processed_count} documents, {failed_count} failed")

        # Add similarity edges if embeddings enabled
        if self.use_embeddings:
            self._add_similarity_edges()

        # Get statistics
        stats = self.connector.get_statistics()
        logger.info(f"✅ Graph built: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")

    def _process_document(self, doc: Dict, doc_index: int):
        """
        Process a single document and add to Neo4j using LLM extraction

        Args:
            doc: Document dictionary
            doc_index: Index of document
        """
        metadata = doc.get("metadata", {})
        question = metadata.get("question", "")
        answer = metadata.get("answer", "")
        section = metadata.get("section", "")

        if not question or not answer:
            return

        # Extract entities and relationships using LLM
        extraction = self.entity_extractor.extract_entities_and_relationships(
            question, answer, section
        )

        entities = extraction.get("entities", {})
        relationships = extraction.get("relationships", [])

        # Create FAQ node (combines Question + Answer)
        faq_id = self._add_faq_node(question, answer, metadata, doc_index)

        # Create Section node and relationship
        if section:
            self._get_or_create_section_node(section)
            self._add_relationship_by_property(
                "FAQ", "id", faq_id,
                "Section", "name", section,
                "BELONGS_TO", {}
            )

        # Create entity nodes
        for entity_type, entity_list in entities.items():
            for entity_name in entity_list:
                if entity_name:
                    self._get_or_create_entity_node(entity_type, entity_name)

        # Create relationships
        for rel in relationships:
            self._create_relationship_from_extraction(faq_id, rel, entities)

    def _add_faq_node(self, question: str, answer: str, metadata: Dict, doc_index: int) -> str:
        """
        Add FAQ node to Neo4j (combines Question + Answer in one node)

        Args:
            question: Question text
            answer: Answer text
            metadata: Metadata dictionary
            doc_index: Document index

        Returns:
            FAQ node ID
        """
        node_id = f"FAQ_{doc_index}"

        # Compute embedding for question
        embedding = None
        if self.embeddings_model:
            try:
                embedding = self.embeddings_model.encode(question).tolist()
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")

        properties = {
            "id": node_id,
            "question": question,
            "answer": answer,
            "keywords": metadata.get("question", ""),
            "source": metadata.get("source", ""),
            "sheet_name": metadata.get("sheet_name", ""),
        }

        # Store embedding
        if embedding:
            properties["embedding"] = embedding

        self.connector.create_node("FAQ", properties, merge=True)
        return node_id

    def _get_or_create_section_node(self, section_name: str) -> str:
        """Get existing or create new Section node"""
        properties = {
            "name": section_name,
            "description": f"Chủ đề về {section_name}"
        }

        self.connector.create_node("Section", properties, merge=True)
        return section_name

    def _get_or_create_entity_node(self, entity_type: str, entity_name: str) -> str:
        """
        Get existing or create new entity node

        Args:
            entity_type: Type of entity (Topic, Service, Bank, Error, etc.)
            entity_name: Name of the entity

        Returns:
            Entity name (used as ID)
        """
        properties = {
            "name": entity_name
        }

        # Add type-specific properties
        if entity_type == "Error":
            properties["severity"] = "medium"
        elif entity_type == "Action":
            properties["category"] = self._get_action_category(entity_name)

        self.connector.create_node(entity_type, properties, merge=True)
        return entity_name

    def _get_action_category(self, action_name: str) -> str:
        """Classify action into category"""
        action_lower = action_name.lower()

        if any(word in action_lower for word in ["nạp", "rút", "chuyển"]):
            return "TRANSACTION"
        elif any(word in action_lower for word in ["liên kết", "hủy"]):
            return "LINKING"
        elif any(word in action_lower for word in ["kiểm tra", "tra cứu", "xem"]):
            return "INQUIRY"
        elif any(word in action_lower for word in ["đăng ký", "cập nhật", "thay đổi"]):
            return "ACCOUNT_MANAGEMENT"
        else:
            return "OTHER"

    def _create_relationship_from_extraction(
        self,
        faq_id: str,
        relationship: Dict,
        entities: Dict
    ):
        """
        Create relationship in Neo4j from LLM extraction

        Args:
            faq_id: FAQ node ID
            relationship: Relationship dictionary from LLM
            entities: Entities dictionary
        """
        from_node = relationship.get("from")
        relation_type = relationship.get("relation")
        to_node = relationship.get("to")
        to_type = relationship.get("to_type")

        if not all([from_node, relation_type, to_node, to_type]):
            return

        # Determine source node
        if from_node == "Question" or from_node == "Answer":
            from_label = "FAQ"
            from_property = "id"
            from_value = faq_id
        else:
            # from_node is an entity name
            from_label = self._find_entity_type(from_node, entities)
            if not from_label:
                return
            from_property = "name"
            from_value = from_node

        # Determine target node
        to_label = to_type
        to_property = "name"
        to_value = to_node

        # Create relationship
        try:
            self._add_relationship_by_property(
                from_label, from_property, from_value,
                to_label, to_property, to_value,
                relation_type, {}
            )
        except Exception as e:
            logger.debug(f"Failed to create relationship {relation_type}: {e}")

    def _find_entity_type(self, entity_name: str, entities: Dict) -> str:
        """Find entity type by name"""
        for entity_type, entity_list in entities.items():
            if entity_name in entity_list:
                return entity_type
        return None

    def _add_relationship_by_property(
        self,
        from_label: str,
        from_prop: str,
        from_value: str,
        to_label: str,
        to_prop: str,
        to_value: str,
        rel_type: str,
        properties: Dict
    ):
        """Add relationship by matching properties"""
        self.connector.create_relationship_by_property(
            from_label, from_prop, from_value,
            to_label, to_prop, to_value,
            rel_type, properties
        )

    def _add_similarity_edges(self):
        """Add SIMILAR_TO edges between similar FAQ questions"""
        if not self.embeddings_model:
            logger.warning("Skipping similarity edges (embeddings not available)")
            return

        logger.info("Computing FAQ similarities...")

        # Get all FAQs with embeddings
        query = """
        MATCH (f:FAQ)
        WHERE f.embedding IS NOT NULL
        RETURN f.id as id, f.embedding as embedding, f.question as question
        LIMIT 100
        """

        faqs = self.connector.execute_query(query)

        if len(faqs) < 2:
            logger.warning("Not enough FAQs with embeddings for similarity computation")
            return

        # Compute pairwise similarities
        import numpy as np

        similarity_count = 0

        for i, faq1 in enumerate(faqs):
            for faq2 in faqs[i+1:]:
                emb1 = np.array(faq1["embedding"])
                emb2 = np.array(faq2["embedding"])

                # Cosine similarity
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

                if similarity >= config.MIN_SIMILARITY_SCORE:
                    # Add bidirectional SIMILAR_TO edges
                    try:
                        self._add_relationship_by_property(
                            "FAQ", "id", faq1["id"],
                            "FAQ", "id", faq2["id"],
                            "SIMILAR_TO", {"similarity_score": float(similarity)}
                        )
                        self._add_relationship_by_property(
                            "FAQ", "id", faq2["id"],
                            "FAQ", "id", faq1["id"],
                            "SIMILAR_TO", {"similarity_score": float(similarity)}
                        )
                        similarity_count += 2
                    except:
                        pass

        logger.info(f"✅ Added {similarity_count} similarity edges")

    def close(self):
        """Close Neo4j connection"""
        self.connector.close()


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Knowledge Graph using LLM")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of documents to process")
    parser.add_argument("--no-embeddings", action="store_true", help="Disable embeddings")
    args = parser.parse_args()

    # Build graph from documents
    builder = Neo4jKnowledgeGraphBuilderLLM(use_embeddings=not args.no_embeddings)

    try:
        # Build graph
        builder.build_graph_from_documents(
            str(config.RAW_DATA_PATH),
            limit=args.limit
        )

        # Get statistics
        stats = builder.connector.get_statistics()
        print("\n" + "=" * 60)
        print("NEO4J GRAPH STATISTICS (LLM-based)")
        print("=" * 60)
        print(f"Total Nodes: {stats['total_nodes']}")
        print(f"Total Relationships: {stats['total_relationships']}")

        if stats.get('nodes_by_label'):
            print("\nNodes by Label:")
            for label, count in sorted(stats['nodes_by_label'].items()):
                print(f"  {label}: {count}")

        if stats.get('relationships_by_type'):
            print("\nRelationships by Type:")
            for rel_type, count in sorted(stats['relationships_by_type'].items()):
                print(f"  {rel_type}: {count}")

    finally:
        # Close connection
        builder.close()
