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

    div[data-testid="stSelectbox"] {
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
    st.session_state.selecionadas = []

if "arquivos_baixados" not in st.session_state:
    st.session_state.arquivos_baixados = []

if "zip_bytes" not in st.session_state:
    st.session_state.zip_bytes = None


# ============================================================
# PALAVRAS / EXPRESSÕES A EVITAR
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
    "pseudo video",
    "pseudo-video",
    "pseudovideo",
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
# VERIFICA TÍTULO INDESEJADO
# ============================================================

def titulo_indesejado(titulo):
    texto = normalizar_texto(titulo)

    for palavra in PALAVRAS_EVITAR:
        palavra_normalizada = normalizar_texto(palavra)

        if palavra_normalizada and palavra_normalizada in texto:
            return True

    return False


# ============================================================
# LIMPA TÍTULO
# ============================================================

def limpar_titulo_musica(titulo, cantor):
    resultado = str(titulo or "").strip()
    artista = str(cantor or "").strip()

    # --------------------------------------------------------
    # Remove artista do início
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Informações extras
    # --------------------------------------------------------

    extras = [
        r"pseudo\s*video",
        r"pseudo\s*vídeo",
        r"pseudo-video",
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

    # --------------------------------------------------------
    # Remove parênteses e colchetes vazios
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Espaços duplicados
    # --------------------------------------------------------

    resultado = re.sub(
        r"\s+",
        " ",
        resultado,
    )

    # --------------------------------------------------------
    # Separadores sobrando
    # --------------------------------------------------------

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
    """
    Primeiro tenta o FFmpeg fornecido pelo imageio-ffmpeg.
    Depois procura no PATH do sistema.
    """

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
# VERIFICA ARTISTA
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

    # Nome completo no título
    if artista and artista in titulo_n:
        return True, 100

    # Nome completo no uploader
    if artista and artista in uploader_n:
        return True, 150

    # Nome completo no canal
    if artista and artista in canal_n:
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
# VERIFICA DISPONIBILIDADE DO VÍDEO
# ============================================================

def video_disponivel(url):
    """
    Faz uma consulta rápida para evitar colocar na lista
    vídeos claramente indisponíveis.
    """

    opcoes = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
        "extract_flat": True,
    }

    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(
                url,
                download=False,
            )

        return bool(info)

    except Exception:
        return False


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

    # --------------------------------------------------------
    # Executa pesquisas
    # --------------------------------------------------------

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

    cantor_normalizado = normalizar_texto(cantor)

    musicas = []

    ids_vistos = set()
    nomes_vistos = set()

    # --------------------------------------------------------
    # Analisa candidatos
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # Filtra versões indesejadas
        # ----------------------------------------------------

        if titulo_indesejado(titulo):
            continue

        # ----------------------------------------------------
        # Informações
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Confirma artista
        # ----------------------------------------------------

        corresponde, pontos_artista = artista_corresponde(
            cantor,
            titulo,
            canal_completo,
            canal_completo,
        )

        if not corresponde:
            continue

        # ----------------------------------------------------
        # Limpa nome
        # ----------------------------------------------------

        nome_musica = limpar_titulo_musica(
            titulo,
            cantor,
        )

        nome_normalizado = normalizar_texto(
            nome_musica
        )

        if not nome_normalizado:
            continue

        # Não aceita resultado que seja somente o artista
        if nome_normalizado == cantor_normalizado:
            continue

        # Não aceita novamente conteúdo indesejado
        if titulo_indesejado(nome_musica):
            continue

        # ----------------------------------------------------
        # Deduplicação
        # ----------------------------------------------------

        if nome_normalizado in nomes_vistos:
            continue

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        url = video.get("webpage_url")

        if not url:
            url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

        # ----------------------------------------------------
        # Visualizações
        # ----------------------------------------------------

        visualizacoes = (
            video.get("view_count")
            or 0
        )

        # ----------------------------------------------------
        # Pontuação
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Guarda resultado
        # ----------------------------------------------------

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

        # Evita lista excessivamente grande
        if len(musicas) >= 20:
            break

    # --------------------------------------------------------
    # Ordena
    # --------------------------------------------------------

    musicas.sort(
        key=lambda item: item["pontuacao"],
        reverse=True,
    )

    return musicas[:15]


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

    # --------------------------------------------------------
    # FFmpeg
    # --------------------------------------------------------

    ffmpeg_exe = obter_executavel_ffmpeg()

    if not ffmpeg_exe:
        status.error(
            "❌ FFmpeg não foi encontrado no servidor."
        )
        return None

    # --------------------------------------------------------
    # Pasta
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Hook
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Opções yt-dlp
    # --------------------------------------------------------

    opcoes = {
        "format": "bestaudio/best",

        "outtmpl": modelo_saida,

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        "ffmpeg_location": ffmpeg_exe,

        "progress_hooks": [
            hook
        ],

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }
        ],

        "keepvideo": False,

        "restrictfilenames": False,

        # Evita informações extras no nome
        "windowsfilenames": True,

        # Não tenta baixar playlist
        "noplaylist": True,
    }

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    try:

        with yt_dlp.YoutubeDL(opcoes) as ydl:

            ydl.download(
                [musica["url"]]
            )

        arquivo_mp3 = (
            Path(pasta)
            / f"{titulo_seguro}.mp3"
        )

        # ----------------------------------------------------
        # Caso o nome final seja diferente
        # ----------------------------------------------------

        if not arquivo_mp3.exists():

            arquivos = list(
                Path(pasta).glob("*.mp3")
            )

            if arquivos:

                arquivo_mp3 = max(
                    arquivos,
                    key=lambda p: p.stat().st_mtime,
                )

        # ----------------------------------------------------
        # Não encontrou MP3
        # ----------------------------------------------------

        if not arquivo_mp3.exists():

            status.warning(
                f"⚠️ {numero}/{total} — "
                f"'{musica['nome_musica']}' "
                f"não gerou um arquivo MP3."
            )

            return None

        # ----------------------------------------------------
        # Sucesso
        # ----------------------------------------------------

        progresso.progress(
            numero / total
        )

        status.success(
            f"✅ {numero}/{total} — "
            f"{musica['nome_musica']} concluída"
        )

        return str(arquivo_mp3)

    except Exception as erro:

        mensagem = str(erro)

        # Erros comuns de vídeo indisponível
        if (
            "Video unavailable" in mensagem
            or "video is not available" in mensagem.lower()
            or "This video is not available" in mensagem
            or "Private video" in mensagem
            or "has been removed" in mensagem
        ):

            status.warning(
                f"⚠️ {numero}/{total} — "
                f"'{musica['nome_musica']}' "
                f"está indisponível e foi ignorada."
            )

        else:

            status.error(
                f"❌ {numero}/{total} — "
                f"Erro ao baixar "
                f"'{musica['nome_musica']}'."
            )

            with st.expander(
                "Ver detalhes do erro"
            ):
                st.code(mensagem)

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

        nomes_usados = set()

        for arquivo in arquivos:

            caminho = Path(arquivo)

            if not caminho.exists():
                continue

            nome = caminho.name

            # Evita nomes duplicados no ZIP
            if nome in nomes_usados:

                contador = 2

                stem = caminho.stem
                extensao = caminho.suffix

                while (
                    f"{stem} ({contador}){extensao}"
                    in nomes_usados
                ):
                    contador += 1

                nome = (
                    f"{stem} ({contador}){extensao}"
                )

            nomes_usados.add(nome)

            zip_file.write(
                caminho,
                arcname=nome,
            )

    memoria.seek(0)

    return memoria.getvalue()


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    '<h1 class="main-title">'
    "🎵 Downloader de Música"
    "</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="subtitle">'
    "Encontre músicas e escolha exatamente quais deseja processar"
    "</p>",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Configurações")

    quantidade = st.slider(
        "Quantidade de resultados",
        min_value=1,
        max_value=15,
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
        "As músicas são processadas "
        "temporariamente no servidor."
    )

    st.write(
        "Depois você baixa os arquivos "
        "diretamente pelo navegador."
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
        value=st.session_state.cantor,
    )

