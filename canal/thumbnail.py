"""Geração de thumbnail (capa) para o vídeo.

Extrai um quadro do vídeo final (via ffmpeg) e escreve o título por cima com
uma faixa escura para legibilidade. Se não houver vídeo/ffmpeg, usa um fundo
sólido. Dependência: Pillow (importada de forma preguiçosa).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

W, H = 1280, 720  # tamanho padrão de thumbnail do YouTube

# caminhos comuns de uma fonte TrueType (para texto grande e legível)
_FONTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def _fonte(tamanho: int):
    from PIL import ImageFont

    for p in _FONTES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, tamanho)
            except OSError:
                continue
    try:  # Pillow >= 10.1 aceita tamanho na fonte padrão
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def _frame(video: Path, dest: Path) -> bool:
    """Extrai um quadro do vídeo. Retorna True se conseguiu."""
    import shutil

    if shutil.which("ffmpeg") is None or not video.exists():
        return False
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1", "-i", str(video), "-frames:v", "1", str(dest)],
            check=True, capture_output=True,
        )
        return dest.exists()
    except subprocess.CalledProcessError:
        return False


def _cover(img, w: int, h: int):
    """Redimensiona cobrindo a área (w,h) e recorta o centro."""
    from PIL import Image

    escala = max(w / img.width, h / img.height)
    novo = img.resize((int(img.width * escala), int(img.height * escala)), Image.LANCZOS)
    x = (novo.width - w) // 2
    y = (novo.height - h) // 2
    return novo.crop((x, y, x + w, y + h))


def _wrap(draw, texto: str, fonte, largura_max: int) -> list[str]:
    palavras = texto.split()
    linhas: list[str] = []
    atual = ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas[:3]  # no máximo 3 linhas


def gerar_thumbnail(
    titulo: str,
    saida: Path,
    video: Path | None = None,
    cor_fundo: tuple[int, int, int] = (15, 23, 42),
) -> Path:
    from PIL import Image, ImageDraw

    saida.parent.mkdir(parents=True, exist_ok=True)

    # fundo: quadro do vídeo ou cor sólida
    base = Image.new("RGB", (W, H), cor_fundo)
    if video is not None:
        with tempfile.TemporaryDirectory() as tmp:
            frame = Path(tmp) / "frame.png"
            if _frame(video, frame):
                base = _cover(Image.open(frame).convert("RGB"), W, H)

    draw = ImageDraw.Draw(base, "RGBA")

    # faixa escura no rodapé para o texto
    faixa_h = int(H * 0.45)
    faixa = Image.new("RGBA", (W, faixa_h), (0, 0, 0, 150))
    base.paste(faixa, (0, H - faixa_h), faixa)

    fonte = _fonte(72)
    linhas = _wrap(draw, titulo.upper(), fonte, W - 120)
    altura_linha = 82
    y = H - 40 - len(linhas) * altura_linha
    for linha in linhas:
        x = 60
        # contorno preto + texto branco
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            draw.text((x + dx, y + dy), linha, font=fonte, fill=(0, 0, 0, 255))
        draw.text((x, y), linha, font=fonte, fill=(255, 255, 255, 255))
        y += altura_linha

    base.save(saida, "PNG")
    return saida
