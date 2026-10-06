"""Genera assets/icon/app.ico (multi-tamaño) a partir del logo PNG.

Uso: .venv/Scripts/python.exe tools/crear_icono.py
Requiere Pillow (requirements-build.txt). Recorta los márgenes transparentes del logo y lo
centra en un cuadrado. El logo es azul oscuro sobre fondo transparente y casi no se ve en
barras de título o de tareas oscuras, por eso se coloca sobre un fondo blanco redondeado
(pon FONDO_BLANCO = False para generar el ícono transparente).
"""

from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "assets" / "icon" / "FES ARAGON.png"
DESTINO = RAIZ / "assets" / "icon" / "app.ico"
TAMANOS = [16, 24, 32, 48, 64, 128, 256]
FONDO_BLANCO = True
LADO = 256
RADIO_ESQUINAS = 48
OCUPACION = 0.80  # proporción del lienzo que ocupa el logo


def main() -> None:
    logo = Image.open(ORIGEN).convert("RGBA")
    caja = logo.getbbox()
    if caja:
        logo = logo.crop(caja)

    escala = (LADO * (OCUPACION if FONDO_BLANCO else 0.94)) / max(logo.size)
    logo = logo.resize((round(logo.width * escala), round(logo.height * escala)), Image.LANCZOS)

    lienzo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    if FONDO_BLANCO:
        ImageDraw.Draw(lienzo).rounded_rectangle(
            (0, 0, LADO - 1, LADO - 1), radius=RADIO_ESQUINAS, fill=(255, 255, 255, 255)
        )
    lienzo.paste(logo, ((LADO - logo.width) // 2, (LADO - logo.height) // 2), logo)
    lienzo.save(DESTINO, format="ICO", sizes=[(t, t) for t in TAMANOS])
    print(f"Icono creado: {DESTINO} ({', '.join(map(str, TAMANOS))} px)")


if __name__ == "__main__":
    main()
