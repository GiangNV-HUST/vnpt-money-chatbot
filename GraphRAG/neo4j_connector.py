"""
Neo4j Connector for VNPT Money Knowledge Graph
Handles connection, schema creation, and basic operations
"""

import logging
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Connector for Neo4j Graph Database
    Manages connection, schema, and CRUD operations
    """

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        Initialize Neo4j connection

        Args:
            uri: Neo4j URI (default from config)
            user: Username (default from config)
            password: Password (default from config)
            database: Database name (default from config)
        """
        self.uri = uri or config.NEO4J_URI
        self.user = user or config.NEO4J_USER
        self.password = password or config.NEO4J_PASSWORD
        self.database = database or config.NEO4J_DATABASE

        self.driver: Optional[Driver] = None
        self._connect()

    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            logger.info(f"Connecting to Neo4j at {self.uri}...")
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            self.driver.verify_connectivity()
            logger.info("✅ Connected to Neo4j successfully")

        except AuthError as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise

        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j service unavailable: {e}")
            logger.error("Please ensure Neo4j is running at " + self.uri)
            raise

        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def execute_query(
        self,
        query: str,
        parameters: Dict = None,
        write: bool = False
    ) -> List[Dict]:
        """
        Execute Cypher query

        Args:
            query: Cypher query string
            parameters: Query parameters
            write: True for write transactions, False for read

        Returns:
            List of result records
        """
        if parameters is None:
            parameters = {}

        try:
            with self.driver.session(database=self.database) as session:
                if write:
                    result = session.execute_write(
                        lambda tx: list(tx.run(query, parameters))
                    )
                else:
                    result = session.execute_read(
                        lambda tx: list(tx.run(query, parameters))
                    )

                # Convert to list of dicts
                return [record.data() for record in result]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise

    def create_schema(self):
        """
        Create indexes and constraints for better performance
        """
        logger.info("Creating Neo4j schema...")

        # Constraints (unique identifiers)
        constraints = [
            "CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE",
            "CREATE CONSTRAINT answer_id IF NOT EXISTS FOR (a:Answer) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT section_name IF NOT EXISTS FOR (s:Section) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT bank_name IF NOT EXISTS FOR (b:Bank) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT error_name IF NOT EXISTS FOR (e:Error) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT action_name IF NOT EXISTS FOR (a:Action) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT feature_name IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE",
        ]

        # Indexes (for faster queries)
        indexes = [
            "CREATE INDEX question_text IF NOT EXISTS FOR (q:Question) ON (q.text)",
            "CREATE INDEX answer_text IF NOT EXISTS FOR (a:Answer) ON (a.text)",
            "CREATE INDEX error_category IF NOT EXISTS FOR (e:Error) ON (e.category)",
            "CREATE INDEX action_category IF NOT EXISTS FOR (a:Action) ON (a.category)",
        ]

        # Execute schema creation
        for constraint in constraints:
            try:
                self.execute_query(constraint, write=True)
                logger.info(f"✅ Created: {constraint[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ Constraint already exists or failed: {e}")

        for index in indexes:
            try:
                self.execute_query(index, write=True)
                logger.info(f"✅ Created: {index[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ Index already exists or failed: {e}")

        logger.info("Schema creation completed")

    def clear_database(self):
        """
        ⚠️ WARNING: Delete all nodes and relationships
        Use only for development/testing
        """
        logger.warning("⚠️ Clearing entire database...")

        query = """
        MATCH (n)
        DETACH DELETE n
        """

        self.execute_query(query, write=True)
        logger.info("✅ Database cleared")

    def get_statistics(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dictionary with node/relationship counts
        """
        stats = {}

        # Total nodes
        query = "MATCH (n) RETURN count(n) as count"
        result = self.execute_query(query)
        stats["total_nodes"] = result[0]["count"] if result else 0

        # Total relationships
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        result = self.execute_query(query)
        stats["total_relationships"] = result[0]["count"] if result else 0

        # Nodes by label
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        result = self.execute_query(query)
        stats["nodes_by_label"] = {r["label"]: r["count"] for r in result}

        # Relationships by type
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        result = self.execute_query(query)
        stats["relationships_by_type"] = {r["type"]: r["count"] for r in result}

        return stats

    def create_node(
        self,
        label: str,
        properties: Dict,
        merge: bool = True
    ) -> str:
        """
        Create or merge a node

        Args:
            label: Node label (e.g., "Question", "Bank")
            properties: Node properties
            merge: If True, use MERGE (update if exists), else CREATE

        Returns:
            Node ID
        """
        # Extract id or use name for merge key
        merge_key = properties.get("id") or properties.get("name")

        if merge and merge_key:
            # Use MERGE to avoid duplicates
            if "id" in properties:
                query = f"""
                MERGE (n:{label} {{id: $merge_key}})
                SET n += $properties
                RETURN elementId(n) as node_id
                """
            else:
                query = f"""
                MERGE (n:{label} {{name: $merge_key}})
                SET n += $properties
                RETURN elementId(n) as node_id
                """

            result = self.execute_query(
                query,
                {"merge_key": merge_key, "properties": properties},
                write=True
            )
        else:
            # Create new node
            query = f"""
            CREATE (n:{label})
            SET n = $properties
            RETURN elementId(n) as node_id
            """

            result = self.execute_query(
                query,
                {"properties": properties},
                write=True
            )

        return result[0]["node_id"] if result else None

    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        rel_type: str,
        properties: Dict = None
    ):
        """
        Create relationship between nodes

        Args:
            from_node_id: Source node ID (can be node ID or unique property)
            to_node_id: Target node ID
            rel_type: Relationship type
            properties: Relationship properties
        """
        if properties is None:
            properties = {}

        query = f"""
        MATCH (from), (to)
        WHERE elementId(from) = $from_id AND elementId(to) = $to_id
        MERGE (from)-[r:{rel_type}]->(to)
        SET r += $properties
        """

        self.execute_query(
            query,
            {
                "from_id": from_node_id,
                "to_id": to_node_id,
                "properties": properties
            },
            write=True
        )

    def create_relationship_by_property(
        self,
        from_label: str,
        from_property: str,
        from_value: Any,
        to_label: str,
        to_property: str,
        to_value: Any,
        rel_type: str,
        properties: Dict = None
    ):
        """
        Create relationship by matching nodes with properties

        Args:
            from_label: Source node label
            from_property: Property to match on source
            from_value: Value to match
            to_label: Target node label
            to_property: Property to match on target
            to_value: Value to match
            rel_type: Relationship type
            properties: Relationship properties
        """
        if properties is None:
            properties = {}

        query = f"""
        MATCH (from:{from_label} {{{from_property}: $from_value}})
        MATCH (to:{to_label} {{{to_property}: $to_value}})
        MERGE (from)-[r:{rel_type}]->(to)
        SET r += $properties
        """

        self.execute_query(
            query,
            {
                "from_value": from_value,
                "to_value": to_value,
                "properties": properties
            },
            write=True
        )

    def batch_create_nodes(
        self,
        label: str,
        nodes: List[Dict],
        merge: bool = True
    ):
        """
        Batch create nodes for better performance

        Args:
            label: Node label
            nodes: List of node properties
            merge: If True, use MERGE
        """
        if merge:
            query = f"""
            UNWIND $nodes as node
            MERGE (n:{label} {{id: node.id}})
            SET n += node
            """
        else:
            query = f"""
            UNWIND $nodes as node
            CREATE (n:{label})
            SET n = node
            """

        self.execute_query(query, {"nodes": nodes}, write=True)
        logger.info(f"✅ Batch created {len(nodes)} {label} nodes")


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test connection
    connector = Neo4jConnector()

    # Create schema
    connector.create_schema()

    # Get statistics
    stats = connector.get_statistics()
    print("\n" + "=" * 60)
    print("NEO4J DATABASE STATISTICS")
    print("=" * 60)
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"Total Relationships: {stats['total_relationships']}")

    if stats.get('nodes_by_label'):
        print("\nNodes by Label:")
        for label, count in stats['nodes_by_label'].items():
            print(f"  {label}: {count}")

    if stats.get('relationships_by_type'):
        print("\nRelationships by Type:")
        for rel_type, count in stats['relationships_by_type'].items():
            print(f"  {rel_type}: {count}")

    # Close connection
    connector.close()
