"""
Visualize Knowledge Graph Schema
Shows the structure of entities and relationships in the graph
"""

from neo4j_connector import Neo4jConnector
import config


def visualize_schema():
    """Visualize graph schema and statistics"""
    connector = Neo4jConnector()

    print("=" * 70)
    print("VNPT MONEY KNOWLEDGE GRAPH SCHEMA")
    print("=" * 70)

    # Get node statistics
    print("\n📦 NODE TYPES:\n")
    stats = connector.get_statistics()

    if stats.get('nodes_by_label'):
        nodes = sorted(stats['nodes_by_label'].items(), key=lambda x: x[1], reverse=True)
        for label, count in nodes:
            print(f"  ├─ {label:<20} : {count:>5} nodes")

    print(f"\n  Total Nodes: {stats['total_nodes']}")

    # Get relationship statistics
    print("\n🔗 RELATIONSHIP TYPES:\n")

    if stats.get('relationships_by_type'):
        rels = sorted(stats['relationships_by_type'].items(), key=lambda x: x[1], reverse=True)
        for rel_type, count in rels:
            print(f"  ├─ {rel_type:<25} : {count:>5} relationships")

    print(f"\n  Total Relationships: {stats['total_relationships']}")

    # Get sample relationships
    print("\n📊 RELATIONSHIP PATTERNS:\n")

    query = """
    MATCH (a)-[r]->(b)
    RETURN labels(a)[0] as from_type, type(r) as rel_type, labels(b)[0] as to_type, count(*) as count
    ORDER BY count DESC
    LIMIT 15
    """

    patterns = connector.execute_query(query)

    for pattern in patterns:
        from_type = pattern['from_type']
        rel_type = pattern['rel_type']
        to_type = pattern['to_type']
        count = pattern['count']

        print(f"  ({from_type}) -[{rel_type}]-> ({to_type}): {count} times")

    # Sample FAQs
    print("\n📝 SAMPLE FAQs:\n")

    query_faq = """
    MATCH (f:FAQ)
    RETURN f.question as question, f.id as id
    LIMIT 5
    """

    faqs = connector.execute_query(query_faq)

    for i, faq in enumerate(faqs, 1):
        print(f"  {i}. {faq['question'][:70]}...")

        # Get connected entities
        query_entities = f"""
        MATCH (f:FAQ {{id: '{faq['id']}'}})-[r]->(e)
        RETURN labels(e)[0] as entity_type, e.name as entity_name, type(r) as rel_type
        LIMIT 5
        """

        entities = connector.execute_query(query_entities)

        for entity in entities:
            print(f"     └─ [{entity['rel_type']}] -> {entity['entity_type']}: {entity['entity_name']}")
        print()

    # Topic analysis
    print("\n🏷️  TOP TOPICS:\n")

    query_topics = """
    MATCH (t:Topic)<-[:ABOUT]-(f:FAQ)
    RETURN t.name as topic, count(f) as faq_count
    ORDER BY faq_count DESC
    LIMIT 10
    """

    topics = connector.execute_query(query_topics)

    for topic in topics:
        print(f"  • {topic['topic']:<30} : {topic['faq_count']} FAQs")

    # Error analysis
    print("\n⚠️  TOP ERRORS:\n")

    query_errors = """
    MATCH (e:Error)<-[:DESCRIBES_ERROR]-(f:FAQ)
    RETURN e.name as error, count(f) as faq_count
    ORDER BY faq_count DESC
    LIMIT 10
    """

    errors = connector.execute_query(query_errors)

    if errors:
        for error in errors:
            print(f"  • {error['error'][:60]:<60} : {error['faq_count']} FAQs")
    else:
        print("  (No errors found)")

    # Action analysis
    print("\n🎯 TOP ACTIONS:\n")

    query_actions = """
    MATCH (a:Action)<-[:SUGGESTS_ACTION]-(f:FAQ)
    RETURN a.name as action, a.category as category, count(f) as faq_count
    ORDER BY faq_count DESC
    LIMIT 10
    """

    actions = connector.execute_query(query_actions)

    if actions:
        for action in actions:
            category = action.get('category', 'N/A')
            print(f"  • {action['action']:<30} [{category:<20}] : {action['faq_count']} FAQs")
    else:
        print("  (No actions found)")

    # Bank analysis
    print("\n🏦 BANKS MENTIONED:\n")

    query_banks = """
    MATCH (b:Bank)<-[:MENTIONS_BANK]-(f:FAQ)
    RETURN b.name as bank, count(f) as faq_count
    ORDER BY faq_count DESC
    """

    banks = connector.execute_query(query_banks)

    if banks:
        for bank in banks:
            print(f"  • {bank['bank']:<20} : {bank['faq_count']} FAQs")
    else:
        print("  (No banks found)")

    # Similar questions
    print("\n🔄 SIMILAR QUESTIONS (Sample):\n")

    query_similar = """
    MATCH (f1:FAQ)-[r:SIMILAR_TO]->(f2:FAQ)
    WHERE r.similarity_score > 0.8
    RETURN f1.question as q1, f2.question as q2, r.similarity_score as score
    ORDER BY score DESC
    LIMIT 3
    """

    similar = connector.execute_query(query_similar)

    if similar:
        for sim in similar:
            print(f"\n  Q1: {sim['q1'][:60]}...")
            print(f"  Q2: {sim['q2'][:60]}...")
            print(f"  Similarity: {sim['score']:.3f}")
    else:
        print("  (No similar questions found - embeddings may not be generated yet)")

    print("\n" + "=" * 70)

    connector.close()


