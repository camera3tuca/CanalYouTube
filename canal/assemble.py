"""Montagem do vídeo final com ffmpeg.

Combina o vídeo base (imagens com licença livre) com a narração gerada,
legendas queimadas, trilha de fundo e formato horizontal (16:9) ou vertical
(9:16, para Shorts). Requer o `ffmpeg` instalado no sistema.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# resolução alvo para Shorts (9:16)
SHORTS_W, SHORTS_H = 1080, 1920


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


def tem_audio(caminho: Path) -> bool:
    """Diz se o arquivo tem pelo menos uma faixa de áudio (via ffprobe)."""
    if shutil.which("ffprobe") is None:
        return False
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=index", "-of", "csv=p=0", str(caminho),
            ],
            capture_output=True, text=True, check=True,
        )
        return bool(out.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def _escapa_legenda(caminho: Path) -> str:
    """Escapa o caminho para uso no filtro `subtitles` do ffmpeg."""
    p = str(caminho)
    p = p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return p


def montar(
    video: Path,
    narracao: Path,
    saida: Path,
    manter_audio_original: bool = True,
    volume_original: float = 0.15,
    legenda: Path | None = None,
    vertical: bool = False,
    musica: Path | None = None,
    volume_musica: float = 0.12,
) -> Path:
    """Monta o vídeo final.

    - Loop do vídeo/trilha para cobrir a narração.
    - `legenda`  : .srt queimado na imagem.
    - `vertical` : recorta/escala para 9:16 (Shorts).
    - `musica`   : trilha de fundo em volume baixo (em loop).
    O áudio original só é usado se o clipe realmente tiver faixa de áudio.
    """
    if not ffmpeg_disponivel():
        raise RuntimeError(
            "ffmpeg não encontrado. Instale (ex.: `apt install ffmpeg` ou "
            "`brew install ffmpeg`) e tente novamente."
        )
    saida.parent.mkdir(parents=True, exist_ok=True)

    dur_narracao = duracao_seg(narracao)
    usar_original = manter_audio_original and tem_audio(video)

    # entradas: 0=video, 1=narração, 2=música (se houver)
    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(video), "-i", str(narracao)]
    idx_musica = None
    if musica is not None and Path(musica).exists():
        idx_musica = 2
        cmd += ["-stream_loop", "-1", "-i", str(musica)]

    partes: list[str] = []

    # --- filtro de vídeo (geometria primeiro, depois legenda) ---
    vf: list[str] = []
    if vertical:
        vf.append(
            f"scale={SHORTS_W}:{SHORTS_H}:force_original_aspect_ratio=increase"
        )
        vf.append(f"crop={SHORTS_W}:{SHORTS_H}")
    if legenda is not None and Path(legenda).exists():
        estilo = "FontSize=22,Outline=2,Shadow=0,Alignment=2,MarginV=60"
        vf.append(f"subtitles='{_escapa_legenda(Path(legenda))}':force_style='{estilo}'")
    if vf:
        partes.append(f"[0:v]{','.join(vf)}[vout]")
        vmap = "[vout]"
    else:
        vmap = "0:v:0"

    # --- filtro de áudio (mistura o que existir) ---
    amix_labels: list[str] = []
    if usar_original:
        partes.append(f"[0:a]volume={volume_original}[orig]")
        amix_labels.append("[orig]")
    amix_labels.append("[1:a]")  # narração
    if idx_musica is not None:
        partes.append(f"[{idx_musica}:a]volume={volume_musica}[mus]")
        amix_labels.append("[mus]")

    if len(amix_labels) > 1:
        partes.append(
            f"{''.join(amix_labels)}amix=inputs={len(amix_labels)}:"
            "duration=longest:dropout_transition=0[aout]"
        )
        amap = "[aout]"
    else:
        amap = "1:a:0"

    if partes:
        cmd += ["-filter_complex", ";".join(partes)]
    cmd += ["-map", vmap, "-map", amap]

    if dur_narracao > 0:
        cmd += ["-t", f"{dur_narracao:.2f}"]

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(saida),
    ]

    subprocess.run(cmd, check=True)
    return saida
