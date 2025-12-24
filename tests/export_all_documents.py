"""
Export tất cả documents từ faq_loader.py ra file text
"""
import sys
import os
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from faq_loader import load_all_faq_files

def export_documents(data_dir="data", output_file="documents_output.txt"):
    """Export tất cả documents ra file text"""

    if not os.path.exists(data_dir):
        print(f"❌ Thư mục không tồn tại: {data_dir}")
        return

    print(f"📖 Đang đọc tất cả các file từ: {data_dir}\n")

    # Load tất cả documents
    documents = load_all_faq_files(data_dir)

    if not documents:
        print("⚠️ Không có document nào được load")
        return

    print(f"\n✅ Đã load {len(documents)} documents")
    print(f"📝 Đang xuất ra file: {output_file}\n")

    # Xuất ra file với encoding UTF-8
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("="*100 + "\n")
        f.write(f"XUẤT TẤT CẢ DOCUMENTS TỪ FAQ LOADER\n")
        f.write(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tổng số documents: {len(documents)}\n")
        f.write("="*100 + "\n\n")

        # Xuất từng document
        for i, doc in enumerate(documents, 1):
            f.write("\n" + "="*100 + "\n")
            f.write(f"DOCUMENT #{i}/{len(documents)}\n")
            f.write("="*100 + "\n\n")

            # Metadata
            f.write("📌 METADATA:\n")
            f.write("-"*100 + "\n")
            for key, value in doc.metadata.items():
                f.write(f"  • {key}: {value}\n")

            # Page content
            f.write("\n📄 PAGE CONTENT:\n")
            f.write("-"*100 + "\n")
            f.write(doc.page_content + "\n")

            # Separator
            f.write("\n" + "="*100 + "\n")

        # Footer với thống kê
        f.write("\n\n" + "="*100 + "\n")
        f.write("THỐNG KÊ TỔNG HỢP\n")
        f.write("="*100 + "\n\n")

        from collections import Counter

        # Thống kê theo file
        f.write("📊 THEO FILE:\n")
        file_counts = Counter([doc.metadata.get("source", "Unknown") for doc in documents])
        for file_name, count in file_counts.most_common():
            f.write(f"  • {file_name}: {count} FAQs\n")

        # Thống kê theo sheet
        f.write("\n📊 THEO SHEET:\n")
        sheet_counts = Counter([doc.metadata.get("sheet_name", "Unknown") for doc in documents])
        for sheet_name, count in sheet_counts.most_common():
            f.write(f"  • {sheet_name}: {count} FAQs\n")

        # Thống kê theo section
        f.write("\n📊 THEO SECTION:\n")
        section_counts = Counter([doc.metadata.get("section", "Unknown") for doc in documents])
        for section_name, count in section_counts.most_common():
            f.write(f"  • {section_name}: {count} FAQs\n")

        # Độ dài
        content_lengths = [len(doc.page_content) for doc in documents]
        question_lengths = [len(doc.metadata.get("question", "")) for doc in documents]
        answer_lengths = [len(doc.metadata.get("answer", "")) for doc in documents]

        f.write("\n📏 ĐỘ DÀI:\n")
        f.write(f"  • Độ dài TB page_content: {sum(content_lengths)/len(content_lengths):.0f} ký tự\n")
        f.write(f"  • Độ dài TB câu hỏi: {sum(question_lengths)/len(question_lengths):.0f} ký tự\n")
        f.write(f"  • Độ dài TB câu trả lời: {sum(answer_lengths)/len(answer_lengths):.0f} ký tự\n")
        f.write(f"  • Câu hỏi dài nhất: {max(question_lengths)} ký tự\n")
        f.write(f"  • Câu trả lời dài nhất: {max(answer_lengths)} ký tự\n")

        f.write("\n" + "="*100 + "\n")
        f.write("✅ HOÀN THÀNH!\n")
        f.write("="*100 + "\n")

    print(f"✅ Đã xuất {len(documents)} documents ra file: {output_file}")
    print(f"📂 Đường dẫn đầy đủ: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    # Cho phép truyền tham số từ command line
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "documents_output.txt"

    export_documents(data_dir, output_file)
