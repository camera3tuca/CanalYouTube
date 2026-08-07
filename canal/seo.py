"""Geração de metadados de SEO (título, descrição, tags) com IA.

Usa a API da Anthropic (Claude) para sugerir título chamativo, descrição
otimizada e tags a partir do tema/roteiro do vídeo.
"""
from __future__ import annotations

import json
import re

from .config import DEFAULT_ANTHROPIC_MODEL


def _extrai_json(texto: str) -> dict:
    """Extrai o primeiro objeto JSON de um texto (tolerante a code fences)."""
    m = re.search(r"\{.*\}", texto, re.DOTALL)
    if not m:
        raise RuntimeError("A resposta do modelo não continha JSON.")
    return json.loads(m.group(0))


def gerar_metadados(
    tema: str,
    roteiro: str,
    api_key: str,
    model: str = DEFAULT_ANTHROPIC_MODEL,
    aviso_financeiro: str | None = None,
) -> dict:
    """Devolve {'titulo': str, 'descricao': str, 'tags': list[str]}.

    Se `aviso_financeiro` for passado, ele é anexado ao fim da descrição.
    """
    if not api_key:
        raise RuntimeError("Chave da API da Anthropic ausente (ANTHROPIC_API_KEY).")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "Você é especialista em SEO de YouTube em português do Brasil. "
        "Com base no tema e no roteiro abaixo, gere metadados otimizados.\n\n"
        f"TEMA: {tema}\n\n"
        f"ROTEIRO:\n{roteiro[:4000]}\n\n"
        "Responda APENAS com um JSON válido no formato:\n"
        '{"titulo": "...", "descricao": "...", "tags": ["...", "..."]}\n'
        "- titulo: até 70 caracteres, chamativo e honesto (sem clickbait enganoso).\n"
        "- descricao: 2 a 4 parágrafos curtos, com um resumo e 3 a 5 hashtags no fim.\n"
        "- tags: 10 a 15 palavras-chave relevantes."
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou gerar os metadados. Ajuste o tema.")

    texto = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    ).strip()

    dados = _extrai_json(texto)
    dados.setdefault("titulo", tema)
    dados.setdefault("descricao", "")
    dados.setdefault("tags", [])
    if not isinstance(dados["tags"], list):
        dados["tags"] = [str(dados["tags"])]

    if aviso_financeiro:
        dados["descricao"] = f"{dados['descricao']}\n\n{aviso_financeiro}"

    return dados
