import pandas as pd
from pathlib import Path
from logger import log


def extract_codes_from_pdf(pdf_path: str, codes: list, output_excel: str = None):
    """
    Сохраняет коды в Excel.
    """
    pdf_path = Path(pdf_path)
    
    if output_excel is None:
        output_excel = pdf_path.with_suffix('.xlsx')
    else:
        output_excel = Path(output_excel)
    
    log(f"Экспорт {len(codes)} кодов в Excel...")
    
    # Очищаем коды от невалидных символов для Excel
    clean_codes = []
    for code in codes:
        # Заменяем control characters на читаемые
        cleaned = code.replace('\x1d', '<GS>')  # Group Separator
        clean_codes.append(cleaned)
    
    if clean_codes:
        df = pd.DataFrame([
            {'page': i + 1, 'code': code}
            for i, code in enumerate(clean_codes)
        ])
        
        try:
            df.to_excel(output_excel, index=False)
            log(f"Сохранено {len(clean_codes)} кодов в {output_excel}")
        except PermissionError:
            output_excel = output_excel.with_name(output_excel.stem + "_new" + output_excel.suffix)
            df.to_excel(output_excel, index=False)
            log(f"Сохранено {len(clean_codes)} кодов в {output_excel} (оригинальный файл открыт)")
    else:
        log("Нет кодов для экспорта")
        try:
            df = pd.DataFrame(columns=['page', 'code'])
            df.to_excel(output_excel, index=False)
        except PermissionError:
            output_excel = output_excel.with_name(output_excel.stem + "_new" + output_excel.suffix)
            df = pd.DataFrame(columns=['page', 'code'])
            df.to_excel(output_excel, index=False)
            log(f"Сохранён пустой файл в {output_excel} (оригинальный файл открыт)")
    
    return clean_codes