"""Geração de roteiro (IA) e narração (TTS).

- gerar_roteiro(): usa a API da Anthropic (Claude) para escrever o texto que
  transforma o vídeo em conteúdo original (comentário, curiosidades, história).
- sintetizar_voz(): converte o texto em áudio com o edge-tts (gratuito, offline
  quanto a chave, mas requer acesso à internet).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .config import DEFAULT_ANTHROPIC_MODEL


SYSTEM_PROMPT = (
    "Você é roteirista de um canal de YouTube em português do Brasil. "
    "Escreve narrações originais, envolventes e faladas de forma natural, "
    "para serem lidas em voz alta sobre imagens. Não use marcações, títulos, "
    "colchetes de cena nem emojis — apenas o texto corrido a ser narrado."
)


def gerar_roteiro(
    tema: str,
    duracao_seg: int,
    estilo: str,
    api_key: str,
    model: str = DEFAULT_ANTHROPIC_MODEL,
) -> str:
    """Gera o texto da narração via API da Anthropic.

    Levanta RuntimeError se a chave faltar ou se o modelo recusar o conteúdo.
    """
    if not api_key:
        raise RuntimeError("Chave da API da Anthropic ausente (ANTHROPIC_API_KEY).")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # ~150 palavras por minuto de narração é uma média confortável em pt-BR.
    palavras = max(40, int(duracao_seg / 60 * 150))

    prompt = (
        f"Escreva uma narração de aproximadamente {palavras} palavras "
        f"(~{duracao_seg} segundos falados) sobre o tema: \"{tema}\".\n"
        f"Estilo/tom: {estilo}.\n"
        "A narração deve ter começo, meio e fim, prender a atenção nos "
        "primeiros segundos e terminar com uma chamada para se inscrever no canal. "
        "Devolva apenas o texto a ser narrado, sem títulos nem instruções de cena."
    )

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(
            "O modelo recusou gerar este roteiro por política de conteúdo. "
            "Ajuste o tema/estilo e tente de novo."
        )

    partes = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    texto = "\n".join(partes).strip()
    if not texto:
        raise RuntimeError("O modelo não devolveu texto utilizável.")
    return texto


async def _tts(texto: str, voz: str, destino: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(str(destino))


def sintetizar_voz(texto: str, voz: str, destino: Path) -> Path:
    """Gera um arquivo de áudio (mp3) a partir do texto usando edge-tts."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_tts(texto, voz, destino))
    return destino
