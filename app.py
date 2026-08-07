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

from canal import assemble, config, narrate, seo, sources

config.ensure_dirs()

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
    pexels_key = st.text_input("Pexels API key", value=config.env("PEXELS_API_KEY"), type="password")
    pixabay_key = st.text_input("Pixabay API key", value=config.env("PIXABAY_API_KEY"), type="password")
    anthropic_key = st.text_input("Anthropic API key", value=config.env("ANTHROPIC_API_KEY"), type="password")
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

with st.expander("📊 Panorama de mercado (a partir do seu monitor da B3)"):
    st.caption(
        "Cole aqui um resumo/JSON do seu monitor (ex.: variação do Ibovespa, "
        "setores em alta/baixa, notícias). A IA gera um roteiro **educativo** — "
        "**não** transforma 'ações com possibilidade de compra' em recomendação, "
        "por causa das regras da CVM."
    )
    contexto_mercado = st.text_area(
        "Contexto do mercado", height=140,
        placeholder="Ibovespa fechou em alta de 0,8% aos 130.000 pontos. "
        "Setor bancário puxou o índice; commodities recuaram. ...",
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

meta = st.session_state.get("meta")
if meta:
    st.text_input("Título", value=meta.get("titulo", ""))
    st.text_area("Descrição", value=meta.get("descricao", ""), height=160)
    tags = meta.get("tags", [])
    st.text_area("Tags (separadas por vírgula)", value=", ".join(tags), height=80)
