"""Interface Streamlit do pipeline do canal.

Fluxo:
    1. Buscar vídeos em fontes com licença livre (Pexels, Pixabay, Archive)
    2. Baixar o clipe + gerar roteiro (IA), inclusive panorama de mercado
    3. Sintetizar voz + legendas sincronizadas (edge-tts)
    4. Montar o vídeo final (ffmpeg): legendas, Shorts 9:16 e trilha
    5. Gerar título, descrição e tags (SEO)

Execute com:  streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from canal import assemble, config, narrate, news, seo, sources, thumbnail, youtube

config.ensure_dirs()


def secret(name: str, default: str = "") -> str:
    """Lê de st.secrets (Streamlit Cloud) e cai para variável de ambiente."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return config.env(name, default)

st.set_page_config(page_title="Canal — Pipeline de vídeos", page_icon="🎬", layout="wide")
st.title("🎬 Pipeline de vídeos com licença livre + narração de IA")
st.caption(
    "Busca material **com licença livre**, adiciona narração original de IA e monta o vídeo. "
    "Sempre confira a licença de cada item antes de publicar."
)

# --------------------------------------------------------------------------- #
# Barra lateral: chaves e opções
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🔑 Chaves de API")
    pexels_key = st.text_input("Pexels API key", value=secret("PEXELS_API_KEY"), type="password")
    pixabay_key = st.text_input("Pixabay API key", value=secret("PIXABAY_API_KEY"), type="password")
    anthropic_key = st.text_input("Anthropic API key", value=secret("ANTHROPIC_API_KEY"), type="password")
    st.divider()
    st.header("⚙️ Opções")
    model = st.text_input("Modelo Claude", value=config.DEFAULT_ANTHROPIC_MODEL)
    voz = st.selectbox("Voz da narração", config.PT_BR_VOICES, index=1)
    usar_archive = st.checkbox("Incluir Internet Archive (domínio público)", value=False)
    st.caption(
        "Pexels e Pixabay têm chave gratuita. Sem chave, use o Internet Archive. "
        "A chave da Anthropic é necessária para gerar o roteiro."
    )
    if not assemble.ffmpeg_disponivel():
        st.warning("⚠️ ffmpeg não encontrado — a etapa de montagem final ficará indisponível.")

# --------------------------------------------------------------------------- #
# 1. Busca
# --------------------------------------------------------------------------- #
st.subheader("1) Buscar vídeos com licença livre")
col_q, col_btn = st.columns([4, 1])
query = col_q.text_input("Tema / palavra-chave", placeholder="ex.: natureza, cidade, café, oceano")
if col_btn.button("Buscar", use_container_width=True) and query:
    with st.spinner("Buscando..."):
        st.session_state["resultados"] = sources.search_all(
            query, pexels_key, pixabay_key, use_archive=usar_archive
        )
    erros = getattr(sources.search_all, "last_errors", None)
    if erros:
        st.warning("Algumas fontes falharam:\n\n" + "\n".join(f"- {e}" for e in erros))

resultados: list[sources.VideoResult] = st.session_state.get("resultados", [])
if resultados:
    st.write(f"**{len(resultados)}** resultado(s):")
    idx = st.radio(
        "Escolha um clipe",
        options=list(range(len(resultados))),
        format_func=lambda i: resultados[i].label,
    )
    escolhido = resultados[idx]
    st.info(f"📄 Licença: {escolhido.license}\n\n🔗 Fonte: {escolhido.page_url}")

    if st.button("⬇️ Baixar clipe selecionado"):
        with st.spinner("Baixando..."):
            caminho = sources.download(escolhido, config.DOWNLOAD_DIR)
        st.session_state["video_path"] = str(caminho)
        st.session_state["credito"] = f"{escolhido.author} — {escolhido.page_url}"
        st.success(f"Baixado: {caminho.name}")

