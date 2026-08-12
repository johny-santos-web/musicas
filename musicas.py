import io
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import imageio_ffmpeg
import streamlit as st
import yt_dlp


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Music Downloader",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at top left,
                #312e81 0%,
                transparent 35%
            ),
            radial-gradient(
                circle at bottom right,
                #581c87 0%,
                transparent 35%
            ),
            #0f172a;
    }

    .main-title {
        text-align: center;
        font-size: 46px;
        font-weight: 800;
        color: white;
        margin-top: 20px;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #cbd5e1;
        font-size: 18px;
        margin-bottom: 30px;
    }

    div.stButton > button {
        border-radius: 12px;
        font-weight: 700;
        min-height: 45px;
    }

    div.stDownloadButton > button {
        border-radius: 12px;
        font-weight: 700;
        min-height: 45px;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "musicas" not in st.session_state:
    st.session_state.musicas = []

if "cantor" not in st.session_state:
    st.session_state.cantor = ""

if "selecionadas" not in st.session_state:
    st.session_state.selecionadas = set()

if "arquivos_baixados" not in st.session_state:
    st.session_state.arquivos_baixados = []

if "zip_bytes" not in st.session_state:
    st.session_state.zip_bytes = None


# ============================================================
# PALAVRAS QUE DEVEM SER EVITADAS
# ============================================================

PALAVRAS_EVITAR = [
    "live",
    "ao vivo",
    "cover",
    "karaoke",
    "karaokê",
    "instrumental",
    "sped up",
    "slowed",
    "slowed reverb",
    "remix",
    "reaction",
    "reação",
    "fan made",
    "fanmade",
    "tribute",
    "tributo",
    "8d audio",
    "dj set",
    "mashup",
    "mix",
    "medley",
    "playlist",
    "compilação",
    "compilacao",
    "concerto",
    "show",
    "performance",
]


# ============================================================
# NORMALIZA TEXTO
# ============================================================

def normalizar_texto(texto):

    if not texto:
        return ""

    texto = str(texto).lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ö": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }

    for origem, destino in substituicoes.items():
        texto = texto.replace(origem, destino)

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================
# TÍTULO INDESEJADO
# ============================================================

def titulo_indesejado(titulo):

    texto = normalizar_texto(titulo)

    for palavra in PALAVRAS_EVITAR:

        palavra_normalizada = normalizar_texto(
            palavra
        )

        if palavra_normalizada in texto:
            return True

    return False


# ============================================================
# LIMPA TÍTULO
# ============================================================

def limpar_titulo_musica(titulo, cantor):

    resultado = str(titulo or "").strip()
    artista = str(cantor or "").strip()

    if artista:

        padroes_artista = [
            rf"^{re.escape(artista)}\s*[-–—:]\s*",
            rf"^{re.escape(artista)}\s+",
        ]

        for padrao in padroes_artista:

            resultado = re.sub(
                padrao,
                "",
                resultado,
                flags=re.IGNORECASE,
            )

    extras = [
        r"pseudo\s*video",
        r"pseudo\s*vídeo",
        r"official\s*video",
        r"official\s*audio",
        r"official",
        r"audio\s*oficial",
        r"áudio\s*oficial",
        r"audio",
        r"áudio",
        r"legendado",
        r"lyrics?",
        r"vídeo",
        r"video",
        r"hd",
        r"4k",
    ]

    mudou = True

    while mudou:

        antes = resultado

        for palavra in extras:

            resultado = re.sub(
                rf"\(\s*{palavra}\s*\)",
                "",
                resultado,
                flags=re.IGNORECASE,
            )

            resultado = re.sub(
                rf"\[\s*{palavra}\s*\]",
                "",
                resultado,
                flags=re.IGNORECASE,
            )

        mudou = resultado != antes

    resultado = re.sub(
        r"\(\s*\)",
        "",
        resultado,
    )

    resultado = re.sub(
        r"\[\s*\]",
        "",
        resultado,
    )

    resultado = re.sub(
        r"\s+",
        " ",
        resultado,
    )

    resultado = resultado.strip(
        " -–—:[]()"
    )

    return resultado.strip()


# ============================================================
# FORMATA VISUALIZAÇÕES
# ============================================================

def formatar_visualizacoes(numero):

    if not numero:
        return "0"

    try:
        numero = int(numero)
    except Exception:
        return "0"

    if numero >= 1_000_000_000:
        return f"{numero / 1_000_000_000:.1f} bilhões"

    if numero >= 1_000_000:
        return f"{numero / 1_000_000:.1f} milhões"

    if numero >= 1_000:
        return f"{numero / 1_000:.1f} mil"

    return str(numero)


# ============================================================
# FFmpeg
# ============================================================

def obter_executavel_ffmpeg():

    try:

        caminho = imageio_ffmpeg.get_ffmpeg_exe()

        if caminho and Path(caminho).exists():
            return caminho

    except Exception:
        pass

    caminho = shutil.which("ffmpeg")

    if caminho:
        return caminho

    return None


# ============================================================
# ARTISTA CORRESPONDE
# ============================================================

def artista_corresponde(
    cantor,
    titulo,
    uploader,
    canal,
):

    artista = normalizar_texto(cantor)

    titulo_n = normalizar_texto(titulo)
    uploader_n = normalizar_texto(uploader)
    canal_n = normalizar_texto(canal)

    texto = (
        f"{titulo_n} "
        f"{uploader_n} "
        f"{canal_n}"
    )

    palavras = [
        palavra
        for palavra in artista.split()
        if len(palavra) > 2
    ]

    if not palavras:
        return False, 0

    if artista in titulo_n:
        return True, 100

    if artista in uploader_n:
        return True, 150

    if artista in canal_n:
        return True, 150

    correspondencias = sum(
        1
        for palavra in palavras
        if palavra in texto
    )

    if len(palavras) >= 2:

        if correspondencias >= len(palavras):
            return True, correspondencias * 30

        return False, 0

    if correspondencias >= 1:
        return True, 20

    return False, 0


# ============================================================
# PESQUISA
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=600,
)
def pesquisar_musicas(cantor):

    opcoes = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
    }

    pesquisas = [
        f'"{cantor}"',
        f'"{cantor}" músicas',
        f'"{cantor}" melhores músicas',
        f'"{cantor}" sucessos',
        f'"{cantor}" canções',
    ]

    candidatos = []

    for consulta in pesquisas:

        try:

            with yt_dlp.YoutubeDL(opcoes) as ydl:

                resultado = ydl.extract_info(
                    f"ytsearch30:{consulta}",
                    download=False,
                )

            if not resultado:
                continue

            videos = resultado.get(
                "entries",
                [],
            )

            for video in videos:

                if video:
                    candidatos.append(video)

        except Exception:
            continue

    if not candidatos:
        return []

    cantor_normalizado = normalizar_texto(
        cantor
    )

    musicas = []

    ids_vistos = set()
    nomes_vistos = set()

    for video in candidatos:

        if not video:
            continue

        video_id = video.get("id")

        if not video_id:
            continue

        if video_id in ids_vistos:
            continue

        ids_vistos.add(video_id)

        titulo = (
            video.get("title")
            or ""
        ).strip()

        if not titulo:
            continue

        if titulo_indesejado(titulo):
            continue

        uploader = (
            video.get("uploader")
            or ""
        )

        canal = (
            video.get("channel")
            or ""
        )

        artista_video = (
            video.get("artist")
            or ""
        )

        canal_completo = (
            f"{uploader} "
            f"{canal} "
            f"{artista_video}"
        )

        corresponde, pontos_artista = (
            artista_corresponde(
                cantor,
                titulo,
                canal_completo,
                canal_completo,
            )
        )

        if not corresponde:
            continue

        nome_musica = limpar_titulo_musica(
            titulo,
            cantor,
        )

        nome_normalizado = normalizar_texto(
            nome_musica
        )

        if not nome_normalizado:
            continue

        if nome_normalizado == cantor_normalizado:
            continue

        if nome_normalizado in nomes_vistos:
            continue

        url = video.get("webpage_url")

        if not url:
            url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

        visualizacoes = (
            video.get("view_count")
            or 0
        )

        pontuacao = pontos_artista

        titulo_normalizado = normalizar_texto(
            titulo
        )

        uploader_normalizado = normalizar_texto(
            uploader
        )

        canal_normalizado = normalizar_texto(
            canal
        )

        if cantor_normalizado in titulo_normalizado:
            pontuacao += 100

        if cantor_normalizado in uploader_normalizado:
            pontuacao += 120

        if cantor_normalizado in canal_normalizado:
            pontuacao += 120

        try:

            pontuacao += min(
                float(visualizacoes) / 1_000_000,
                50,
            )

        except Exception:
            pass

        musicas.append(
            {
                "id": video_id,
                "titulo": titulo,
                "nome_musica": nome_musica,
                "url": url,
                "visualizacoes": visualizacoes,
                "thumbnail": video.get("thumbnail"),
                "uploader": uploader,
                "canal": canal,
                "pontuacao": pontuacao,
            }
        )

        nomes_vistos.add(
            nome_normalizado
        )

    musicas.sort(
        key=lambda item: item["pontuacao"],
        reverse=True,
    )

    return musicas[:10]


