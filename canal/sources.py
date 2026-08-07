"""Busca e download de vídeos em fontes com LICENÇA LIVRE.

IMPORTANTE — este módulo, por decisão de projeto, só integra fontes cujo
licenciamento permite uso (inclusive, na maioria, comercial):

    - Pexels   (https://www.pexels.com/license/)   API key gratuita
    - Pixabay  (https://pixabay.com/service/license-summary/)  API key gratuita
    - Internet Archive (domínio público)            sem chave

NÃO integramos "baixar qualquer vídeo do YouTube/Instagram/etc." porque isso
normalmente viola direito autoral e a política de "conteúdo reutilizado" do
YouTube, o que impede a monetização. Confira sempre a licença de cada item.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

TIMEOUT = 30


@dataclass
class VideoResult:
    """Um resultado de busca padronizado entre as fontes."""

    source: str          # "pexels" | "pixabay" | "archive"
    title: str
    author: str
    page_url: str        # página original (para dar crédito)
    download_url: str    # link direto do arquivo de vídeo
    width: int
    height: int
    duration: int        # segundos (0 se desconhecido)
    license: str         # descrição curta da licença

    @property
    def label(self) -> str:
        dur = f"{self.duration}s" if self.duration else "?"
        return f"[{self.source}] {self.title or 'sem título'} · {self.width}x{self.height} · {dur} · {self.author}"


def _slug(text: str, limit: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:limit] or "video"


# --------------------------------------------------------------------------- #
# Pexels
# --------------------------------------------------------------------------- #
def search_pexels(query: str, api_key: str, per_page: int = 10) -> list[VideoResult]:
    if not api_key:
        return []
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": per_page},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results: list[VideoResult] = []
    for v in resp.json().get("videos", []):
        files = sorted(
            v.get("video_files", []),
            key=lambda f: (f.get("width") or 0),
            reverse=True,
        )
        if not files:
            continue
        best = files[0]
        results.append(
            VideoResult(
                source="pexels",
                title=(v.get("user", {}).get("name") or "Pexels") + " video",
                author=v.get("user", {}).get("name", "desconhecido"),
                page_url=v.get("url", ""),
                download_url=best.get("link", ""),
                width=best.get("width") or 0,
                height=best.get("height") or 0,
                duration=v.get("duration") or 0,
                license="Pexels License (uso livre, inclusive comercial; crédito apreciado)",
            )
        )
    return results


# --------------------------------------------------------------------------- #
# Pixabay
# --------------------------------------------------------------------------- #
def search_pixabay(query: str, api_key: str, per_page: int = 10) -> list[VideoResult]:
    if not api_key:
        return []
    resp = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": max(3, per_page)},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results: list[VideoResult] = []
    for hit in resp.json().get("hits", []):
        streams = hit.get("videos", {})
        # escolhe a melhor resolução disponível
        best = None
        for key in ("large", "medium", "small", "tiny"):
            s = streams.get(key)
            if s and s.get("url"):
                best = s
                break
        if not best:
            continue
        results.append(
            VideoResult(
                source="pixabay",
                title=hit.get("tags", "Pixabay video"),
                author=hit.get("user", "desconhecido"),
                page_url=hit.get("pageURL", ""),
                download_url=best.get("url", ""),
                width=best.get("width") or 0,
                height=best.get("height") or 0,
                duration=hit.get("duration") or 0,
                license="Pixabay Content License (uso livre, inclusive comercial)",
            )
        )
    return results


# --------------------------------------------------------------------------- #
# Internet Archive (domínio público)
# --------------------------------------------------------------------------- #
def search_archive(query: str, rows: int = 10) -> list[VideoResult]:
    """Busca itens de vídeo. Filtramos por coleções de domínio público.

    Ainda assim, confira a licença de cada item — o Archive hospeda material
    de licenças variadas.
    """
    resp = requests.get(
        "https://archive.org/advancedsearch.php",
        params={
            "q": f'({query}) AND mediatype:(movies)',
            "fl[]": ["identifier", "title", "creator"],
            "rows": rows,
            "output": "json",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])
    results: list[VideoResult] = []
    for d in docs:
        ident = d.get("identifier")
        if not ident:
            continue
        # tenta descobrir um arquivo .mp4 nos metadados do item
        try:
            meta = requests.get(
                f"https://archive.org/metadata/{ident}", timeout=TIMEOUT
            ).json()
        except requests.RequestException:
            continue
        mp4 = next(
            (f["name"] for f in meta.get("files", []) if f.get("name", "").lower().endswith(".mp4")),
            None,
        )
        if not mp4:
            continue
        creator = d.get("creator")
        if isinstance(creator, list):
            creator = ", ".join(creator)
        results.append(
            VideoResult(
                source="archive",
                title=d.get("title", ident) if not isinstance(d.get("title"), list) else d["title"][0],
                author=creator or "desconhecido",
                page_url=f"https://archive.org/details/{ident}",
                download_url=f"https://archive.org/download/{ident}/{mp4}",
                width=0,
                height=0,
                duration=0,
                license="Internet Archive — CONFIRA a licença do item (muitos são domínio público)",
            )
        )
    return results


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #
def download(video: VideoResult, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{video.source}-{_slug(video.title or video.author)}.mp4"
    path = dest_dir / name
    with requests.get(video.download_url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
    return path


def search_all(
    query: str,
    pexels_key: str = "",
    pixabay_key: str = "",
    use_archive: bool = False,
    per_source: int = 8,
) -> list[VideoResult]:
    """Roda todas as fontes configuradas e devolve os resultados agregados."""
    results: list[VideoResult] = []
    errors: list[str] = []
    for name, fn in (
        ("pexels", lambda: search_pexels(query, pexels_key, per_source)),
        ("pixabay", lambda: search_pixabay(query, pixabay_key, per_source)),
    ):
        try:
            results.extend(fn())
        except requests.RequestException as exc:  # pragma: no cover - rede
            errors.append(f"{name}: {exc}")
    if use_archive:
        try:
            results.extend(search_archive(query, per_source))
        except requests.RequestException as exc:  # pragma: no cover - rede
            errors.append(f"archive: {exc}")
    if errors:
        # anexa erros como atributo para a UI mostrar, sem quebrar o fluxo
        setattr(search_all, "last_errors", errors)
    return results