video_path = st.session_state.get("video_path")
if video_path and Path(video_path).exists():
    st.video(video_path)

# --------------------------------------------------------------------------- #
# 2. Roteiro (IA)
# --------------------------------------------------------------------------- #
st.subheader("2) Gerar roteiro de narração (IA)")
col_a, col_b, col_c = st.columns(3)
tema_roteiro = col_a.text_input("Tema da narração", value=query or "")
duracao = col_b.number_input("Duração alvo (segundos)", min_value=15, max_value=600, value=60, step=15)
estilo = col_c.text_input("Estilo/tom", value="curiosidades, informativo e leve")

educativo = st.checkbox(
    "📈 Conteúdo financeiro educativo (bolsa/investimentos)",
    value=False,
    help="Mantém o roteiro didático, evita recomendar ativos específicos e "
    "adiciona um aviso de que não é recomendação de investimento (nicho YMYL).",
)
if educativo:
    st.caption(
        "Sugestões de tema seguras: *como funciona o home broker*, *o que é um "
        "dividendo*, *o que é o Ibovespa*, *renda fixa x renda variável*, "
        "*o que é um ETF*. Evite \"qual ação comprar agora\"."
    )

if st.button("✍️ Gerar roteiro"):
    try:
        with st.spinner("Escrevendo o roteiro..."):
            st.session_state["roteiro"] = narrate.gerar_roteiro(
                tema_roteiro, int(duracao), estilo, anthropic_key,
                model=model, educativo_financeiro=educativo,
            )
    except Exception as exc:  # mostra o erro de forma amigável
        st.error(str(exc))

with st.expander("📊 Panorama de mercado — dados e notícias do dia"):
    st.caption(
        "Busca **fatos** (cotações da B3 via brapi.dev) e **manchetes** (só os "
        "títulos, via RSS) e monta um contexto factual. A IA gera então um roteiro "
        "**educativo** — não vira recomendação de compra (regras da CVM). "
        "Você também pode colar dados do seu monitor da B3 direto no campo."
    )
    coln1, coln2 = st.columns(2)
    brapi_token = coln1.text_input("Token brapi.dev (opcional)", value=secret("BRAPI_TOKEN"), type="password")
    feed_url = coln2.text_input("Feed RSS de notícias", value=list(news.FEEDS_SUGERIDOS.values())[0])
    tickers_txt = st.text_input("Tickers para cotação (vírgula)", value="^BVSP, PETR4, VALE3, ITUB4")

    if st.button("🔎 Buscar dados e notícias do dia"):
        try:
            tickers = [t.strip() for t in tickers_txt.split(",") if t.strip()]
            with st.spinner("Buscando dados e manchetes..."):
                st.session_state["contexto_mercado"] = news.montar_contexto_do_dia(
                    tickers, feed_url, brapi_token
                )
            st.success("Contexto preenchido abaixo — revise antes de gerar.")
        except Exception as exc:
            st.error(str(exc))

    st.session_state.setdefault("contexto_mercado", "")
    contexto_mercado = st.text_area(
        "Contexto do mercado (fatos + manchetes)", key="contexto_mercado", height=200
    )
    if st.button("📈 Gerar panorama educativo") and contexto_mercado.strip():
        try:
            with st.spinner("Escrevendo o panorama..."):
                st.session_state["roteiro"] = narrate.gerar_panorama_educativo(
                    contexto_mercado, int(duracao), anthropic_key, model=model
                )
            st.success("Panorama gerado — veja/edite no campo de roteiro abaixo.")
        except Exception as exc:
            st.error(str(exc))

roteiro = st.text_area("Roteiro (edite à vontade)", value=st.session_state.get("roteiro", ""), height=200)
st.session_state["roteiro"] = roteiro

