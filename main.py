import tkinter as tk

from config import ensure_directories
from gui.app import DataMatrixApp


def main():
    ensure_directories()

    root = tk.Tk()

    app = DataMatrixApp(root)

    app.run()


if __name__ == "__main__":
    main()