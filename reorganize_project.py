"""
Reorganize project structure into GraphRAG and Traditional RAG folders
"""

import os
import sys
import shutil
from pathlib import Path

# Fix encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')


def analyze_files():
    """Analyze all files in the project"""

    root = Path(__file__).parent

    # Files to keep in GraphRAG folder
    graph_rag_files = {
        # Main files
        'graphRAGChatBot/chatbot.py',
        'graphRAGChatBot/neo4j_rag_engine.py',
        'graphRAGChatBot/neo4j_connector.py',
        'graphRAGChatBot/config.py',
        'graphRAGChatBot/main.py',
        'graphRAGChatBot/app_streamlit.py',

        # Entity extraction
        'graphRAGChatBot/enhanced_entity_extractor.py',
        'graphRAGChatBot/simple_entity_extractor.py',
        'graphRAGChatBot/llm_entity_extractor.py',

        # Intent and context
        'graphRAGChatBot/intent_classifier.py',
        'graphRAGChatBot/conversation_context_manager.py',
        'graphRAGChatBot/step_tracker.py',

        # Migration and setup
        'graphRAGChatBot/neo4j_graph_builder_llm.py',
        'graphRAGChatBot/migrate_steps_to_neo4j.py',
        'graphRAGChatBot/migrate_case_nodes.py',
        'graphRAGChatBot/export_neo4j_database.py',

        # Case nodes
        'graphRAGChatBot/auto_create_case_nodes.py',
        'graphRAGChatBot/fix_mobile_money_cases.py',
        'graphRAGChatBot/extract_case_nodes.py',
        'graphRAGChatBot/analyze_conditional_cases.py',

        # Utilities
        'graphRAGChatBot/update_embeddings.py',
        'graphRAGChatBot/visualize_graph_schema.py',
        'graphRAGChatBot/simple_document_view.py',

        # Verification
        'graphRAGChatBot/verify_all_cases.py',
        'graphRAGChatBot/check_faq_answer.py',
        'graphRAGChatBot/check_step_text.py',
        'graphRAGChatBot/check_error_entities.py',

        # Config
        'graphRAGChatBot/.env',
        'graphRAGChatBot/requirements.txt',

        # Documentation
        'graphRAGChatBot/README.md',
        'graphRAGChatBot/INDEX.md',
        'graphRAGChatBot/CASE_NODES_SUMMARY.md',
        'graphRAGChatBot/CASE_NODES_UPDATE_REPORT.md',
        'graphRAGChatBot/PROJECT_SUMMARY.md',
        'graphRAGChatBot/IMPLEMENTATION_COMPLETE.md',

        # Data
        'graphRAGChatBot/data/conditional_cases_analysis.json',
        'graphRAGChatBot/database_exports/',
    }

    # Files to keep in Traditional RAG folder
    traditional_rag_files = {
        'rag_chatbot.py',
        'hybrid_search.py',
        'faq_loader.py',
        'app.py',
        'requirements.txt',
        '.env',
    }

    # Files to DELETE (temporary/debug/duplicate)
    files_to_delete = {
        # Root level debug/test files
        'check_faq72.py',
        'check_faq8.py',
        'check_mo_khoa_faq.py',
        'check_neo4j_error.py',
        'check_neo4j_faqs.py',
        'check_steps_migration.py',
        'debug_query.py',
        'explain_query_flow.py',
        'quick_test.py',
        'test_chatbot.py',
        'test_context_detection.py',
        'test_cypher_error_matching.py',
        'test_end_to_end.py',
        'test_entity_extraction.py',
        'test_entity_matching.py',
        'test_fix.py',
        'test_fixed_query.py',
        'test_full_query.py',
        'test_greetings.py',
        'test_intent_fix.py',
        'test_neo4j_password_query.py',
        'test_specific_query.py',
        'test_streamlit_context.py',
        'inspect_neo4j_structure.py',

        # GraphRAG test files (keep only important ones)
        'graphRAGChatBot/debug_query.py',
        'graphRAGChatBot/test_context_aware_chatbot.py',
        'graphRAGChatBot/test_context_detection.py',
        'graphRAGChatBot/test_context_fix.py',
        'graphRAGChatBot/test_embedded_query.py',
        'graphRAGChatBot/test_full_conversation.py',
        'graphRAGChatBot/test_full_query.py',
        'graphRAGChatBot/test_new_full_query.py',
        'graphRAGChatBot/test_new_query.py',
        'graphRAGChatBot/test_process_query.py',
        'graphRAGChatBot/test_semantic_search.py',
        'graphRAGChatBot/test_steps_query.py',
        'graphRAGChatBot/test_step_4.py',
        'graphRAGChatBot/test_with_chatbot.py',
        'graphRAGChatBot/test_wrong_transfer.py',
        'graphRAGChatBot/analyze_extraction_impact.py',
        'graphRAGChatBot/visualize_document_processing.py',

        # Temporary files
        'graphRAGChatBot/_chatbot_embedded_test.txt',
        'graphRAGChatBot/_migration_analysis.txt',
        'graphRAGChatBot/chatbot_test_results.json',
        'graphRAGChatBot/quick_test_results.json',
        'graphRAGChatBot/ve_may_bay_entities.json',

        # Old markdown docs (keep only essential ones)
        'ARCHITECTURE_CHANGES.md',
        'BULLET_POINT_FORMATTING_FIX.md',
        'CASE_NODES_MIGRATION_SUMMARY.md',
        'CODE_CLEANUP.md',
        'compare_solutions.md',
        'CONFIDENCE_CALCULATION.md',
        'CONTEXT_AWARE_FIX.md',
        'CONTEXT_UNDERSTANDING_IMPROVEMENTS.md',
        'current_weights_analysis.md',
        'FINAL_SUMMARY.md',
        'FORMATTING_IMPROVEMENTS.md',
        'KNOWLEDGE_GRAPH_DESIGN.md',
        'MIGRATION_STATUS_REPORT.md',
        'MIGRATION_TO_OPENAI.md',
        'NEO4J_GRAPH_STRUCTURE.md',
        'QUERY_FLOW_EXPLANATION.md',
        'STEP_EXTRACTION_FIX.md',
        'STREAMLIT_CONTEXT_FIX.md',

        # GraphRAG old docs
        'graphRAGChatBot/ERROR_SUMMARY.md',
        'graphRAGChatBot/FILES_OVERVIEW.txt',
        'graphRAGChatBot/FINAL_SUCCESS_SUMMARY.md',
        'graphRAGChatBot/MIGRATION_SUMMARY.md',
        'graphRAGChatBot/ROOT_CAUSE_ANALYSIS.md',
        'graphRAGChatBot/VERIFICATION_CHECKLIST.md',
        'graphRAGChatBot/WORK_COMPLETED.md',

        # Utilities not needed
        'convert_paraphrases_to_documents.py',
        'compare_models.py',
        'finetune_mnrl.py',
        'fix_neo4j_links.py',
        'generate_paraphrases.py',
        'generate_paraphrases_from_txt.py',
    }

    print("="*80)
    print("FILE ANALYSIS REPORT")
    print("="*80)

    print(f"\nGraphRAG files: {len(graph_rag_files)}")
    print(f"Traditional RAG files: {len(traditional_rag_files)}")
    print(f"Files to delete: {len(files_to_delete)}")

    # Check which files exist
    print("\n" + "="*80)
    print("FILES TO DELETE (if exist):")
    print("="*80)

    existing_to_delete = []
    for file in sorted(files_to_delete):
        file_path = root / file
        if file_path.exists():
            existing_to_delete.append(file)
            print(f"  ✓ {file}")

    print(f"\nTotal files to delete: {len(existing_to_delete)}")

    return {
        'graph_rag': graph_rag_files,
        'traditional_rag': traditional_rag_files,
        'to_delete': existing_to_delete
    }


