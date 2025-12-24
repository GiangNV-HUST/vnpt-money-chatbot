# -*- coding: utf-8 -*-
"""
Export entire Neo4j database to output files
Supports multiple output formats: JSON, CSV, and TXT
"""

import json
import csv
import sys
from datetime import datetime
from pathlib import Path
from neo4j_connector import Neo4jConnector

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Create output directory
OUTPUT_DIR = Path("database_exports")
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for filenames
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

def export_to_json(connector):
    """Export all nodes and relationships to JSON format"""
    print("\n" + "=" * 60)
    print("EXPORTING TO JSON FORMAT")
    print("=" * 60)

    export_data = {
        "export_time": datetime.now().isoformat(),
        "nodes": {},
        "relationships": []
    }

    # Get all node labels
    labels_query = """
    CALL db.labels() YIELD label
    RETURN label
    """
    labels = connector.execute_query(labels_query)

    # Export nodes by label
    for label_record in labels:
        label = label_record['label']
        print(f"Exporting nodes with label: {label}")

        nodes_query = f"""
        MATCH (n:{label})
        RETURN elementId(n) as id, properties(n) as properties
        """
        nodes = connector.execute_query(nodes_query)

        export_data["nodes"][label] = [
            {
                "id": node["id"],
                "properties": node["properties"]
            }
            for node in nodes
        ]
        print(f"  ✓ Exported {len(nodes)} {label} nodes")

    # Export all relationships
    print(f"\nExporting relationships...")
    rels_query = """
    MATCH (a)-[r]->(b)
    RETURN elementId(a) as from_id, labels(a) as from_labels,
           elementId(b) as to_id, labels(b) as to_labels,
           type(r) as rel_type, properties(r) as properties
    """
    relationships = connector.execute_query(rels_query)

    export_data["relationships"] = [
        {
            "from": {
                "id": rel["from_id"],
                "labels": rel["from_labels"]
            },
            "to": {
                "id": rel["to_id"],
                "labels": rel["to_labels"]
            },
            "type": rel["rel_type"],
            "properties": rel["properties"]
        }
        for rel in relationships
    ]
    print(f"  ✓ Exported {len(relationships)} relationships")

    # Save to file
    json_file = OUTPUT_DIR / f"neo4j_export_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSON export saved to: {json_file}")
    return json_file


def export_nodes_to_csv(connector):
    """Export all nodes to CSV files (one file per label)"""
    print("\n" + "=" * 60)
    print("EXPORTING NODES TO CSV FORMAT")
    print("=" * 60)

    csv_files = []

    # Get all node labels
    labels_query = """
    CALL db.labels() YIELD label
    RETURN label
    """
    labels = connector.execute_query(labels_query)

    for label_record in labels:
        label = label_record['label']
        print(f"Exporting {label} nodes to CSV...")

        # Get all nodes with this label
        nodes_query = f"""
        MATCH (n:{label})
        RETURN n
        """
        nodes = connector.execute_query(nodes_query)

        if nodes:
            # Get all unique property keys for this label
            all_keys = set()
            for node in nodes:
                all_keys.update(node['n'].keys())

            # Sort keys for consistent column order
            fieldnames = sorted(all_keys)

            # Write to CSV
            csv_file = OUTPUT_DIR / f"nodes_{label}_{timestamp}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for node in nodes:
                    writer.writerow(node['n'])

            csv_files.append(csv_file)
            print(f"  ✓ Exported {len(nodes)} nodes to {csv_file.name}")

    print(f"\n✅ CSV exports saved to: {OUTPUT_DIR}")
    return csv_files


