# 🎵 Music Downloader - Streamlit App

Um aplicativo Streamlit para buscar e baixar músicas em MP3 diretamente do YouTube.

## ✨ Características

- 🔎 **Busca inteligente** de artistas no YouTube
- 📥 **Download em MP3** com qualidade configurável (128-320 kbps)
- 📦 **Múltiplos formatos de saída** (ZIP ou individual)
- 🎨 **Interface moderna** com tema escuro
- 💾 **Dois modos de salvamento**:
  - Windows / Local: Salva automaticamente em `Downloads/Musicas`
  - Online / Navegador: Processa no servidor e baixa via navegador
- ⚡ **Otimizado para Streamlit Cloud** com bypass automático de bloqueios

## 📋 Requisitos

### Local (Windows/Mac/Linux)

- Python 3.8+
- FFmpeg
- Node.js (opcional, mas recomendado para melhor compatibilidade com YouTube)

### Instalação

```bash
# Clone o repositório
git clone <seu-repositório>
cd musicas-downloader

# Instale as dependências
pip install -r requirements.txt

# Para Windows/Mac com Homebrew:
# FFmpeg
choco install ffmpeg  # Windows
brew install ffmpeg   # Mac

# Node.js
choco install nodejs  # Windows
brew install node     # Mac
```

## 🚀 Como Usar

### Local

```bash
streamlit run musicas.py
```

A aplicação abrirá em `http://localhost:8501`

### Deploy no Streamlit Cloud

Veja [STREAMLIT_CLOUD_GUIDE.md](STREAMLIT_CLOUD_GUIDE.md) para instruções completas.

## 🔧 Solução de Problemas

### "Não encontrei músicas"

1. **Ativar Modo Debug** (veja seção "Debug Mode")
2. **Limpar cache** (as buscas são cacheadas por 10 minutos)
3. **Tentar outro artista** (alguns artistas têm menos vídeos)
4. **Usar proxy** (se estiver em Streamlit Cloud com IP bloqueado)

### "FFmpeg não disponível"

Execute o script de diagnóstico:

```bash
python teste_diagnostico.py
```

### Problemas no Streamlit Cloud

Consulte o guia completo: [STREAMLIT_CLOUD_GUIDE.md](STREAMLIT_CLOUD_GUIDE.md)

## 🔍 Debug Mode

Para ativar logs detalhados:

**Localmente:**
```bash
DEBUG_MODE=true streamlit run musicas.py
```

**Streamlit Cloud:**
- Vá em ⚙️ Configurações → Secrets
- Adicione: `DEBUG_MODE = "true"`
- Redeploy

## 📂 Estrutura do Projeto

```
musicas-downloader/
├── musicas.py                    # App principal
├── requirements.txt              # Dependências Python
├── packages.txt                  # Dependências do sistema
├── .streamlit/
│   └── config.toml              # Configuração do Streamlit
├── STREAMLIT_CLOUD_GUIDE.md     # Guia de deploy
├── .env.example                 # Exemplo de variáveis de ambiente
├── teste_diagnostico.py         # Script de diagnóstico
└── README.md                    # Este arquivo
```

## 🎯 Funcionalidades em Detalhes

### Filtros Inteligentes

- Remove covers, karaokês, remixes, remasterizações
- Valida se o vídeo é do artista correto
- Classifica por relevância (visualizações, canal oficial, etc)

### Qualidade de Áudio

Escolha entre:
- 128 kbps (leve, <5MB por música)
- 192 kbps (bom equilíbrio)
- 256 kbps (boa qualidade)
- 320 kbps (máxima qualidade)

### Modos de Salvamento

**Windows / Local:**
- Salva automaticamente em `C:\Users\SEU_USUARIO\Downloads\Musicas`
- Útil para uso pessoal

**Online / Navegador:**
- Processa no servidor Streamlit Cloud
- Baixa via browser (define onde salvar)
- Funciona em qualquer dispositivo

## 🛠️ Tecnologias

- **Streamlit** - Framework para interface web
- **yt-dlp** - Download de vídeos do YouTube
- **FFmpeg** - Conversão de áudio para MP3
- **Node.js/Deno** - Runtime JavaScript para bypass de proteções

## 📝 Notas

- O cache de buscas é de 10 minutos (economiza requisições)
- Arquivos são processados em pasta temporária
- No modo local, arquivos são salvos permanentemente
- No modo online, use o botão de download do navegador

## ⚠️ Aviso Legal

Este aplicativo é apenas para fins educacionais e pessoais. Respeite os direitos autorais e os termos de serviço do YouTube.

## 📧 Suporte

Se encontrar problemas:

1. Verifique o [guia de Streamlit Cloud](STREAMLIT_CLOUD_GUIDE.md)
2. Execute `python teste_diagnostico.py`
3. Ative Debug Mode para ver logs detalhados
4. Abra uma issue no GitHub com os logs

## 📄 Licença

MIT - Use livremente!

---

**Desenvolvido com ❤️ usando Streamlit**
