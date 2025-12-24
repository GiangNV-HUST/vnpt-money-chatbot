"""
Custom loader cho file Excel FAQ và JSON
Tối ưu để giữ nguyên cấu trúc câu hỏi-trả lời
"""

import pandas as pd
from langchain_core.documents import Document
from typing import List
import logging
import os
import json

logger = logging.getLogger(__name__)


def _detect_qa_columns(df) -> tuple:
    """Tự động detect cột câu hỏi và trả lời"""
    question_col = None
    answer_col = None

    # Tìm các cột có tên (không phải Unnamed)
    named_columns = [col for col in df.columns if not str(col).startswith("Unnamed:")]

    # Scan các cột có tên để tìm question/answer
    for col in named_columns:
        col_lower = str(col).lower()

        # Detect question column
        if question_col is None and any(
            keyword in col_lower for keyword in ["câu hỏi", "question", "q", "cau hoi"]
        ):
            question_col = col

        # Detect answer column
        if answer_col is None and any(
            keyword in col_lower
            for keyword in [
                "câu trả lời",
                "trả lời",
                "answer",
                "tra loi",
                "cau tra loi",
                "nội dung",
                "noi dung",
            ]
        ):
            answer_col = col

    # Fallback logic:
    # - Nếu chỉ tìm thấy answer column (vd: "TRẢ LỜI"), thì cột đầu tiên là question
    # - Nếu không tìm thấy gì, dùng 2 cột đầu tiên
    if question_col is None and answer_col is not None:
        # Trường hợp: cột 1 là Unnamed (question), cột 2 là "TRẢ LỜI" (answer)
        question_col = df.columns[0]
    elif question_col is None:
        # Không tìm thấy gì cả
        question_col = df.columns[0]

    if answer_col is None:
        # Nếu có question_col, answer_col là cột tiếp theo
        question_idx = list(df.columns).index(question_col)
        if question_idx + 1 < len(df.columns):
            answer_col = df.columns[question_idx + 1]
        else:
            answer_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    return question_col, answer_col


def load_faq_excel_sheet(file_path: str, sheet_name: str) -> List[Document]:
    """
    Load 1 sheet từ Excel FAQ

    Args:
        file_path: Đường dẫn file Excel
        sheet_name: Tên sheet cụ thể

    Returns:
        List of Documents
    """

    logger.info(f"  Đang load sheet: {sheet_name}")

    # Tự động phát hiện header row
    header_row = 0
    temp_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    for i in range(0, min(5, len(temp_df))):
        row_values = [
            str(val).lower() for val in temp_df.iloc[i].values if pd.notna(val)
        ]

        has_question = any("câu hỏi" in v or "question" in v for v in row_values)
        has_answer = any(
            "trả lời" in v or "answer" in v or "câu trả lời" in v for v in row_values
        )

        if (has_question and len(row_values) >= 2) or (has_question and has_answer):
            header_row = i
            logger.info(f"  Header tại row {i+1}")
            break

    # Đọc excel với header đúng
    if file_path.endswith(".xlsx"):
        df = pd.read_excel(
            file_path, sheet_name=sheet_name, engine="openpyxl", header=header_row
        )
    elif file_path.endswith(".xls"):
        df = pd.read_excel(
            file_path, sheet_name=sheet_name, engine="xlrd", header=header_row
        )
    else:
        raise ValueError(f"Không hỗ trợ định dạng: {file_path}")

    # Check minium columns
    if len(df.columns) < 2:
        logger.warning(f"   Sheet '{sheet_name}' có < 2 cột, skip")
        return []

    # Auto-detect cột Q&A
    question_col, answer_col = _detect_qa_columns(df)
    logger.info(f"  Q: '{question_col}', A: '{answer_col}'")

    documents = []
    current_section = "Tổng quan"

    for idx, row in df.iterrows():
        try:
            question = str(row[question_col]).strip()
            answer = str(row[answer_col]).strip()

            # Skip empty rows
            if pd.isna(row[question_col]) and pd.isna(row[answer_col]):
                continue

            # Phát hiện section headers (I., II., III., 1., 2.,...)
            if pd.isna(row[answer_col]) or answer == "nan" or answer == "":
                if not (pd.isna(row[question_col]) or question == "nan"):
                    if any(
                        question.startswith(prefix)
                        for prefix in [
                            "I.",
                            "II.",
                            "III.",
                            "IV.",
                            "V.",
                            "1.",
                            "2.",
                            "3.",
                            "4.",
                            "5.",
                            "6.",
                            "7.",
                            "8.",
                            "9.",
                        ]
                    ):
                        current_section = question
                        logger.info(f"  Section: {current_section}")
                continue

            # Skip nếu câu hỏi rỗng
            if pd.isna(row[question_col]) or question == "nan" or question == "":
                continue

            # Tạo document
            content = (
                f"Câu hỏi: {question}\n\n"
                f"Trả lời: {answer}\n"
                f"Keywords: {question}"
            )

            doc = Document(
                page_content=content,
                metadata={
                    "source": os.path.basename(file_path),
                    "sheet_name": sheet_name,
                    "type": "faq",
                    "section": current_section,
                    "question": question,
                    "answer": answer,
                    "row_id": idx + header_row + 2,
                },
            )
            documents.append(doc)

        except Exception as e:
            logger.warning(f"   Lỗi row {idx+2}: {e}")
            continue
    logger.info(f"  ✅ {len(documents)}")
    return documents


