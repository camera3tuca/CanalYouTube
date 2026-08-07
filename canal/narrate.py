"""Geração de roteiro (IA), narração (TTS) e legendas sincronizadas.

- gerar_roteiro(): usa a API da Anthropic (Claude) para escrever o texto que
  transforma o vídeo em conteúdo original (comentário, curiosidades, aula).
- sintetizar_voz(): converte o texto em áudio com o edge-tts.
- sintetizar_com_legendas(): gera o áudio E um arquivo .srt sincronizado,
  usando os eventos de limite de palavra do edge-tts.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .config import DEFAULT_ANTHROPIC_MODEL

AVISO_FINANCEIRO = (
    "Este conteúdo é educativo e informativo e não constitui recomendação de "
    "investimento. Consulte um profissional certificado antes de investir."
)

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
    educativo_financeiro: bool = False,
) -> str:
    """Gera o texto da narração via API da Anthropic.

    Se educativo_financeiro=True, instrui o modelo a manter o conteúdo
    educativo, evitar recomendações de ativos específicos e encerrar com um
    aviso de que não é recomendação de investimento (importante para o nicho
    de bolsa: mais seguro para monetização e para as regras da CVM).

    Levanta RuntimeError se a chave faltar ou se o modelo recusar o conteúdo.
    """
    if not api_key:
        raise RuntimeError("Chave da API da Anthropic ausente (ANTHROPIC_API_KEY).")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # ~150 palavras por minuto de narração é uma média confortável em pt-BR.
    palavras = max(40, int(duracao_seg / 60 * 150))

    regras_financeiras = ""
    if educativo_financeiro:
        regras_financeiras = (
            "\nEste é um vídeo EDUCATIVO sobre mercado financeiro. Regras obrigatórias:\n"
            "- Explique conceitos de forma didática e imparcial.\n"
            "- NÃO recomende comprar ou vender ativos específicos, nem prometa retornos.\n"
            "- NÃO dê conselho financeiro personalizado.\n"
            f"- Encerre com um aviso curto e natural equivalente a: \"{AVISO_FINANCEIRO}\"\n"
        )

    prompt = (
        f"Escreva uma narração de aproximadamente {palavras} palavras "
        f"(~{duracao_seg} segundos falados) sobre o tema: \"{tema}\".\n"
        f"Estilo/tom: {estilo}.\n"
        "A narração deve ter começo, meio e fim, prender a atenção nos "
        "primeiros segundos e terminar com uma chamada para se inscrever no canal."
        f"{regras_financeiras}"
        "\nDevolva apenas o texto a ser narrado, sem títulos nem instruções de cena."
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


def gerar_panorama_educativo(
    contexto_mercado: str,
    duracao_seg: int,
    api_key: str,
    model: str = DEFAULT_ANTHROPIC_MODEL,
) -> str:
    """Gera um roteiro EDUCATIVO de panorama de mercado.

    `contexto_mercado` é texto/JSON livre com dados gerais (ex.: variação do
    Ibovespa, setores em alta/baixa, notícias). Pode vir do seu monitor da B3.

    Guardrails: o roteiro explica o que os movimentos significam de forma
    didática e NÃO recomenda comprar/vender ativos específicos — mesmo que o
    contexto traga "sinais de compra", eles são tratados apenas como exemplo de
    como analistas leem o mercado, sempre com aviso de que não é recomendação.
    """
    if not api_key:
        raise RuntimeError("Chave da API da Anthropic ausente (ANTHROPIC_API_KEY).")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    palavras = max(60, int(duracao_seg / 60 * 150))

    prompt = (
        "Você faz um panorama EDUCATIVO do mercado financeiro brasileiro para o "
        "YouTube. Use os dados abaixo apenas como contexto factual.\n\n"
        f"DADOS DE CONTEXTO (do monitor da B3):\n{contexto_mercado[:4000]}\n\n"
        f"Escreva ~{palavras} palavras (~{duracao_seg}s falados). Regras:\n"
        "- Explique o que os movimentos gerais significam de forma didática.\n"
        "- NÃO diga para o espectador comprar ou vender nenhum ativo específico.\n"
        "- Se o contexto listar 'ações com possibilidade de compra', NÃO as "
        "apresente como recomendação; no máximo explique, de forma genérica, "
        "quais critérios costumam ser observados numa análise.\n"
        "- NÃO prometa retornos.\n"
        f"- Encerre com um aviso natural equivalente a: \"{AVISO_FINANCEIRO}\"\n"
        "Devolva apenas o texto a ser narrado, sem títulos nem marcações."
    )

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou gerar este panorama. Ajuste o contexto.")

    texto = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    ).strip()
    if not texto:
        raise RuntimeError("O modelo não devolveu texto utilizável.")
    return texto


# --------------------------------------------------------------------------- #
# TTS + legendas
# --------------------------------------------------------------------------- #
def _srt_time(ticks_100ns: int) -> str:
    """Converte ticks de 100 ns (formato do edge-tts) para 'HH:MM:SS,mmm'."""
    total = ticks_100ns / 10_000_000  # segundos
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = int(total % 60)
    ms = int(round((total - int(total)) * 1000))
    if ms == 1000:  # arredondamento
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _srt_de_palavras(palavras: list[dict], por_cue: int = 8) -> str:
    """Monta um SRT agrupando palavras em blocos curtos.

    Cada palavra é um dict com 'offset', 'duration' (ticks de 100 ns) e 'text'.
    Fecha o bloco a cada `por_cue` palavras ou quando a palavra termina frase.
    """
    cues: list[tuple[int, int, str]] = []
    buffer: list[dict] = []

    def fecha():
        if not buffer:
            return
        inicio = buffer[0]["offset"]
        fim = buffer[-1]["offset"] + buffer[-1]["duration"]
        texto = " ".join(p["text"] for p in buffer)
        cues.append((inicio, fim, texto))
        buffer.clear()

    for p in palavras:
        buffer.append(p)
        termina_frase = p["text"].endswith((".", "!", "?", "…"))
        if len(buffer) >= por_cue or termina_frase:
            fecha()
    fecha()

    linhas = []
    for i, (inicio, fim, texto) in enumerate(cues, start=1):
        linhas.append(str(i))
        linhas.append(f"{_srt_time(inicio)} --> {_srt_time(fim)}")
        linhas.append(texto)
        linhas.append("")
    return "\n".join(linhas)


async def _tts_stream(texto: str, voz: str, destino_audio: Path) -> list[dict]:
    """Gera o áudio e devolve a lista de limites de palavra (WordBoundary)."""
    import edge_tts

    palavras: list[dict] = []
    communicate = edge_tts.Communicate(texto, voz)
    with open(destino_audio, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                palavras.append(
                    {
                        "offset": chunk["offset"],
                        "duration": chunk["duration"],
                        "text": chunk["text"],
                    }
                )
    return palavras


def sintetizar_com_legendas(
    texto: str, voz: str, destino_audio: Path, destino_srt: Path
) -> tuple[Path, Path]:
    """Gera o áudio (mp3) e um .srt sincronizado a partir do texto."""
    destino_audio.parent.mkdir(parents=True, exist_ok=True)
    palavras = asyncio.run(_tts_stream(texto, voz, destino_audio))
    srt = _srt_de_palavras(palavras)
    destino_srt.write_text(srt, encoding="utf-8")
    return destino_audio, destino_srt


def sintetizar_voz(texto: str, voz: str, destino: Path) -> Path:
    """Gera apenas o áudio (mp3), sem legendas."""
    destino.parent.mkdir(parents=True, exist_ok=True)

    async def _run():
        import edge_tts

        await edge_tts.Communicate(texto, voz).save(str(destino))

    asyncio.run(_run())
    return destino
