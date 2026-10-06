"""Rutas de la aplicación, tanto en desarrollo como empaquetada (.exe con PyInstaller)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

NOMBRE_APP = "Participaciones"


def esta_empaquetado() -> bool:
    return bool(getattr(sys, "frozen", False))


def carpeta_proyecto() -> Path:
    return Path(__file__).resolve().parent.parent


def carpeta_recursos() -> Path:
    """Dónde están los archivos incluidos (íconos, etc.)."""
    if esta_empaquetado():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return carpeta_proyecto()


def recurso(relativa: str | Path) -> Path:
    return carpeta_recursos() / relativa


def carpeta_datos() -> Path:
    """Base de datos y respaldos.

    En desarrollo: `data/` del proyecto. Empaquetada: Participaciones/data dentro de
    %LOCALAPPDATA%, fuera de la carpeta del .exe para que reconstruir o mover la app
    nunca toque los datos.
    """
    if esta_empaquetado():
        base = os.environ.get("LOCALAPPDATA")
        raiz = Path(base) if base else Path.home() / "AppData" / "Local"
        return raiz / NOMBRE_APP / "data"
    return carpeta_proyecto() / "data"