def load_faq_json(file_path: str) -> List[Document]:
    """
    Load FAQ documents từ file JSON

    Args:
        file_path: Đường dẫn đến file JSON

    Returns:
        List of Documents
    """
    logger.info(f"📄 Đang load JSON file: {os.path.basename(file_path)}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error(f"JSON file phải là một list, nhận được: {type(data)}")
            return []

        documents = []
        for idx, item in enumerate(data):
            try:
                # Lấy page_content và metadata
                page_content = item.get('page_content', '')
                metadata = item.get('metadata', {})

                if not page_content:
                    logger.warning(f"  ⚠️ Item {idx} không có page_content, skip")
                    continue

                # Tạo Document
                doc = Document(
                    page_content=page_content,
                    metadata=metadata
                )
                documents.append(doc)

            except Exception as e:
                logger.warning(f"  ⚠️ Lỗi khi xử lý item {idx}: {e}")
                continue

        logger.info(f"  ✅ Load thành công {len(documents)} documents từ JSON")
        return documents

    except FileNotFoundError:
        logger.error(f"❌ Không tìm thấy file: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ Lỗi decode JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Lỗi không xác định: {e}")
        return []


def load_all_faq_files(data_dir: str) -> List[Document]:
    """
    Load tất cả sheets từ tất cả các file excel trong thư mục data

    Args:
        data_dir: Thư mục chứ file excel

    Returns:
        List of all FAQ documents
    """
    all_documents = []

    # Tìm tất cả file excel
    excel_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith((".xlsx", ".xls")) and not file.startswith("~"):
                excel_files.append(os.path.join(root, file))

    if not excel_files:
        logger.warning(f"Không tìm thấy file Excel nào trong {data_dir}")
        return []

    logger.info(f"Tìm thấy {len(excel_files)} file Excel trong {data_dir}")

    for excel_file in excel_files:
        try:
            xl_file = pd.ExcelFile(excel_file)
            file_name = os.path.basename(excel_file)
            logger.info(f"\n📁 File: {file_name} ({len(xl_file.sheet_names)}) sheets")

            # ⭐ Load tất cả các sheets
            for sheet_name in xl_file.sheet_names:
                try:
                    docs = load_faq_excel_sheet(excel_file, sheet_name)
                    if docs:
                        all_documents.extend(docs)
                    else:
                        logger.info(f"  ⏭️ Sheet '{sheet_name}' không có FAQ hợp lệ")

                except Exception as e:
                    logger.warning(f"   ⚠️ Skip sheet '{sheet_name}': {e}")
        except Exception as e:
            logger.warning(f"❌ Lỗi file {excel_file}: {e}")
            continue
    logger.info(
        f"\n✅ TỔNG CỘNG: {len(all_documents)} FAQ documents từ {len(excel_files)} file(s)"
    )
    return all_documents


# Test
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "data"

    if os.path.exists(data_dir):
        print(f"📖 Đọc tất cả các file từ: {data_dir}\n")
        documents = load_all_faq_files(data_dir)

        print(f"\n{'='*80}")
        print(f"✅ TỔNG: {len(documents)} documents")

        if documents:
            print(f"\n{'='*80}")
            print("VÍ DỤ DOCUMENT ĐẦU TIÊN")
            print("=" * 80)
            print(documents[0].page_content)
            print("\nMETADATA:")
            for key, value in documents[0].metadata.items():
                print(f"    {key}: {value}")

            # Thống kê theo sheet
            print(f"\n{'='*80}")
            print("THỐNG KÊ THEO SHEET:")
            print("=" * 80)

            from collections import Counter

            sheet_counts = Counter(
                [doc.metadata.get("sheet_name", "Unknown") for doc in documents]
            )
            for sheet_name, count in sheet_counts.most_common():
                print(f"    {sheet_name}: {count} FAQs")

    else:
        print(f"❌ Thư mục không tồn tại: {data_dir}")
        print("\nCách sử dụng:")
        print(" python faq_loader.py [data_dir]")
        print("\nVí dụ:")
        print(" python faq_loader.py data")
