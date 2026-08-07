"""Bridge com o monitor de quedas de BDRs (rastreador pessoal).

Lê uma EXPORTAÇÃO (CSV ou JSON) do rastreador — as colunas do painel:
Ticker, Empresa, Queda_Dia, IS (Índice de Sobrevenda), Potencial/Sinal,
Score/Força, Sinais — e monta um CONTEXTO EDUCATIVO AGREGADO para o gerador
de panorama.

Decisão de projeto (importante): este bridge **não** reproduz o ranking de
"melhores oportunidades" como recomendação. Ele produz apenas estatísticas do
dia e a frequência dos sinais técnicos, para o canal explicar CONCEITOS
(o que é o IS, o que é RSI sobrevendido, como se pensa uma reversão). O próprio
monitor deixa claro que é "um rastreador, não recomendação de compra".

Como exportar do monitor: adicione um botão no app do rastreador, por exemplo
    st.download_button("Baixar CSV", df_res.to_csv(index=False), "bdrs.csv")
e use o arquivo gerado aqui.
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import date

# nomes de coluna aceitos (tolerante a variações)
COL_TICKER = ("Ticker", "ticker")
COL_QUEDA = ("Queda_Dia", "Queda", "queda")
COL_IS = ("IS", "I.S.", "is")
COL_SINAIS = ("Sinais", "Sinais Técnicos", "sinais")


def _get(row: dict, nomes: tuple[str, ...], default=""):
    for n in nomes:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return default


def _num(v) -> float | None:
    """Converte '−2,10%' / '3.5' / 42 em float; None se não der."""
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip().replace("%", "").replace("−", "-").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def carregar_export(conteudo: bytes | str, nome: str = "") -> list[dict]:
    """Lê CSV ou JSON (bytes ou str) e devolve uma lista de dicionários."""
    if isinstance(conteudo, bytes):
        conteudo = conteudo.decode("utf-8", errors="replace")
    nome = nome.lower()
    if nome.endswith(".json") or conteudo.lstrip().startswith(("[", "{")):
        dados = json.loads(conteudo)
        if isinstance(dados, dict):  # ex.: {"data": [...]} ou dict de colunas
            for chave in ("data", "rows", "results"):
                if isinstance(dados.get(chave), list):
                    return dados[chave]
            return [dados]
        return dados
    return list(csv.DictReader(io.StringIO(conteudo)))


def contexto_educativo(rows: list[dict]) -> str:
    """Monta um contexto factual/agregado (sem ranking de compra)."""
    if not rows:
        return "Nenhum dado no arquivo do rastreador."

    quedas = [q for q in (_num(_get(r, COL_QUEDA)) for r in rows) if q is not None]
    is_vals = [i for i in (_num(_get(r, COL_IS)) for r in rows) if i is not None]

    contagem = Counter()
    for r in rows:
        sinais = _get(r, COL_SINAIS)
        if isinstance(sinais, str):
            for parte in sinais.replace(";", ",").split(","):
                parte = parte.strip()
                if parte:
                    contagem[parte] += 1

    linhas = [f"DADOS DO RASTREADOR DE BDRs (educativo, {date.today().isoformat()}):"]
    linhas.append(f"- BDRs em queda listadas hoje: {len(rows)}")
    if quedas:
        media_q = sum(quedas) / len(quedas)
        linhas.append(
            f"- Queda média: {media_q:.2f}% | maior queda: {min(quedas):.2f}%".replace(".", ",")
        )
    if is_vals:
        media_is = sum(is_vals) / len(is_vals)
        linhas.append(
            f"- Índice de Sobrevenda (IS) médio: {media_is:.0f} | máximo: {max(is_vals):.0f}"
        )
    if contagem:
        top = ", ".join(f"{sinal} ({n})" for sinal, n in contagem.most_common(6))
        linhas.append(f"- Sinais técnicos mais frequentes: {top}")

    linhas.append(
        "\nObservação: isto é um RASTREADOR (screener), não recomendação de compra. "
        "Use os dados apenas para explicar CONCEITOS de análise (o que é o Índice de "
        "Sobrevenda, RSI sobrevendido, como se avalia uma possível reversão) — sem "
        "indicar ativos específicos para comprar."
    )
    return "\n".join(linhas)


def contexto_de_arquivo(conteudo: bytes | str, nome: str = "") -> str:
    """Atalho: carrega o export e devolve o contexto educativo."""
    return contexto_educativo(carregar_export(conteudo, nome))