with coluna_pesquisar:

    pesquisar = st.button(
        "🔎 Pesquisar",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# EXECUTA PESQUISA
# ============================================================

if pesquisar:

    if not cantor.strip():

        st.warning(
            "⚠️ Digite o nome de um cantor ou artista."
        )

    else:

        st.session_state.cantor = cantor.strip()

        st.session_state.musicas = []

        st.session_state.selecionadas = []

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

                st.session_state.musicas = resultados

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

                with st.expander(
                    "Ver detalhes do erro"
                ):
                    st.code(str(erro))


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
        "Selecione abaixo somente as músicas que deseja processar."
    )

    # --------------------------------------------------------
    # Quantidade exibida
    # --------------------------------------------------------

    musicas_exibidas = musicas[:quantidade]

    # --------------------------------------------------------
    # Botões selecionar todos / limpar
    # --------------------------------------------------------

    col_todos, col_nenhum = st.columns(2)

    with col_todos:

        selecionar_todos = st.button(
            "☑️ Selecionar todas",
            use_container_width=True,
        )

    with col_nenhum:

        limpar_selecao = st.button(
            "⬜ Limpar seleção",
            use_container_width=True,
        )

    if selecionar_todos:

        st.session_state.selecionadas = [
            musica["id"]
            for musica in musicas_exibidas
        ]

    if limpar_selecao:

        st.session_state.selecionadas = []

    # --------------------------------------------------------
    # Lista
    # --------------------------------------------------------

    ids_selecionados = set(
        st.session_state.selecionadas
    )

    for numero, musica in enumerate(
        musicas_exibidas,
        1,
    ):

        video_id = musica["id"]

        selecionada = video_id in ids_selecionados

        coluna_check, coluna_info = st.columns(
            [0.7, 7]
        )

        with coluna_check:

            marcada = st.checkbox(
                "",
                value=selecionada,
                key=f"selecionar_{video_id}",
                label_visibility="collapsed",
            )

        # Atualiza estado
        if marcada and video_id not in ids_selecionados:

            st.session_state.selecionadas.append(
                video_id
            )

        elif not marcada and video_id in ids_selecionados:

            st.session_state.selecionadas.remove(
                video_id
            )

        with coluna_info:

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {numero:02d} — 🎵 "
                    f"{musica['nome_musica']}"
                )

                visualizacoes = formatar_visualizacoes(
                    musica["visualizacoes"]
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

    # --------------------------------------------------------
    # Seleção final
    # --------------------------------------------------------

    ids_selecionados = set(
        st.session_state.selecionadas
    )

    musicas_selecionadas = [
        musica
        for musica in musicas_exibidas
        if musica["id"] in ids_selecionados
    ]

    st.divider()

    st.subheader(
        "⬇️ Download"
    )

    if not musicas_selecionadas:

        st.info(
            "☝️ Selecione pelo menos uma música "
            "na lista acima."
        )

    else:

        st.success(
            f"🎵 {len(musicas_selecionadas)} "
            f"música(s) selecionada(s)."
        )

        st.write(
            "Selecionadas:"
        )

        for musica in musicas_selecionadas:

            st.write(
                f"• {musica['nome_musica']}"
            )

        baixar = st.button(
            "⬇️ PROCESSAR SELECIONADAS",
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

            # ------------------------------------------------
            # Diretório temporário
            # ------------------------------------------------

            pasta_temporaria = tempfile.mkdtemp(
                prefix="music_downloader_"
            )

            try:

                # --------------------------------------------
                # Download
                # --------------------------------------------

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

                # --------------------------------------------
                # Final
                # --------------------------------------------

                progresso.progress(1.0)

                if sucessos:

                    st.success(
                        f"🎵 {len(sucessos)} música(s) "
                        "processada(s) com sucesso."
                    )

                if falhas:

                    st.warning(
                        f"⚠️ {len(falhas)} música(s) "
                        "não puderam ser processadas."
                    )

                # --------------------------------------------
                # Guarda resultados
                # --------------------------------------------

                st.session_state.arquivos_baixados = (
                    sucessos
                )

                st.session_state.zip_bytes = None

                # --------------------------------------------
                # Cria ZIP
                # --------------------------------------------

                if sucessos:

                    with st.spinner(
                        "📦 Preparando arquivo ZIP..."
                    ):

                        zip_bytes = criar_zip(
                            sucessos
                        )

                    st.session_state.zip_bytes = (
                        zip_bytes
                    )

            except Exception as erro:

                st.error(
                    "❌ Ocorreu um erro durante "
                    "o processamento."
                )

                with st.expander(
                    "Ver detalhes do erro"
                ):
                    st.code(str(erro))


# ============================================================
# ARQUIVOS PRONTOS
# ============================================================

arquivos_baixados = (
    st.session_state.arquivos_baixados
)


if arquivos_baixados:

    st.divider()

    st.subheader(
        "📥 Seus arquivos estão prontos"
    )

    st.success(
        f"{len(arquivos_baixados)} arquivo(s) "
        "disponível(is) para baixar."
    )

    # --------------------------------------------------------
    # ZIP
    # --------------------------------------------------------

    zip_bytes = st.session_state.zip_bytes

    if zip_bytes:

        nome_artista = nome_arquivo_seguro(
            st.session_state.cantor
        )

        nome_zip = (
            f"{nome_artista}_musicas.zip"
        )

        st.download_button(
            label="📦 BAIXAR TODAS EM ZIP",
            data=zip_bytes,
            file_name=nome_zip,
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Downloads individuais
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
                key=f"download_{indice}_{caminho.name}",
                use_container_width=True,
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
