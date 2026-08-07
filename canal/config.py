"""Configuração central: chaves de API e diretórios de trabalho.

As chaves podem vir de variáveis de ambiente ou serem passadas pela interface.
Nunca escreva chaves diretamente no código — use um arquivo .env (ignorado pelo git)
ou os campos da barra lateral do Streamlit.
"""
from __future__ import annotations

import os
from pathlib import Path

# Diretórios de trabalho (criados sob demanda)
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"


def ensure_dirs() -> None:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# Modelo padrão da API da Anthropic para gerar roteiros de narração.
# Pode ser trocado na interface; use um dos IDs válidos da API.
DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"

# Vozes de exemplo do edge-tts (pt-BR). Liste todas com: `edge-tts --list-voices`.
PT_BR_VOICES = [
    "pt-BR-AntonioNeural",
    "pt-BR-FranciscaNeural",
    "pt-BR-ThalitaNeural",
]