# ============================================================
# NOME SEGURO
# ============================================================

def nome_arquivo_seguro(nome):

    nome = str(nome or "").strip()

    nome = re.sub(
        r'[<>:"/\\|?*]',
        "",
        nome,
    )

    nome = re.sub(
        r"\s+",
        " ",
        nome,
    )

    nome = nome.strip(". ")

    if not nome:
        nome = "musica"

    return nome[:180]


# ============================================================
# DOWNLOAD
# ============================================================

def baixar_musica(
    musica,
    pasta,
    qualidade,
    numero,
    total,
    progresso,
    status,
):

    if qualidade == "128 kbps":
        bitrate = "128"

    elif qualidade == "192 kbps":
        bitrate = "192"

    elif qualidade == "256 kbps":
        bitrate = "256"

    elif qualidade == "320 kbps":
        bitrate = "320"

    else:
        bitrate = "192"

    ffmpeg_exe = obter_executavel_ffmpeg()

    if not ffmpeg_exe:

        status.error(
            "❌ FFmpeg não foi encontrado."
        )

        return None

    def hook(d):

        if d.get("status") == "downloading":

            percentual = d.get(
                "_percent_str",
                "0%",
            )

            velocidade = d.get(
                "_speed_str",
                "",
            )

            status.info(
                f"⬇️ {numero}/{total} — "
                f"{musica['nome_musica']} — "
                f"{percentual} "
                f"{velocidade}"
            )

        elif d.get("status") == "finished":

            status.info(
                f"🎧 {numero}/{total} — "
                f"Convertendo para MP3..."
            )

    os.makedirs(
        pasta,
        exist_ok=True,
    )

    titulo_seguro = nome_arquivo_seguro(
        musica["nome_musica"]
    )

    modelo_saida = os.path.join(
        pasta,
        f"{titulo_seguro}.%(ext)s",
    )

    opcoes = {
    "format": "bestaudio/best",
    "outtmpl": modelo_saida,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,

    "ffmpeg_location": ffmpeg_exe,

    "retries": 5,
    "fragment_retries": 5,
    "file_access_retries": 5,

    "continuedl": True,
    "nopart": False,

    "progress_hooks": [hook],

    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": bitrate,
        }
    ],

    "keepvideo": False,
    "restrictfilenames": False,
}

    try:

        with yt_dlp.YoutubeDL(opcoes) as ydl:

            ydl.download(
                [musica["url"]]
            )

        arquivo_mp3 = Path(
            pasta
        ) / f"{titulo_seguro}.mp3"

        if not arquivo_mp3.exists():

            arquivos = list(
                Path(pasta).glob("*.mp3")
            )

            if arquivos:

                arquivo_mp3 = max(
                    arquivos,
                    key=lambda p: p.stat().st_mtime,
                )

        if not arquivo_mp3.exists():

            status.error(
                f"❌ O MP3 de "
                f"'{musica['nome_musica']}' "
                f"não foi encontrado."
            )

            return None

        progresso.progress(
            numero / total
        )

        status.success(
            f"✅ {numero}/{total} — "
            f"{musica['nome_musica']} concluída"
        )

        return str(arquivo_mp3)

    except Exception as erro:

        status.error(
            f"❌ Erro ao baixar "
            f"'{musica['titulo']}'"
        )

        with st.expander(
            "Ver detalhes do erro"
        ):
            st.code(
                str(erro)
            )

        return None


