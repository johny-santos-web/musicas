# 🚀 Guia de Deploy no Streamlit Cloud

## ✅ Pré-requisitos

1. **Repositório no GitHub** com os seguintes arquivos:
   - `musicas.py`
   - `requirements.txt`
   - `packages.txt`
   - `.streamlit/config.toml` (novo)

2. **Conta no Streamlit Cloud** (https://streamlit.io/cloud)

## 📋 Checklist de Deploy

### 1. Prepare o Repositório
```bash
# Certifique-se de que você tem:
- requirements.txt (com yt-dlp[default], streamlit, imageio-ffmpeg)
- packages.txt (com ffmpeg e nodejs)
- .streamlit/config.toml (arquivo de configuração otimizado)
```

### 2. Variáveis de Ambiente no Streamlit Cloud

Se tiver problemas com buscas, ative as seguintes variáveis no painel do Streamlit Cloud:

**Secrets** (⚙️ Configurações → Secrets):
```toml
# Para modo debug (ver logs detalhados)
DEBUG_MODE = "true"

# Se precisar usar proxy (substitua pela URL do proxy)
YT_DLP_PROXY = "http://seu-proxy:porta"
```

### 3. Configuração do Deploy

1. Acesse [https://share.streamlit.io](https://share.streamlit.io)
2. Clique em "New app"
3. Selecione seu repositório GitHub
4. Escolha a branch `main`
5. Define o arquivo principal: `musicas.py`
6. Clique em "Deploy"

## 🔧 Solução de Problemas

### Problema: "Não encontrei músicas"

**Solução 1: Ativar Debug Mode**
- Vá em ⚙️ Configurações → Secrets
- Adicione: `DEBUG_MODE = "true"`
- Redeploy a aplicação
- Faça uma busca e veja os logs detalhados

**Solução 2: Aguarde o build completo**
- O Streamlit Cloud pode levar 5-10 minutos para instalar ffmpeg e nodejs
- Tente de novo após 15 minutos

**Solução 3: Use um Proxy**
- Alguns datacenters do Streamlit Cloud são bloqueados pelo YouTube
- Configure um proxy em Secrets:
  ```toml
  YT_DLP_PROXY = "http://proxy.exemplo.com:8080"
  ```

**Solução 4: Limpe o Cache**
- As buscas são cacheadas por 10 minutos
- Tente buscar um artista diferente
- Ou aguarde 10 minutos e tente o mesmo artista novamente

## 📊 Monitorar o Deploy

1. Vá em ⚙️ Configurações
2. Clique em "Manage app"
3. Veja os logs em tempo real
4. Procure por erros relacionados ao YouTube

## 📝 Detalhes das Melhorias

### O que foi otimizado:

✅ **Múltiplas estratégias de bypass do YouTube**
- Diferentes client players (android, ios, mweb, web, tv_embedded)
- User-Agent realista e headers melhorados

✅ **Melhor tratamento de erros**
- Log detalhado de cada tentativa de busca
- Diagnóstico no painel lateral
- Sugestões quando nenhuma música é encontrada

✅ **Configuração otimizada do Streamlit Cloud**
- Timeouts aumentados (45 segundos)
- Retries agressivos (15 tentativas)
- Debug mode opcional

✅ **Múltiplas estrat\u00e9gias de busca**
- Pesquisa por: nome, "official", "música", "melhores", "sucessos", aspas, "lyric", "video"

## 🆘 Ainda não funciona?

1. Abra uma issue no GitHub
2. Rode localmente para confirmar que funciona
3. Copie os logs do debug mode
4. Descreva qual artista você está tentando buscar
