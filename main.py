"""Punto de entrada. Uso: python main.py [--db RUTA]"""

import argparse

from core.database import RUTA_POR_DEFECTO
from ui_desktop.app import App


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestor de participaciones")
    parser.add_argument("--db", default=RUTA_POR_DEFECTO, help="ruta de la base de datos SQLite")
    args = parser.parse_args()
    App(args.db).mainloop()


if __name__ == "__main__":
    main()
