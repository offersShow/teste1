from flask import Flask, render_template, request, jsonify, session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import requests
import subprocess
import pandas as pd
import os
import re
import difflib
from security_config import configurar_talisman, configurar_limiter, verificar_token, sanitizar
from flask_cors import CORS

front = Flask("front", template_folder=".")
front.secret_key = os.environ.get("SECRET_KEY", "chave-secreta-segura")
ARQUIVO_CACHE = "cache_buscas.xlsx"

def limpar_nome_sheet(nome):
    nome = nome.lower().strip()
    nome = re.sub(r'-+', '-', nome)         # Remove hífens duplicados
    return nome[:31]  # Excel limita nomes de abas a 31 caracteres

def buscar_em_cache(termo):
    if not os.path.exists(ARQUIVO_CACHE):
        return None

    termo = termo.lower()
    df_dict = pd.read_excel(ARQUIVO_CACHE, sheet_name=None)
    abas = list(df_dict.keys())

    # 1. Normaliza os nomes para comparar
    def normalizar(s):
        return s.lower().strip().replace("-", " ").replace("_", " ")

    termo_normalizado = normalizar(termo)

    # 2. Verifica exato
    if termo in df_dict:
        print(f"[📁] Cache exato encontrado para: {termo}")
        df_validos = df_dict[termo].dropna(subset=["nome", "preco", "link"])
        return df_validos.to_dict(orient="records")

    # 3. Verifica por substring
    for aba in abas:
        if termo_normalizado in normalizar(aba) or normalizar(aba) in termo_normalizado:
            print(f"[🔁] Cache semelhante (substring) encontrado para: {aba}")
            return df_dict[aba].to_dict(orient="records")

    # 4. Verifica por similaridade leve
    match = difflib.get_close_matches(termo_normalizado, [normalizar(a) for a in abas], n=1, cutoff=0.6)
    if match:
        idx = [normalizar(a) for a in abas].index(match[0])
        aba = abas[idx]
        print(f"[🤏] Cache similar encontrado para: {aba}")
        return df_dict[aba].to_dict(orient="records")

    print(f"[❌] Nenhum cache encontrado para: {termo}")
    return None

def salvar_no_cache(termo, resultados):
    if not resultados:
        return

    # Filtra itens válidos: que têm nome, preço e link
    resultados_filtrados = [
        r for r in resultados
        if r.get("nome") and r.get("preco") and r.get("link")
    ]

    if not resultados_filtrados:
        print(f"[⚠️] Nenhum resultado válido para '{termo}'")
        return

    df_novo = pd.DataFrame(resultados_filtrados)

    if os.path.exists(ARQUIVO_CACHE):
        with pd.ExcelWriter(ARQUIVO_CACHE, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
            df_novo.to_excel(writer, sheet_name=termo, index=False)
    else:
        with pd.ExcelWriter(ARQUIVO_CACHE, engine="openpyxl") as writer:
            df_novo.to_excel(writer, sheet_name=termo, index=False)

CORS(front)
# Aplica headers de segurança e limitador
configurar_talisman(front)
limiter = configurar_limiter(front)

# ─── Configurações do ChromeDriver ────────────────────────────────────────
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--log-level=3')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.add_argument(
    'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    ' AppleWebKit/537.36 (KHTML, like Gecko)'
    ' Chrome/114.0.0.0 Safari/537.36'
)

driver = webdriver.Chrome(options=chrome_options)

##driver_lock = threading.Lock()
cache_ready_event = threading.Event()
# ─── Termos promocionais e cache ──────────────────────────────────────────
PROMO_TERMS = ['Celulares', 'Tablets',  'Notebooks', 'Eletrônicos', 'Fones de ouvido']
promo_cache = {}
cache_lock = threading.Lock()

def buscar_amazon_autenticado(termo):
    try:
        resp = requests.post(
            "https://0.0.0.0:5001/buscar_autenticado",
            json={"termo": termo},
            ##headers={"Authorization": "Bearer meu-token-secreto-123"}
        )
        if resp.status_code == 200:
            if not cache_ready_event.is_set():
                print("[⚙️] Primeira resposta bem-sucedida, liberando cache thread.")
                cache_ready_event.set()  # libera a thread do cache
            return resp.json()
    except Exception as e:
        print("Erro ao buscar da instância logada:", e)
    return []

# ─── Thread para atualizar promo_cache ───────────────────────────────────
def atualizar_promo_cache():
    global promo_cache
    novos = {}

    for term in PROMO_TERMS:
        print(f"[🔎] Verificando cache para: {term}")
        cache = buscar_em_cache(term)
        if cache:
            print(f"[📁] Cache encontrado para: {term}")
            novos[term] = cache
        else:
            print(f"[🌐] Buscando online: {term}")
            resultado = buscar_amazon_autenticado(term)
            print(f"[💾] Salvando {len(resultado)} itens no cache de: {term}")
            novos[term] = resultado
            salvar_no_cache(term, resultado)

    with cache_lock:
        promo_cache = novos

    while True:
        time.sleep(60 * 60)  # Atualiza a cada 1 hora
        novos = {}
        for term in PROMO_TERMS:
            resultado = buscar_amazon_autenticado(term)
            resultado_filtrado = [
                r for r in resultado
                if r.get("nome") and r.get("preco") and r.get("link") and r.get("imagem")
            ]

            if resultado_filtrado:
                print(f"[✅] {term} → {len(resultado_filtrado)} produtos válidos.")
                novos[term] = resultado_filtrado  # pega até 6
                salvar_no_cache(term, resultado_filtrado)
            else:
                print(f"[⛔️] {term} → Nenhum produto válido encontrado. Ignorando cache.")

        with cache_lock:
            promo_cache = novos

# Inicia thread de atualização como daemon (não bloqueia shutdown)
threading.Thread(target=atualizar_promo_cache, daemon=True).start()

# ─── Rotas Flask ──────────────────────────────────────────────────────────
@front.route('/')
def index():
    with cache_lock:
        data = promo_cache.copy()
    return render_template('index.html', default_results=data)

@front.route('/buscar', methods=['POST'])
def rota_buscar():
    termo = request.json.get('termo', '').strip()

    if termo:
        session['ultimo_termo'] = termo  # ✅ Salva o termo na sessão

    # 1. Verifica se já tem no cache
    cache = buscar_em_cache(termo)
    if cache:
        return jsonify(cache)
    
    # 2. Se não tiver, busca na Amazon
    resultados = buscar_amazon_autenticado(termo)

    # 3. Salva no cache
    salvar_no_cache(termo, resultados)

    return jsonify(resultados)

@front.route("/promocoes")
def promocoes():
    with cache_lock:
        return jsonify(promo_cache)

@front.route('/ultima_busca')
def ultima_busca():
    termo = session.get('ultimo_termo', {})
    if not termo:
        return jsonify({"termo": "", "dados": []})
    
    cache = buscar_em_cache(termo)
    return jsonify({"termo": termo, "dados": cache or []})