def export_relationships_to_csv(connector):
    """Export all relationships to CSV file"""
    print("\n" + "=" * 60)
    print("EXPORTING RELATIONSHIPS TO CSV FORMAT")
    print("=" * 60)

    rels_query = """
    MATCH (a)-[r]->(b)
    RETURN
        elementId(a) as from_id,
        labels(a)[0] as from_label,
        properties(a) as from_properties,
        type(r) as relationship_type,
        properties(r) as rel_properties,
        elementId(b) as to_id,
        labels(b)[0] as to_label,
        properties(b) as to_properties
    """
    relationships = connector.execute_query(rels_query)

    if relationships:
        csv_file = OUTPUT_DIR / f"relationships_{timestamp}.csv"

        fieldnames = [
            'from_id', 'from_label', 'from_properties',
            'relationship_type', 'rel_properties',
            'to_id', 'to_label', 'to_properties'
        ]

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rel in relationships:
                # Convert properties to JSON strings for CSV
                rel['from_properties'] = json.dumps(rel['from_properties'], ensure_ascii=False)
                rel['rel_properties'] = json.dumps(rel['rel_properties'], ensure_ascii=False)
                rel['to_properties'] = json.dumps(rel['to_properties'], ensure_ascii=False)
                writer.writerow(rel)

        print(f"  ✓ Exported {len(relationships)} relationships")
        print(f"\n✅ Relationships CSV saved to: {csv_file}")
        return csv_file

    return None