def export_cypher_schema():
    """Export Cypher queries to visualize schema in Neo4j Browser"""

    queries = """
# ==================================================
# NEO4J BROWSER VISUALIZATION QUERIES
# ==================================================

# 1. Visualize entire schema (small sample)
MATCH (n)
RETURN n
LIMIT 100

# 2. Visualize FAQs and their connections
MATCH (f:FAQ)-[r]->(e)
RETURN f, r, e
LIMIT 50

# 3. Visualize a specific topic's graph
MATCH (f:FAQ)-[:ABOUT]->(t:Topic {name: 'Nạp tiền'})
MATCH (f)-[r]->(e)
RETURN f, r, e, t
LIMIT 30

# 4. Visualize error -> solution paths
MATCH (f:FAQ)-[:DESCRIBES_ERROR]->(err:Error)
MATCH (f)-[:SUGGESTS_ACTION]->(act:Action)
RETURN f, err, act
LIMIT 20

# 5. Visualize bank-related FAQs
MATCH (f:FAQ)-[:MENTIONS_BANK]->(b:Bank)
MATCH (f)-[r]->(e)
RETURN f, r, e, b
LIMIT 30

# 6. Visualize similar questions network
MATCH (f1:FAQ)-[r:SIMILAR_TO]-(f2:FAQ)
WHERE r.similarity_score > 0.75
RETURN f1, r, f2
LIMIT 20

# 7. Visualize action requirements
MATCH (f:FAQ)-[:SUGGESTS_ACTION]->(a:Action)
MATCH (a)-[:REQUIRES]->(req:Requirement)
RETURN f, a, req
LIMIT 20

# 8. Complete path: Question -> Error -> Action -> Feature
MATCH path = (f:FAQ)-[:DESCRIBES_ERROR]->(err:Error),
             (f)-[:SUGGESTS_ACTION]->(act:Action),
             (act)-[:USES_FEATURE]->(feat:Feature)
RETURN path
LIMIT 10
"""

    print("\n" + "=" * 70)
    print("CYPHER QUERIES FOR NEO4J BROWSER")
    print("=" * 70)
    print(queries)

    # Save to file
    with open("neo4j_visualization_queries.cypher", "w", encoding="utf-8") as f:
        f.write(queries)

    print("\n✅ Queries saved to: neo4j_visualization_queries.cypher")
    print("📌 Copy and paste these queries into Neo4j Browser to visualize the graph\n")


if __name__ == "__main__":
    print("\n🔍 Analyzing Knowledge Graph...\n")

    try:
        visualize_schema()
        export_cypher_schema()

        print("\n✅ Analysis complete!")
        print("\n💡 Tips:")
        print("  1. Open Neo4j Browser: http://localhost:7474")
        print("  2. Use the queries in neo4j_visualization_queries.cypher")
        print("  3. Explore the graph visually\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
