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

### Nicho financeiro (bolsa/investimentos)

Marque **"Conteúdo financeiro educativo"** na etapa 3 para o nicho de bolsa.
Isso mantém o roteiro **didático e imparcial**, evita recomendar ativos
específicos e adiciona automaticamente o aviso de que **não é recomendação de
investimento**.

⚠️ Conteúdo financeiro é "YMYL" (o YouTube e os anunciantes são mais rígidos) e,
no Brasil, recomendar compra/venda de ativos específicos sem credenciamento pode
esbarrar em regras da **CVM**. Prefira temas educativos ("como funciona o home
broker", "o que é dividendo", "o que é o Ibovespa") com o aviso incluído.

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
