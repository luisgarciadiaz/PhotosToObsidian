__version__ = "0.1.0"

from src.gui import GUI


def main() -> None:
    app = GUI()
    app.run()


if __name__ == "__main__":
    main()