def create_new_structure(dry_run=True):
    """Create new folder structure"""

    root = Path(__file__).parent

    files = analyze_files()

    if dry_run:
        print("\n" + "="*80)
        print("DRY RUN MODE - No changes will be made")
        print("="*80)
        return

    print("\n" + "="*80)
    print("EXECUTE MODE - Creating new structure...")
    print("="*80)

    # Create new folders
    graph_rag_new = root / 'GraphRAG'
    traditional_rag_new = root / 'TraditionalRAG'
    archive = root / 'Archive_Old_Files'

    graph_rag_new.mkdir(exist_ok=True)
    traditional_rag_new.mkdir(exist_ok=True)
    archive.mkdir(exist_ok=True)

    print(f"\n✅ Created folders:")
    print(f"   - {graph_rag_new}")
    print(f"   - {traditional_rag_new}")
    print(f"   - {archive}")

    # Move GraphRAG files
    print(f"\n📁 Moving GraphRAG files...")
    for file in files['graph_rag']:
        src = root / 'graphRAGChatBot' / file.replace('graphRAGChatBot/', '')
        if src.exists():
            dest = graph_rag_new / file.replace('graphRAGChatBot/', '')
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Handle directories
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
            print(f"   ✓ {file}")

    # Move Traditional RAG files
    print(f"\n📁 Moving Traditional RAG files...")
    for file in files['traditional_rag']:
        src = root / file
        if src.exists():
            dest = traditional_rag_new / file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"   ✓ {file}")

    # Move files to delete to archive
    print(f"\n🗑️ Archiving files to delete...")
    for file in files['to_delete']:
        src = root / file
        if src.exists():
            dest = archive / file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            print(f"   ✓ {file}")

    print("\n✅ Reorganization complete!")
    print(f"\nNext steps:")
    print(f"  1. Review files in: {graph_rag_new}")
    print(f"  2. Review files in: {traditional_rag_new}")
    print(f"  3. Check archived files in: {archive}")
    print(f"  4. Delete old 'graphRAGChatBot' folder if everything looks good")


if __name__ == '__main__':
    import sys

    dry_run = '--execute' not in sys.argv

    if dry_run:
        analyze_files()
        print("\n" + "="*80)
        print("To execute reorganization, run:")
        print("  python reorganize_project.py --execute")
        print("="*80)
    else:
        confirm = input("\n⚠️  This will reorganize the entire project. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            create_new_structure(dry_run=False)
        else:
            print("Cancelled.")
