"""Publicação de vídeos no YouTube via API oficial (Data API v3).

Dois modos de autenticação:

1. Refresh token (recomendado no Streamlit Cloud / servidores sem navegador):
   guarde client_id, client_secret e refresh_token nos *secrets* e chame
   `servico_por_refresh_token(...)`.

2. Fluxo local com navegador (rodando na sua máquina): use
   `servico_local(client_secret.json, token.json)` — abre o navegador uma vez
   e salva o token para as próximas execuções.

Bibliotecas Google são importadas de forma preguiçosa, então o app roda mesmo
sem elas instaladas (só a etapa de publicação fica indisponível).
"""
from __future__ import annotations

from pathlib import Path

ESCOPOS = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def servico_por_refresh_token(client_id: str, client_secret: str, refresh_token: str):
    """Cria o serviço do YouTube a partir de um refresh token (sem navegador)."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=TOKEN_URI,
        scopes=ESCOPOS,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def servico_local(client_secret_file: Path, token_file: Path):
    """Fluxo OAuth local (abre o navegador). Salva/reusa o token em disco."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), ESCOPOS)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), ESCOPOS)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def publicar(
    servico,
    arquivo: Path,
    titulo: str,
    descricao: str,
    tags: list[str] | None = None,
    privacidade: str = "private",   # private | unlisted | public
    categoria: str = "22",           # 22 = People & Blogs
    para_criancas: bool = False,
) -> dict:
    """Faz o upload (resumable) e devolve o recurso do vídeo criado."""
    from googleapiclient.http import MediaFileUpload

    corpo = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao,
            "tags": tags or [],
            "categoryId": categoria,
        },
        "status": {
            "privacyStatus": privacidade,
            "selfDeclaredMadeForKids": para_criancas,
        },
    }
    media = MediaFileUpload(str(arquivo), chunksize=-1, resumable=True)
    req = servico.videos().insert(part="snippet,status", body=corpo, media_body=media)

    resposta = None
    while resposta is None:
        _, resposta = req.next_chunk()
    return resposta


def definir_thumbnail(servico, video_id: str, thumbnail: Path) -> None:
    from googleapiclient.http import MediaFileUpload

    servico.thumbnails().set(
        videoId=video_id, media_body=MediaFileUpload(str(thumbnail))
    ).execute()


def url_do_video(video_id: str) -> str:
    return f"https://youtu.be/{video_id}"