# --------------------------------------------------------------------------- #
# 3. Narração (TTS)
# --------------------------------------------------------------------------- #
st.subheader("3) Sintetizar a narração (voz) + legendas")
if st.button("🔊 Gerar áudio + legenda") and roteiro.strip():
    try:
        with st.spinner("Gerando voz e legendas sincronizadas..."):
            audio_path, srt_path = narrate.sintetizar_com_legendas(
                roteiro,
                voz,
                config.OUTPUT_DIR / "narracao.mp3",
                config.OUTPUT_DIR / "narracao.srt",
            )
        st.session_state["audio_path"] = str(audio_path)
        st.session_state["srt_path"] = str(srt_path)
        st.success("Narração e legenda (.srt) geradas.")
    except Exception as exc:
        st.error(str(exc))

audio_path = st.session_state.get("audio_path")
if audio_path and Path(audio_path).exists():
    st.audio(audio_path)
srt_path = st.session_state.get("srt_path")
if srt_path and Path(srt_path).exists():
    with open(srt_path, "rb") as fh:
        st.download_button("⬇️ Baixar legenda (.srt)", fh, file_name="narracao.srt")

# --------------------------------------------------------------------------- #
# 4. Montagem final
# --------------------------------------------------------------------------- #
st.subheader("4) Montar o vídeo final")
col_m1, col_m2, col_m3 = st.columns(3)
manter = col_m1.checkbox("Manter áudio original (como fundo)", value=True)
queimar_legenda = col_m2.checkbox("Queimar legendas", value=True)
vertical = col_m3.checkbox("Formato Shorts (9:16)", value=False)

musica_up = st.file_uploader(
    "Trilha de fundo (opcional — use áudio livre, ex.: Biblioteca de Áudio do YouTube)",
    type=["mp3", "wav", "m4a", "aac"],
)
musica_path = None
if musica_up is not None:
    musica_path = config.DOWNLOAD_DIR / f"trilha_{musica_up.name}"
    musica_path.write_bytes(musica_up.getbuffer())

if st.button("🎞️ Montar vídeo final"):
    if not (video_path and Path(video_path).exists()):
        st.error("Baixe um clipe primeiro (etapa 1).")
    elif not (audio_path and Path(audio_path).exists()):
        st.error("Gere a narração primeiro (etapa 3).")
    else:
        legenda = None
        if queimar_legenda and srt_path and Path(srt_path).exists():
            legenda = Path(srt_path)
        try:
            with st.spinner("Montando com ffmpeg..."):
                final = assemble.montar(
                    Path(video_path),
                    Path(audio_path),
                    config.OUTPUT_DIR / "video_final.mp4",
                    manter_audio_original=manter,
                    legenda=legenda,
                    vertical=vertical,
                    musica=musica_path,
                )
            st.session_state["final_path"] = str(final)
            st.success("Pronto!")
        except Exception as exc:
            st.error(str(exc))

final_path = st.session_state.get("final_path")
if final_path and Path(final_path).exists():
    st.video(final_path)
    with open(final_path, "rb") as fh:
        st.download_button("⬇️ Baixar vídeo final", fh, file_name="video_final.mp4", mime="video/mp4")
    descricao = ""
    if st.session_state.get("credito"):
        descricao += f"Imagens: {st.session_state['credito']}\n"
    if educativo:
        descricao += f"\n{narrate.AVISO_FINANCEIRO}\n"
    if descricao:
        st.caption("Crédito/aviso para colar na descrição do vídeo:")
        st.code(descricao, language="text")

# --------------------------------------------------------------------------- #
# 5. Metadados (SEO)
# --------------------------------------------------------------------------- #
st.subheader("5) Título, descrição e tags (SEO)")
if st.button("🏷️ Gerar metadados") and roteiro.strip():
    try:
        with st.spinner("Otimizando para busca..."):
            st.session_state["meta"] = seo.gerar_metadados(
                tema_roteiro or query,
                roteiro,
                anthropic_key,
                model=model,
                aviso_financeiro=narrate.AVISO_FINANCEIRO if educativo else None,
            )
    except Exception as exc:
        st.error(str(exc))

