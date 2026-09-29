from pathlib import Path

from config import (
    REPORTS_OUTPUT_DIR,
)

from reports.csv_report import (
    save_csv_report,
)

from reports.json_report import (
    save_json_report,
)


def save_scan_report(
    scan_results,
    output_dir=None,
):
    """
    Сохраняет JSON и CSV-отчёты.

    Для обратной совместимости возвращает
    путь к JSON-отчёту, который отображается
    в GUI.
    """
    if output_dir is None:
        output_dir = REPORTS_OUTPUT_DIR

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        output_dir
        / "scan_report.json"
    )

    csv_path = (
        output_dir
        / "scan_report.csv"
    )

    save_json_report(
        scan_results=scan_results,
        output_path=json_path,
    )

    save_csv_report(
        scan_results=scan_results,
        output_path=csv_path,
    )

    return str(
        json_path
    )