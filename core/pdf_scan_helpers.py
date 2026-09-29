from core.decoder import (
    collect_codes,
    decode_image,
)

from logger import log


class PdfScanHelpersMixin:
    @staticmethod
    def stopped(
        stop_event,
    ):
        return (
            stop_event is not None
            and stop_event.is_set()
        )

    @staticmethod
    def merge_codes(
        source,
        found,
        result,
    ):
        for code in source or []:
            if code is None:
                continue

            if code not in found:
                found.add(code)
                result.append(code)

    def scan_full_image(
        self,
        image,
        label,
        stop_event=None,
    ):
        if self.stopped(stop_event):
            return []

        decoded = decode_image(
            image,
            label,
            stop_event=stop_event,
        )

        found = set()
        result = []

        collect_codes(
            decoded,
            found,
            result,
        )

        return result