meta = st.session_state.get("meta", {})
titulo_final = st.text_input("Título", value=meta.get("titulo", tema_roteiro or query))
descricao_final = st.text_area("Descrição", value=meta.get("descricao", ""), height=160)
tags_txt = st.text_area(
    "Tags (separadas por vírgula)", value=", ".join(meta.get("tags", [])), height=80
)
tags_final = [t.strip() for t in tags_txt.split(",") if t.strip()]

# --------------------------------------------------------------------------- #
# 6. Thumbnail (capa)
# --------------------------------------------------------------------------- #
st.subheader("6) Gerar thumbnail (capa)")
titulo_thumb = st.text_input("Texto da capa", value=titulo_final)
if st.button("🖼️ Gerar thumbnail"):
    try:
        base_video = final_path or video_path
        with st.spinner("Criando capa..."):
            thumb = thumbnail.gerar_thumbnail(
                titulo_thumb,
                config.OUTPUT_DIR / "thumbnail.png",
                video=Path(base_video) if base_video and Path(base_video).exists() else None,
            )
        st.session_state["thumb_path"] = str(thumb)
        st.success("Thumbnail gerada.")
    except Exception as exc:
        st.error(str(exc))

thumb_path = st.session_state.get("thumb_path")
if thumb_path and Path(thumb_path).exists():
    st.image(thumb_path, caption="Prévia da thumbnail")
    with open(thumb_path, "rb") as fh:
        st.download_button("⬇️ Baixar thumbnail", fh, file_name="thumbnail.png", mime="image/png")

# --------------------------------------------------------------------------- #
# 7. Publicar no YouTube (API oficial)
# --------------------------------------------------------------------------- #
st.subheader("7) Publicar no YouTube")
st.caption(
    "Usa a API oficial do YouTube. No Streamlit Cloud, informe client_id, "
    "client_secret e refresh_token (gerados uma vez — veja o README). "
    "Comece sempre como **privado** para revisar antes de tornar público."
)
col_p1, col_p2 = st.columns(2)
yt_client_id = col_p1.text_input("Client ID", value=secret("YOUTUBE_CLIENT_ID"), type="password")
yt_client_secret = col_p2.text_input("Client Secret", value=secret("YOUTUBE_CLIENT_SECRET"), type="password")
yt_refresh = st.text_input("Refresh token", value=secret("YOUTUBE_REFRESH_TOKEN"), type="password")
privacidade = st.selectbox("Privacidade", ["private", "unlisted", "public"], index=0)

if st.button("🚀 Enviar para o YouTube"):
    if not (final_path and Path(final_path).exists()):
        st.error("Monte o vídeo final primeiro (etapa 4).")
    elif not (yt_client_id and yt_client_secret and yt_refresh):
        st.error("Informe client_id, client_secret e refresh_token.")
    else:
        try:
            with st.spinner("Autenticando e enviando..."):
                servico = youtube.servico_por_refresh_token(
                    yt_client_id, yt_client_secret, yt_refresh
                )
                resp = youtube.publicar(
                    servico,
                    Path(final_path),
                    titulo_final,
                    descricao_final,
                    tags=tags_final,
                    privacidade=privacidade,
                )
                video_id = resp.get("id")
                if thumb_path and Path(thumb_path).exists() and video_id:
                    try:
                        youtube.definir_thumbnail(servico, video_id, Path(thumb_path))
                    except Exception as exc_t:  # thumbnail exige canal verificado
                        st.warning(f"Vídeo enviado, mas a thumbnail falhou: {exc_t}")
            if video_id:
                st.success(f"Publicado! {youtube.url_do_video(video_id)}")
            else:
                st.warning("Envio concluído, mas não recebi o ID do vídeo.")
        except Exception as exc:
            st.error(f"Falha na publicação: {exc}")