def export_to_readable_text(connector):
    """Export database to human-readable text format"""
    print("\n" + "=" * 60)
    print("EXPORTING TO READABLE TEXT FORMAT")
    print("=" * 60)

    txt_file = OUTPUT_DIR / f"neo4j_readable_{timestamp}.txt"

    with open(txt_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("NEO4J DATABASE EXPORT\n")
        f.write(f"Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Statistics
        stats = connector.get_statistics()
        f.write("DATABASE STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Nodes: {stats['total_nodes']}\n")
        f.write(f"Total Relationships: {stats['total_relationships']}\n\n")

        if stats.get('nodes_by_label'):
            f.write("Nodes by Label:\n")
            for label, count in stats['nodes_by_label'].items():
                f.write(f"  - {label}: {count}\n")
            f.write("\n")

        if stats.get('relationships_by_type'):
            f.write("Relationships by Type:\n")
            for rel_type, count in stats['relationships_by_type'].items():
                f.write(f"  - {rel_type}: {count}\n")
            f.write("\n")

        # Export nodes by label
        labels_query = "CALL db.labels() YIELD label RETURN label"
        labels = connector.execute_query(labels_query)

        for label_record in labels:
            label = label_record['label']

            f.write("=" * 80 + "\n")
            f.write(f"NODES: {label}\n")
            f.write("=" * 80 + "\n\n")

            nodes_query = f"""
            MATCH (n:{label})
            RETURN n
            LIMIT 1000
            """
            nodes = connector.execute_query(nodes_query)

            for i, node_record in enumerate(nodes, 1):
                node = node_record['n']
                f.write(f"[{i}] {label} Node:\n")
                for key, value in node.items():
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 200:
                        value = value[:200] + "..."
                    f.write(f"  {key}: {value}\n")
                f.write("\n")

        # Export relationships
        f.write("=" * 80 + "\n")
        f.write("RELATIONSHIPS\n")
        f.write("=" * 80 + "\n\n")

        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN
            labels(a)[0] as from_label,
            properties(a) as from_props,
            type(r) as rel_type,
            labels(b)[0] as to_label,
            properties(b) as to_props
        LIMIT 1000
        """
        relationships = connector.execute_query(rels_query)

        for i, rel in enumerate(relationships, 1):
            from_name = rel['from_props'].get('name') or rel['from_props'].get('id') or 'unnamed'
            to_name = rel['to_props'].get('name') or rel['to_props'].get('id') or 'unnamed'

            f.write(f"[{i}] ({rel['from_label']}: {from_name}) ")
            f.write(f"-[{rel['rel_type']}]-> ")
            f.write(f"({rel['to_label']}: {to_name})\n")

    print(f"✅ Readable text export saved to: {txt_file}")
    return txt_file


def export_cypher_queries(connector):
    """Export database as Cypher CREATE statements for recreation"""
    print("\n" + "=" * 60)
    print("EXPORTING AS CYPHER QUERIES")
    print("=" * 60)

    cypher_file = OUTPUT_DIR / f"neo4j_cypher_{timestamp}.cypher"

    with open(cypher_file, 'w', encoding='utf-8') as f:
        f.write("// Neo4j Database Export - Cypher Statements\n")
        f.write(f"// Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("// Run these statements to recreate the database\n\n")

        f.write("// Clear existing data (WARNING: This will delete everything!)\n")
        f.write("// MATCH (n) DETACH DELETE n;\n\n")

        # Export nodes
        labels_query = "CALL db.labels() YIELD label RETURN label"
        labels = connector.execute_query(labels_query)

        for label_record in labels:
            label = label_record['label']

            f.write(f"// Create {label} nodes\n")

            nodes_query = f"MATCH (n:{label}) RETURN properties(n) as props"
            nodes = connector.execute_query(nodes_query)

            for node in nodes:
                props = node['props']
                props_str = ", ".join([f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in props.items()])
                f.write(f"CREATE (:{label} {{{props_str}}});\n")

            f.write("\n")

        # Export relationships
        f.write("// Create relationships\n")
        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN
            labels(a)[0] as from_label,
            properties(a) as from_props,
            type(r) as rel_type,
            properties(r) as rel_props,
            labels(b)[0] as to_label,
            properties(b) as to_props
        """
        relationships = connector.execute_query(rels_query)

        for rel in relationships:
            # Create match pattern for nodes
            from_match = _create_match_pattern(rel['from_label'], rel['from_props'])
            to_match = _create_match_pattern(rel['to_label'], rel['to_props'])

            rel_props_str = ""
            if rel['rel_props']:
                props = ", ".join([f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in rel['rel_props'].items()])
                rel_props_str = f" {{{props}}}"

            f.write(f"MATCH {from_match}, {to_match}\n")
            f.write(f"MERGE (a)-[:{rel['rel_type']}{rel_props_str}]->(b);\n\n")

    print(f"✅ Cypher export saved to: {cypher_file}")
    return cypher_file


def _create_match_pattern(label, props):
    """Helper to create MATCH pattern from node properties"""
    # Use id or name as unique identifier
    if 'id' in props:
        return f"(a:{label} {{id: {json.dumps(props['id'], ensure_ascii=False)}}})"
    elif 'name' in props:
        return f"(a:{label} {{name: {json.dumps(props['name'], ensure_ascii=False)}}})"
    else:
        # Use first property as identifier
        key = list(props.keys())[0]
        return f"(a:{label} {{{key}: {json.dumps(props[key], ensure_ascii=False)}}})"


def main():
    """Main export function"""
    print("=" * 60)
    print("NEO4J DATABASE EXPORT TOOL")
    print("=" * 60)

    # Connect to Neo4j
    connector = Neo4jConnector()

    try:
        # Get statistics first
        stats = connector.get_statistics()
        print(f"\nDatabase contains:")
        print(f"  - {stats['total_nodes']} nodes")
        print(f"  - {stats['total_relationships']} relationships")

        # Export in all formats
        json_file = export_to_json(connector)
        csv_files = export_nodes_to_csv(connector)
        rel_csv = export_relationships_to_csv(connector)
        txt_file = export_to_readable_text(connector)
        cypher_file = export_cypher_queries(connector)

        # Summary
        print("\n" + "=" * 60)
        print("EXPORT COMPLETE!")
        print("=" * 60)
        print(f"\nAll exports saved to: {OUTPUT_DIR.absolute()}")
        print("\nGenerated files:")
        print(f"  1. JSON format: {json_file.name}")
        print(f"  2. CSV nodes: {len(csv_files)} files")
        if rel_csv:
            print(f"  3. CSV relationships: {rel_csv.name}")
        print(f"  4. Readable text: {txt_file.name}")
        print(f"  5. Cypher queries: {cypher_file.name}")

    finally:
        connector.close()


if __name__ == "__main__":
    main()
