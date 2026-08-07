"""Montagem do vídeo final com ffmpeg.

Combina o vídeo base (imagens com licença livre) com a narração gerada,
opcionalmente abaixando o volume do áudio original. Requer o `ffmpeg`
instalado no sistema (não é um pacote pip).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_disponivel() -> bool:
    return shutil.which("ffmpeg") is not None


def duracao_seg(caminho: Path) -> float:
    """Duração de um mídia em segundos via ffprobe (0.0 se indisponível)."""
    if shutil.which("ffprobe") is None:
        return 0.0
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(caminho),
            ],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip() or 0.0)
    except (subprocess.CalledProcessError, ValueError):
        return 0.0


def montar(
    video: Path,
    narracao: Path,
    saida: Path,
    manter_audio_original: bool = True,
    volume_original: float = 0.15,
) -> Path:
    """Sobrepõe a narração ao vídeo.

    O vídeo é cortado/estendido para acompanhar a duração da narração:
    se a narração for mais longa que o vídeo, o vídeo entra em loop.
    """
    if not ffmpeg_disponivel():
        raise RuntimeError(
            "ffmpeg não encontrado. Instale (ex.: `apt install ffmpeg` ou "
            "`brew install ffmpeg`) e tente novamente."
        )
    saida.parent.mkdir(parents=True, exist_ok=True)

    dur_narracao = duracao_seg(narracao)

    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(video), "-i", str(narracao)]

    if manter_audio_original:
        # mistura áudio original (abaixado) + narração
        filtro = (
            f"[0:a]volume={volume_original}[orig];"
            "[orig][1:a]amix=inputs=2:duration=longest:dropout_transition=0[aout]"
        )
        cmd += ["-filter_complex", filtro, "-map", "0:v:0", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]

    # termina quando a narração termina
    if dur_narracao > 0:
        cmd += ["-t", f"{dur_narracao:.2f}"]

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(saida),
    ]

    subprocess.run(cmd, check=True)
    return saida
