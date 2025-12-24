"""
Update Embeddings in Neo4j Database
This script updates ONLY the embeddings of existing FAQ nodes
without re-extracting entities or rebuilding the entire graph.

Usage:
    python update_embeddings.py
"""

import logging
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from neo4j_connector import Neo4jConnector
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_all_embeddings():
    """Update embeddings for all FAQ nodes in Neo4j"""

    logger.info("="*60)
    logger.info("UPDATING EMBEDDINGS IN NEO4J DATABASE")
    logger.info("="*60)

    # Initialize connector
    connector = Neo4jConnector()

    # Load new embedding model
    logger.info(f"Loading new embedding model: {config.EMBEDDING_MODEL}")
    try:
        embeddings_model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("✅ Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load embedding model: {e}")
        return

    # Get all FAQ nodes
    logger.info("Fetching all FAQ nodes from Neo4j...")
    cypher_get_faqs = """
    MATCH (f:FAQ)
    RETURN f.id as id, f.question as question
    ORDER BY f.id
    """

    faqs = connector.execute_query(cypher_get_faqs)
    total_faqs = len(faqs)
    logger.info(f"Found {total_faqs} FAQ nodes to update")

    if total_faqs == 0:
        logger.warning("No FAQ nodes found in database!")
        return

    # Update embeddings for each FAQ
    updated_count = 0
    failed_count = 0

    for faq in tqdm(faqs, desc="Updating embeddings"):
        try:
            faq_id = faq['id']
            question = faq['question']

            # Generate new embedding
            embedding = embeddings_model.encode(question).tolist()

            # Update in Neo4j
            cypher_update = """
            MATCH (f:FAQ {id: $id})
            SET f.embedding = $embedding
            RETURN f.id as id
            """

            result = connector.execute_query(
                cypher_update,
                {"id": faq_id, "embedding": embedding},
                write=True  # IMPORTANT: Enable write mode
            )

            if result:
                updated_count += 1
            else:
                logger.warning(f"Failed to update FAQ {faq_id}")
                failed_count += 1

        except Exception as e:
            logger.error(f"Error updating FAQ {faq.get('id', 'unknown')}: {e}")
            failed_count += 1

    logger.info("="*60)
    logger.info("EMBEDDING UPDATE COMPLETED")
    logger.info("="*60)
    logger.info(f"✅ Successfully updated: {updated_count}/{total_faqs} FAQs")
    if failed_count > 0:
        logger.warning(f"❌ Failed: {failed_count} FAQs")

    # Update similarity edges (optional)
    logger.info("\nDo you want to update similarity edges? (y/n)")
    response = input().strip().lower()

    if response == 'y':
        update_similarity_edges(connector, embeddings_model)

    # Close connection
    connector.close()
    logger.info("Database connection closed")


def update_similarity_edges(connector, embeddings_model):
    """
    Update SIMILAR_TO relationships between FAQ nodes
    based on new embeddings
    """
    logger.info("\n" + "="*60)
    logger.info("UPDATING SIMILARITY EDGES")
    logger.info("="*60)

    # First, delete old similarity edges
    logger.info("Deleting old SIMILAR_TO relationships...")
    cypher_delete = """
    MATCH ()-[r:SIMILAR_TO]->()
    DELETE r
    """
    connector.execute_query(cypher_delete, write=True)
    logger.info("✅ Old similarity edges deleted")

    # Get all FAQ embeddings
    logger.info("Fetching FAQ embeddings...")
    cypher_get_embeddings = """
    MATCH (f:FAQ)
    WHERE f.embedding IS NOT NULL
    RETURN f.id as id, f.embedding as embedding
    """

    faqs = connector.execute_query(cypher_get_embeddings)
    logger.info(f"Found {len(faqs)} FAQs with embeddings")

    # Compute similarities and create edges
    import numpy as np

    created_edges = 0

    for i, faq1 in enumerate(tqdm(faqs, desc="Computing similarities")):
        similarities = []

        for j, faq2 in enumerate(faqs):
            if i >= j:  # Skip self and already processed pairs
                continue

            # Compute cosine similarity
            emb1 = np.array(faq1['embedding'])
            emb2 = np.array(faq2['embedding'])

            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

            # Only create edge if similarity is high enough
            if similarity >= config.MIN_SIMILARITY_SCORE:
                similarities.append({
                    'faq1_id': faq1['id'],
                    'faq2_id': faq2['id'],
                    'similarity': float(similarity)
                })

        # Create edges in batch
        if similarities:
            cypher_create = """
            UNWIND $similarities as sim
            MATCH (f1:FAQ {id: sim.faq1_id})
            MATCH (f2:FAQ {id: sim.faq2_id})
            MERGE (f1)-[r:SIMILAR_TO]->(f2)
            SET r.similarity = sim.similarity
            """
            connector.execute_query(cypher_create, {"similarities": similarities}, write=True)
            created_edges += len(similarities)

    logger.info(f"✅ Created {created_edges} SIMILAR_TO relationships")
    logger.info(f"   (Threshold: {config.MIN_SIMILARITY_SCORE})")


if __name__ == "__main__":
    update_all_embeddings()
