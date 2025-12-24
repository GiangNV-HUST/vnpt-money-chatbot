"""
Main entry point for GraphRAG Chatbot
Provides CLI interface for building graph and running chatbot
"""

import argparse
import logging
import sys
from pathlib import Path

from graph_builder import KnowledgeGraphBuilder
from chatbot import GraphRAGChatbot, interactive_chat
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def build_graph(data_path: str = None, use_embeddings: bool = True):
    """
    Build knowledge graph from documents

    Args:
        data_path: Path to documents JSON file
        use_embeddings: Whether to compute embeddings
    """
    if data_path is None:
        data_path = str(config.RAW_DATA_PATH)

    if not Path(data_path).exists():
        logger.error(f"Data file not found: {data_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Building Knowledge Graph")
    logger.info("=" * 60)

    # Create builder
    builder = KnowledgeGraphBuilder(use_embeddings=use_embeddings)

    # Build graph
    graph = builder.build_graph_from_documents(data_path)

    # Get statistics
    stats = builder.get_graph_statistics()

    print("\n" + "=" * 60)
    print("GRAPH BUILDING COMPLETED")
    print("=" * 60)
    print(f"Total Nodes: {stats['num_nodes']}")
    print(f"Total Edges: {stats['num_edges']}")

    print("\nNodes by Type:")
    for node_type, count in sorted(stats['nodes_by_type'].items()):
        print(f"  {node_type:20s}: {count:5d}")

    print("\nEdges by Type:")
    for edge_type, count in sorted(stats['edges_by_type'].items()):
        print(f"  {edge_type:20s}: {count:5d}")

    # Save graph
    builder.save_graph()
    print(f"\nGraph saved to: {config.GRAPH_DB_PATH}")
    print("=" * 60)


def run_chatbot():
    """Run interactive chatbot"""
    logger.info("Starting GraphRAG Chatbot")

    # Check if graph exists
    if not Path(config.GRAPH_DB_PATH).exists():
        logger.error(f"Knowledge graph not found at: {config.GRAPH_DB_PATH}")
        logger.error("Please build the graph first using: python main.py build")
        sys.exit(1)

    # Run chatbot
    interactive_chat()


def test_chatbot(queries: list = None):
    """
    Test chatbot with predefined queries

    Args:
        queries: List of test queries
    """
    if queries is None:
        queries = [
            "Làm sao để nạp tiền từ ngân hàng vào VNPT Money?",
            "Tôi nạp tiền từ Vietinbank bị lỗi thì phải làm gì?",
            "Giao dịch nạp tiền thất bại nhưng ngân hàng đã trừ tiền",
            "Làm sao để xem lịch sử giao dịch?",
            "Có những cách nào để nạp tiền vào ví?"
        ]

    logger.info("Testing chatbot with predefined queries")

    chatbot = GraphRAGChatbot()

    print("\n" + "=" * 60)
    print("CHATBOT TESTING")
    print("=" * 60)

    for i, query in enumerate(queries, 1):
        print(f"\n[Test {i}/{len(queries)}]")
        print(f"Query: {query}")
        print("-" * 60)

        response = chatbot.chat(query)

        print(f"Response:\n{response}")
        print("=" * 60)

    # Print statistics
    stats = chatbot.get_chat_statistics()
    print(f"\nTest Statistics:")
    print(f"  Total queries: {stats['total_conversations']}")
    print(f"  LLM enabled: {stats['llm_enabled']}")
    print(f"  Cache hits: {stats['cache_size']}")


def show_stats():
    """Show graph statistics"""
    if not Path(config.GRAPH_DB_PATH).exists():
        logger.error(f"Knowledge graph not found at: {config.GRAPH_DB_PATH}")
        logger.error("Please build the graph first using: python main.py build")
        sys.exit(1)

    from graph_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder()
    builder.load_graph()

    stats = builder.get_graph_statistics()

    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("=" * 60)
    print(f"Graph file: {config.GRAPH_DB_PATH}")
    print(f"\nTotal Nodes: {stats['num_nodes']}")
    print(f"Total Edges: {stats['num_edges']}")

    print("\nNodes by Type:")
    for node_type, count in sorted(stats['nodes_by_type'].items()):
        print(f"  {node_type:20s}: {count:5d}")

    print("\nEdges by Type:")
    for edge_type, count in sorted(stats['edges_by_type'].items()):
        print(f"  {edge_type:20s}: {count:5d}")
    print("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="VNPT Money GraphRAG Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build knowledge graph from data
  python main.py build

  # Build graph without embeddings (faster)
  python main.py build --no-embeddings

  # Build graph from custom data file
  python main.py build --data path/to/data.json

  # Run interactive chatbot
  python main.py chat

  # Test chatbot with predefined queries
  python main.py test

  # Show graph statistics
  python main.py stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build knowledge graph')
    build_parser.add_argument(
        '--data',
        type=str,
        default=None,
        help=f'Path to data file (default: {config.RAW_DATA_PATH})'
    )
    build_parser.add_argument(
        '--no-embeddings',
        action='store_true',
        help='Skip computing embeddings (faster but less accurate)'
    )

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Run interactive chatbot')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test chatbot with predefined queries')
    test_parser.add_argument(
        '--queries',
        type=str,
        nargs='+',
        help='Custom test queries'
    )

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show graph statistics')

    args = parser.parse_args()

    # Execute command
    if args.command == 'build':
        build_graph(
            data_path=args.data,
            use_embeddings=not args.no_embeddings
        )
    elif args.command == 'chat':
        run_chatbot()
    elif args.command == 'test':
        test_chatbot(queries=args.queries)
    elif args.command == 'stats':
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
