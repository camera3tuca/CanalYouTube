"""Notícias e dados do dia para roteiros EDUCATIVOS de mercado.

Princípio: fatos não têm direito autoral, mas o texto tem. Por isso:

    - DADOS DE MERCADO (cotações, altas/baixas) vêm de APIs livres (brapi.dev).
    - MANCHETES vêm de RSS — coletamos apenas TÍTULO + LINK, nunca o texto
      completo do artigo. RSS existe para sindicância de manchetes.

Com isso a IA escreve um comentário ORIGINAL sobre os fatos, o que é
transformativo e adequado para monetização.

NÃO faça scraping de portais como TradingView/Investing: o conteúdo é protegido
e os Termos de Uso proíbem cópia/redistribuição. Use as fontes abaixo.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import quote

import requests

TIMEOUT = 20

# Feeds RSS sugeridos (confira/ajuste — URLs de feed mudam com o tempo)
FEEDS_SUGERIDOS = {
    "InfoMoney — Mercados": "https://www.infomoney.com.br/mercados/feed/",
    "InfoMoney — Onde Investir": "https://www.infomoney.com.br/onde-investir/feed/",
}


def _pct(v) -> str:
    try:
        return f"{float(v):+.2f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "?"


def cotacoes_brapi(tickers: list[str], token: str = "") -> list[dict]:
    """Cotações da B3 via brapi.dev. `^BVSP` = Ibovespa."""
    if not tickers:
        return []
    caminho = quote(",".join(tickers), safe=",^")
    params = {"token": token} if token else {}
    resp = requests.get(f"https://brapi.dev/api/quote/{caminho}", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    saida = []
    for r in resp.json().get("results", []):
        saida.append(
            {
                "simbolo": r.get("symbol", "?"),
                "nome": r.get("shortName") or r.get("longName") or r.get("symbol", ""),
                "preco": r.get("regularMarketPrice"),
                "variacao": r.get("regularMarketChangePercent"),
            }
        )
    return saida


def movers_brapi(token: str = "", limite: int = 5, alta: bool = True) -> list[dict]:
    """Maiores altas (alta=True) ou baixas do dia via brapi.dev."""
    params = {
        "sortBy": "change",
        "sortOrder": "desc" if alta else "asc",
        "limit": limite,
    }
    if token:
        params["token"] = token
    resp = requests.get("https://brapi.dev/api/quote/list", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    saida = []
    for s in resp.json().get("stocks", [])[:limite]:
        saida.append(
            {
                "simbolo": s.get("stock", "?"),
                "nome": s.get("name", ""),
                "variacao": s.get("change"),
            }
        )
    return saida


def manchetes_rss(feed_url: str, limite: int = 8) -> list[dict]:
    """Títulos + links de um feed RSS/Atom (apenas manchetes, sem o texto)."""
    import feedparser

    feed = feedparser.parse(feed_url)
    saida = []
    for e in feed.entries[:limite]:
        saida.append(
            {
                "titulo": getattr(e, "title", "").strip(),
                "link": getattr(e, "link", ""),
                "publicado": getattr(e, "published", ""),
            }
        )
    return saida


def montar_contexto_do_dia(
    tickers: list[str],
    feed_url: str = "",
    token: str = "",
    n_movers: int = 5,
    n_manchetes: int = 8,
) -> str:
    """Reúne dados + manchetes num texto factual para o gerador de panorama.

    Cada fonte é tolerante a falha: se uma cair, as demais continuam e um
    aviso é anexado ao fim.
    """
    linhas = [f"DADOS DE MERCADO (fatos, {date.today().isoformat()}):"]
    erros: list[str] = []

    try:
        for c in cotacoes_brapi(tickers, token):
            preco = c["preco"]
            preco_txt = f"{preco:.2f}".replace(".", ",") if isinstance(preco, (int, float)) else "?"
            linhas.append(f"- {c['simbolo']} ({c['nome']}): {preco_txt} ({_pct(c['variacao'])})")
    except requests.RequestException as exc:
        erros.append(f"cotações: {exc}")

    try:
        altas = movers_brapi(token, n_movers, alta=True)
        if altas:
            linhas.append(
                "Maiores altas: "
                + ", ".join(f"{m['simbolo']} ({_pct(m['variacao'])})" for m in altas)
            )
    except requests.RequestException as exc:
        erros.append(f"altas: {exc}")

    try:
        baixas = movers_brapi(token, n_movers, alta=False)
        if baixas:
            linhas.append(
                "Maiores baixas: "
                + ", ".join(f"{m['simbolo']} ({_pct(m['variacao'])})" for m in baixas)
            )
    except requests.RequestException as exc:
        erros.append(f"baixas: {exc}")

    if feed_url:
        try:
            manchetes = manchetes_rss(feed_url, n_manchetes)
            if manchetes:
                linhas.append("\nMANCHETES DO DIA (apenas títulos, para contexto):")
                for m in manchetes:
                    linhas.append(f"- {m['titulo']}")
        except Exception as exc:  # feedparser é tolerante, mas por segurança
            erros.append(f"manchetes: {exc}")

    if erros:
        linhas.append("\n(Observação: algumas fontes falharam: " + "; ".join(erros) + ")")

    return "\n".join(linhas)
