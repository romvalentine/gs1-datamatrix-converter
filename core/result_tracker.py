from dataclasses import asdict

from core.models import (
    CodeResult,
    ScanResult,
)


class ResultTracker:
    def __init__(self):
        self.scan_results = []
        self.code_results = []
        self.page_results = []

        self._unique_codes = set()
        self._all_codes = []

    def add_scan_result(
        self,
        result=None,
        **kwargs,
    ):
        if result is None:
            result = ScanResult(
                **kwargs
            )

        self.scan_results.append(
            result
        )

        return result

    def add_page_result(
        self,
        file_path,
        page_number,
        codes=None,
        status="",
        mode="",
        elapsed=0.0,
        error="",
        method="",
        variant="",
    ):
        codes = list(
            codes or []
        )

        item = {
            "file_path": str(
                file_path
            ),
            "page_number": page_number,
            "codes": codes,
            "codes_count": len(codes),
            "status": status,
            "mode": mode,
            "elapsed": float(
                elapsed or 0.0
            ),
            "error": error or "",
            "method": method or "",
            "variant": variant or "",
        }

        self.page_results.append(
            item
        )

        for code in codes:
            self.add_code(
                code=code,
                file_path=file_path,
                page_number=page_number,
                source=method,
                variant=variant,
                elapsed=elapsed,
            )

        return item

    def add_code(
        self,
        code,
        file_path="",
        page_number=None,
        source="",
        variant="",
        elapsed=0.0,
    ):
        if code is None:
            return None

        code = str(code)

        is_duplicate = (
            code in self._unique_codes
        )

        self._unique_codes.add(
            code
        )

        self._all_codes.append(
            code
        )

        result = CodeResult(
            code=code,
            file_path=str(
                file_path
            ),
            page_number=page_number,
            source=source or "",
            variant=variant or "",
            elapsed=float(
                elapsed or 0.0
            ),
        )

        self.code_results.append(
            {
                **asdict(result),
                "is_duplicate": (
                    is_duplicate
                ),
            }
        )

        return result

    def add_codes(
        self,
        codes,
        file_path="",
        page_number=None,
        source="",
        variant="",
        elapsed=0.0,
    ):
        added = []

        for code in codes or []:
            result = self.add_code(
                code=code,
                file_path=file_path,
                page_number=page_number,
                source=source,
                variant=variant,
                elapsed=elapsed,
            )

            if result is not None:
                added.append(result)

        return added

    def unique_codes(self):
        return list(
            self._unique_codes
        )

    def all_codes(self):
        return list(
            self._all_codes
        )

    def duplicates(self):
        counts = {}

        for code in self._all_codes:
            counts[code] = (
                counts.get(code, 0)
                + 1
            )

        return [
            code
            for code, count
            in counts.items()
            if count > 1
        ]

    def total_codes(self):
        return len(
            self._all_codes
        )

    def unique_count(self):
        return len(
            self._unique_codes
        )

    def failed_scan_results(self):
        return [
            result
            for result in self.scan_results
            if result.status in {
                "error",
                "not_found",
                "stopped",
            }
        ]

    def to_dict(self):
        return {
            "scan_results": [
                asdict(result)
                for result
                in self.scan_results
            ],
            "code_results": list(
                self.code_results
            ),
            "page_results": list(
                self.page_results
            ),
            "summary": {
                "total_codes": (
                    self.total_codes()
                ),
                "unique_codes": (
                    self.unique_count()
                ),
                "duplicates": (
                    self.duplicates()
                ),
                "files": len(
                    self.scan_results
                ),
                "failed_files": len(
                    self.failed_scan_results()
                ),
            },
        }

    def clear(self):
        self.scan_results.clear()
        self.code_results.clear()
        self.page_results.clear()
        self._unique_codes.clear()
        self._all_codes.clear()