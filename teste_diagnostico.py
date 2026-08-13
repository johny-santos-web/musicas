#!/usr/bin/env python3
"""
Script de diagnóstico para testar o yt-dlp e dependências localmente.
Execute com: python teste_diagnostico.py
"""

import os
import sys
import shutil
from pathlib import Path

print("=" * 60)
print("🔧 DIAGNÓSTICO DE DEPENDÊNCIAS - Music Downloader")
print("=" * 60)
print()

# ============================================================
# PYTHON
# ============================================================

print("📌 Python:")
print(f"   Versão: {sys.version}")
print(f"   Executável: {sys.executable}")
print()

# ============================================================
# FFMPEG
# ============================================================

print("📌 FFmpeg:")
ffmpeg = shutil.which("ffmpeg")
if ffmpeg:
    print(f"   ✅ Encontrado: {ffmpeg}")
else:
    print("   ❌ Não encontrado")
    print("   Instale com: choco install ffmpeg (Windows) ou brew install ffmpeg (Mac)")
print()

# ============================================================
# NODE.JS
# ============================================================

print("📌 Node.js:")
node = shutil.which("node")
if node:
    print(f"   ✅ Encontrado: {node}")
else:
    print("   ❌ Não encontrado")
    print("   Instale com: https://nodejs.org/ (recomendado)")
print()

# ============================================================
# MÓDULOS PYTHON
# ============================================================

print("📌 Módulos Python:")

modulos = ["streamlit", "yt_dlp", "imageio_ffmpeg"]
for modulo in modulos:
    try:
        __import__(modulo)
        print(f"   ✅ {modulo}")
    except ImportError:
        print(f"   ❌ {modulo} (instale com: pip install {modulo})")
print()

# ============================================================
# TESTE YT-DLP
# ============================================================

print("📌 Teste yt-dlp:")
try:
    import yt_dlp
    
    opcoes = {
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": True,
        "extract_flat": True,
        "skip_download": True,
        "socket_timeout": 30,
    }
    
    print("   Testando busca por 'Nelson Gonçalves'...")
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        resultado = ydl.extract_info("ytsearch5:Nelson Gonçalves", download=False)
        videos = resultado.get("entries", [])
        print(f"   ✅ Busca funcionando: {len(videos)} vídeos encontrados")
        
        if videos and videos[0]:
            print(f"   Exemplo: {videos[0].get('title', 'Sem título')[:60]}")
            
except Exception as e:
    print(f"   ❌ Erro na busca: {e}")

print()
print("=" * 60)
print("✅ Diagnóstico completo!")
print("=" * 60)