# ============================================================
# CRIA ZIP
# ============================================================

def criar_zip(arquivos):

    memoria = io.BytesIO()

    with zipfile.ZipFile(
        memoria,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:

        for arquivo in arquivos:

            caminho = Path(arquivo)

            if caminho.exists():

                zip_file.write(
                    caminho,
                    arcname=caminho.name,
                )

    memoria.seek(0)

    return memoria.getvalue()


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    '<h1 class="main-title">🎵 Downloader de Música</h1>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="subtitle">'
    'Encontre músicas populares e salve o áudio em MP3'
    '</p>',
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Configurações")

    quantidade = st.slider(
        "Quantidade de músicas",
        min_value=1,
        max_value=10,
        value=10,
    )

    qualidade = st.selectbox(
        "Qualidade do MP3",
        [
            "128 kbps",
            "192 kbps",
            "256 kbps",
            "320 kbps",
        ],
        index=1,
    )

    st.divider()

    st.markdown(
        "### ☁️ Modo online"
    )

    st.write(
        "Os arquivos são processados "
        "temporariamente no servidor."
    )

    st.write(
        "Você escolhe onde salvar "
        "pelo navegador."
    )

    st.divider()

    ffmpeg = obter_executavel_ffmpeg()

    if ffmpeg:

        st.success(
            "✅ FFmpeg disponível"
        )

    else:

        st.error(
            "❌ FFmpeg não disponível"
        )


# ============================================================
# ARTISTA
# ============================================================

st.subheader(
    "🎤 Escolha o artista"
)

coluna_artista, coluna_pesquisar = st.columns(
    [4, 1]
)

with coluna_artista:

    cantor = st.text_input(
        "Nome do cantor",
        placeholder="Ex.: Nelson Gonçalves",
        label_visibility="collapsed",
    )

with coluna_pesquisar:

    pesquisar = st.button(
        "🔎 Pesquisar",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# PESQUISAR
# ============================================================

if pesquisar:

    if not cantor.strip():

        st.warning(
            "⚠️ Digite o nome de um cantor ou artista."
        )

    else:

        st.session_state.cantor = (
            cantor.strip()
        )

        st.session_state.musicas = []

        st.session_state.selecionadas = set()

        st.session_state.arquivos_baixados = []

        st.session_state.zip_bytes = None

        with st.spinner(
            f"🔎 Procurando músicas de "
            f"{cantor.strip()}..."
        ):

            try:

                resultados = pesquisar_musicas(
                    cantor.strip()
                )

                st.session_state.musicas = (
                    resultados
                )

                if not resultados:

                    st.warning(
                        f"⚠️ Não encontrei músicas "
                        f"relacionadas claramente a "
                        f"'{cantor.strip()}'."
                    )

            except Exception as erro:

                st.error(
                    "❌ Ocorreu um erro durante a pesquisa."
                )

                st.code(
                    str(erro)
                )


# ============================================================
# RESULTADOS
# ============================================================

musicas = st.session_state.musicas


if musicas:

    st.divider()

    st.subheader(
        "🎵 Músicas encontradas"
    )

    st.caption(
        f"Artista: {st.session_state.cantor}"
    )

    st.caption(
        "Marque somente as músicas que deseja baixar."
    )

    # --------------------------------------------------------
    # BOTÕES SELECIONAR / DESMARCAR
    # --------------------------------------------------------

    col_sel, col_des = st.columns(2)

    with col_sel:

        if st.button(
            "☑️ Selecionar todas",
            use_container_width=True,
        ):

            st.session_state.selecionadas = {
                musica["id"]
                for musica in musicas[:quantidade]
            }

            st.rerun()

    with col_des:

        if st.button(
            "☐ Desmarcar todas",
            use_container_width=True,
        ):

            st.session_state.selecionadas = set()

            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # LISTA DE MÚSICAS
    # --------------------------------------------------------

    for numero, musica in enumerate(
        musicas[:quantidade],
        1,
    ):

        musica_id = musica["id"]

        if musica_id in st.session_state.selecionadas:
            marcado = True
        else:
            marcado = False

        coluna_numero, coluna_info = st.columns(
            [0.5, 7]
        )

        with coluna_numero:

            st.markdown(
                f"### {numero:02d}"
            )

        with coluna_info:

            with st.container(border=True):

                selecionada = st.checkbox(
                    f"🎵 {musica['nome_musica']}",
                    value=marcado,
                    key=f"musica_{musica_id}",
                )

                if selecionada:

                    st.session_state.selecionadas.add(
                        musica_id
                    )

                else:

                    st.session_state.selecionadas.discard(
                        musica_id
                    )

                visualizacoes = (
                    formatar_visualizacoes(
                        musica["visualizacoes"]
                    )
                )

                st.caption(
                    f"👁️ {visualizacoes} visualizações"
                )

                st.caption(
                    f"Original: {musica['titulo']}"
                )

                if musica.get("uploader"):

                    st.caption(
                        f"📺 Canal: "
                        f"{musica['uploader']}"
                    )


    # ========================================================
    # RESUMO DA SELEÇÃO
    # ========================================================

    musicas_selecionadas = [
        musica
        for musica in musicas[:quantidade]
        if musica["id"]
        in st.session_state.selecionadas
    ]

    st.divider()

    st.info(
        f"🎵 {len(musicas_selecionadas)} "
        f"música(s) selecionada(s) "
        f"de {min(quantidade, len(musicas))}."
    )

    # ========================================================
    # DOWNLOAD
    # ========================================================

    if musicas_selecionadas:

        st.subheader(
            "⬇️ Download"
        )

        st.info(
            f"Qualidade selecionada: **{qualidade}**"
        )

        baixar = st.button(
            "⬇️ PROCESSAR MÚSICAS SELECIONADAS",
            type="primary",
            use_container_width=True,
        )

        if baixar:

            total = len(
                musicas_selecionadas
            )

            progresso = st.progress(0)

            status = st.empty()

            sucessos = []
            falhas = []

            pasta_temporaria = tempfile.mkdtemp(
                prefix="music_downloader_"
            )

            try:

                for numero, musica in enumerate(
                    musicas_selecionadas,
                    1,
                ):

                    arquivo = baixar_musica(
                        musica=musica,
                        pasta=pasta_temporaria,
                        qualidade=qualidade,
                        numero=numero,
                        total=total,
                        progresso=progresso,
                        status=status,
                    )

                    if arquivo:

                        sucessos.append(
                            arquivo
                        )

                    else:

                        falhas.append(
                            musica
                        )

                progresso.progress(1.0)

                if sucessos:

                    st.session_state.arquivos_baixados = (
                        sucessos
                    )

                    with st.spinner(
                        "📦 Preparando ZIP..."
                    ):

                        st.session_state.zip_bytes = (
                            criar_zip(sucessos)
                        )

                    st.success(
                        f"✅ {len(sucessos)} música(s) "
                        f"processada(s) com sucesso."
                    )

                if falhas:

                    st.warning(
                        f"⚠️ {len(falhas)} música(s) "
                        f"não puderam ser processadas."
                    )

            except Exception as erro:

                st.error(
                    "❌ Ocorreu um erro durante "
                    "o processamento."
                )

                st.code(
                    str(erro)
                )

    else:

        st.warning(
            "☝️ Selecione pelo menos uma música."
        )


# ============================================================
# ARQUIVOS PRONTOS
# ============================================================

arquivos_baixados = (
    st.session_state.arquivos_baixados
)


if arquivos_baixados:

    st.divider()

    st.subheader(
        "📥 Arquivos prontos"
    )

    st.success(
        f"{len(arquivos_baixados)} arquivo(s) "
        "pronto(s) para baixar."
    )

    # --------------------------------------------------------
    # ZIP
    # --------------------------------------------------------

    zip_bytes = (
        st.session_state.zip_bytes
    )

    if zip_bytes:

        nome_artista = nome_arquivo_seguro(
            st.session_state.cantor
        )

        nome_zip = (
            f"{nome_artista}_musicas.zip"
        )

        st.download_button(
            label="📦 BAIXAR TODAS AS SELECIONADAS EM ZIP",
            data=zip_bytes,
            file_name=nome_zip,
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # INDIVIDUAIS
    # --------------------------------------------------------

    st.markdown(
        "### 🎧 Baixar individualmente"
    )

    for indice, arquivo in enumerate(
        arquivos_baixados
    ):

        caminho = Path(arquivo)

        if not caminho.exists():
            continue

        try:

            dados = caminho.read_bytes()

        except Exception:

            continue

        col_nome, col_botao = st.columns(
            [5, 2]
        )

        with col_nome:

            st.write(
                f"🎵 {caminho.name}"
            )

        with col_botao:

            st.download_button(
                label="⬇️ Baixar",
                data=dados,
                file_name=caminho.name,
                mime="audio/mpeg",
                key=f"download_individual_{indice}",
                use_container_width=True,
            )

    st.info(
        "💡 O local onde o arquivo será salvo "
        "é definido pelo seu navegador."
    )


# ============================================================
# TELA INICIAL
# ============================================================

if not musicas:

    st.divider()

    st.markdown(
        "## 🎧 Escolha um artista"
    )

    st.write(
        "Digite o nome do cantor acima "
        "e clique em **Pesquisar**."
    )

    st.info(
        "💡 Exemplo: Nelson Gonçalves"
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "🎵 Music Downloader • "
    "Streamlit + yt-dlp + FFmpeg"
)