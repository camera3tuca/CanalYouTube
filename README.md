# CanalYouTube

Pipeline em Python/Streamlit para produzir vídeos **monetizáveis** para um canal
do YouTube a partir de material com **licença livre**, adicionando **narração
original gerada por IA** (Claude) e **voz por TTS** (edge-tts), com montagem final
em **ffmpeg**.

## Por que assim (e não "baixar shows/vídeos aleatórios")

O YouTube só monetiza conteúdo que **você tem direito de usar** e ao qual você
**agrega valor original**. Baixar e reenviar vídeos de terceiros (shows, clipes
engraçados alheios) viola direito autoral e a regra de **"conteúdo reutilizado"**,
o que reprova o canal na monetização e pode gerar strikes.

Por isso este projeto integra **somente fontes com licença livre**:

| Fonte | Licença | Chave |
|-------|---------|-------|
| [Pexels](https://www.pexels.com/license/) | Uso livre, inclusive comercial | grátis |
| [Pixabay](https://pixabay.com/service/license-summary/) | Uso livre, inclusive comercial | grátis |
| [Internet Archive](https://archive.org) | Varia — muitos em domínio público | — |

E transforma o material com narração/comentário próprio (IA), o que o torna
**conteúdo original**. **Sempre confira a licença de cada item** antes de publicar.

## Instalação

```bash
pip install -r requirements.txt
# ffmpeg é necessário para a montagem final (não é pacote pip):
#   Debian/Ubuntu: sudo apt install ffmpeg
#   macOS:         brew install ffmpeg
```

## Chaves de API (gratuitas)

- **Pexels:** https://www.pexels.com/api/
- **Pixabay:** https://pixabay.com/api/docs/
- **Anthropic (Claude):** https://console.anthropic.com/ (necessária para o roteiro)

Defina como variáveis de ambiente (ou preencha na barra lateral do app):

```bash
export PEXELS_API_KEY=...
export PIXABAY_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Uso

```bash
streamlit run app.py
```

Fluxo na interface:

1. **Buscar** vídeos por tema nas fontes com licença livre.
2. **Baixar** o clipe escolhido.
3. **Gerar o roteiro** de narração com IA (edite à vontade).
4. **Sintetizar a voz + legenda** (edge-tts, vozes pt-BR, `.srt` sincronizado).
5. **Montar** o vídeo final (narração + legendas sobre as imagens) e baixar o `.mp4`.

### Recursos extras

- **Formato Shorts (9:16):** marque na etapa 4 para recorte vertical automático.
- **Trilha de fundo:** envie um áudio livre na etapa 4 (entra em loop, volume baixo).
- **SEO (etapa 5):** gera título, descrição e tags otimizados a partir do roteiro.
- **Thumbnail (etapa 6):** capa 1280×720 com o texto do título sobre um quadro do vídeo.
- **Publicar (etapa 7):** envio direto ao YouTube via API oficial (começa como privado).
- **Legendas:** `.srt` sincronizado com a fala, opcionalmente queimado no vídeo.

## Rodar no Streamlit Cloud

1. Suba este repositório e aponte o app para `app.py`.
2. O `packages.txt` já instala o **ffmpeg** no ambiente.
3. Em **Settings > Secrets**, cole o conteúdo de `.streamlit/secrets.toml.example`
   preenchido com suas chaves.

## Publicar no YouTube (API oficial)

1. No [Google Cloud Console](https://console.cloud.google.com/): crie um projeto,
   ative a **YouTube Data API v3** e gere uma credencial **OAuth (App para computador)**.
   Baixe o `client_secret.json`.
2. **Uma vez, na sua máquina**, gere o `refresh_token` (o servidor do Streamlit
   Cloud não abre navegador):

   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file(
       "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
   creds = flow.run_local_server(port=0)
   print("REFRESH TOKEN:", creds.refresh_token)
   ```

3. Guarde `client_id`, `client_secret` e `refresh_token` nos *secrets* do Streamlit
   (chaves `YOUTUBE_*` do exemplo). A etapa 7 do app usa esses valores.

> Comece sempre com privacidade **privada** para revisar o vídeo antes de publicar.
> Definir thumbnail pela API exige canal verificado.

### Nicho financeiro (bolsa/investimentos)

Marque **"Conteúdo financeiro educativo"** na etapa 3 para o nicho de bolsa.
Isso mantém o roteiro **didático e imparcial**, evita recomendar ativos
específicos e adiciona automaticamente o aviso de que **não é recomendação de
investimento**.

**Panorama de mercado (dados e notícias do dia):** no painel "Panorama de
mercado" o app busca **fatos** (cotações da B3 via [brapi.dev](https://brapi.dev),
chave gratuita) e **manchetes** (só os títulos, via RSS de portais que oferecem
feed) e monta um contexto factual; a IA gera um roteiro **educativo** a partir
dele. Você também pode colar dados do seu monitor da B3 no mesmo campo.

> ⚠️ **Não faça scraping de portais como TradingView/Investing** — o conteúdo é
> protegido e os Termos de Uso proíbem cópia/redistribuição. Fatos (números) e
> manchetes (títulos + link) são fontes legítimas; o texto dos artigos, não.
> Por decisão de projeto, o app **não** converte "ações com possibilidade de
> compra" em recomendação pública.

⚠️ Conteúdo financeiro é "YMYL" (o YouTube e os anunciantes são mais rígidos) e,
no Brasil, recomendar compra/venda de ativos específicos ao público sem
credenciamento pode esbarrar em regras da **CVM**. Prefira temas educativos
("como funciona o home broker", "o que é dividendo", "o que é o Ibovespa") com o
aviso incluído. Use o monitor como fonte de **contexto e ideias**, não como
lista de recomendações num vídeo.

## Estrutura

```
app.py              # interface Streamlit
canal/
  config.py         # chaves e diretórios
  sources.py        # busca e download (Pexels, Pixabay, Archive)
  narrate.py        # roteiro (Claude) + voz (edge-tts)
  assemble.py       # montagem com ffmpeg
```

## Boas práticas para monetizar

- **Agregue valor**: narração, curadoria com contexto, edição — não só repostar.
- **Credite as fontes** na descrição do vídeo (o app sugere o texto de crédito).
- Use áudio da **Biblioteca de Áudio do YouTube** se quiser trilha musical.
- Verifique a **licença individual** de cada clipe, sobretudo no Internet Archive.
