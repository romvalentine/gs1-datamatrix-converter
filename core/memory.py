import json
import os
from pathlib import Path

from config import MEMORY_FILE
from logger import log


class VariantMemory:
    def __init__(
        self,
        path=MEMORY_FILE,
    ):
        self.path = Path(path)

        self.data = {
            "variants": {},
            "signatures": {},
        }

        self.changed = False
        self.load()

    def load(self):
        if not self.path.exists():
            return

        try:
            with self.path.open(
                "r",
                encoding="utf-8",
            ) as file:
                loaded_data = json.load(file)

            if not isinstance(
                loaded_data,
                dict,
            ):
                raise ValueError(
                    "Некорректный формат памяти"
                )

            self.data = loaded_data

            self.data.setdefault(
                "variants",
                {},
            )

            self.data.setdefault(
                "signatures",
                {},
            )

        except Exception as error:
            log(
                f"memory load error: "
                f"{error}"
            )

            self.data = {
                "variants": {},
                "signatures": {},
            }

    def save(self):
        """
        Безопасно сохраняет память.

        Сначала создаётся временный файл,
        затем он заменяет основной.
        """
        temp_path = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    self.data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

                file.flush()
                os.fsync(
                    file.fileno()
                )

            os.replace(
                temp_path,
                self.path,
            )

            self.changed = False

        except Exception as error:
            log(
                f"memory save error: "
                f"{error}"
            )

            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

    def save_if_changed(self):
        if self.changed:
            self.save()

    def record_success(
        self,
        signature,
        variant_name,
    ):
        signatures = self.data.setdefault(
            "signatures",
            {},
        )

        variants = self.data.setdefault(
            "variants",
            {},
        )

        signatures[signature] = variant_name

        variants[variant_name] = (
            variants.get(
                variant_name,
                0,
            )
            + 1
        )

        self.changed = True

    def preferred_variant(
        self,
        signature,
    ):
        signatures = self.data.get(
            "signatures",
            {},
        )

        return signatures.get(
            signature
        )