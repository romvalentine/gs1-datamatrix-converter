import time


def log(message: str) -> None:
    print(
        f"[{time.strftime('%H:%M:%S')}] {message}",
        flush=True,
    )


def format_seconds(value: float) -> str:
    return f"{value:.2f} сек"