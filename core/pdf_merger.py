import fitz
from pathlib import Path
from logger import log


def merge_pdfs(pdf_paths: list, output_path: str):
    """
    Объединяет несколько PDF в один.
    """
    log(f"Объединение {len(pdf_paths)} PDF в {output_path}...")
    
    result = fitz.open()
    
    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
        result.insert_pdf(doc)
        doc.close()
    
    result.save(output_path)
    result.close()
    
    log(f"Объединённый PDF сохранён: {output_path}")
    return output_path


def extract_pages(pdf_path: str, page_numbers: list, output_path: str):
    """
    Извлекает указанные страницы из PDF.
    """
    log(f"Извлечение страниц {page_numbers} из {pdf_path}...")
    
    doc = fitz.open(pdf_path)
    result = fitz.open()
    
    for page_num in page_numbers:
        if 0 <= page_num < len(doc):
            result.insert_pdf(doc, from_page=page_num, to_page=page_num)
    
    result.save(output_path)
    result.close()
    doc.close()
    
    log(f"Извлечённые страницы сохранены: {output_path}")
    return output_path