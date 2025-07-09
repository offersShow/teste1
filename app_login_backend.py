from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, pickle, subprocess, requests
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from dotenv import load_dotenv
import sys
import io
import psutil
import unicodedata
import re
from flask_cors import CORS
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.action_chains import ActionChains
from security_config import (configurar_talisman, configurar_limiter, verificar_token, gerar_token, sanitizar, limiter)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# ───────────── CONFIGURAÇÃO INICIAL ─────────────
backend = Flask(__name__)
CORS(backend)
load_dotenv()
EMAIL = os.getenv("EMAIL")
SENHA = os.getenv("SENHA")

##TOKEN = "meu-token-secreto-123"
autenticado = False  # Só vira True quando login for válido

configurar_talisman(backend)
configurar_limiter(backend)

driver = None

def iniciar_chrome():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--headless")  # descomente se quiser headless
    return webdriver.Chrome(options=chrome_options)

def esperar_codigo_2fa(timeout=180):
    print("[🔐] Aguardando código 2FA via Telegram...")
    for _ in range(timeout):
        try:
            r = requests.get("http://127.0.0.1:5050/obter_codigo")
            if r.ok:
                codigo = r.json().get("codigo")
                if codigo:
                    print(f"[✅] Código recebido: {codigo}")
                    return codigo
        except Exception as e:
            print("[!] Erro ao buscar código:", e)
        time.sleep(5)
    raise TimeoutError("⏰ Tempo esgotado para o código 2FA.")

def is_telegram_running():
    for proc in psutil.process_iter(['cmdline']):
        try:
            if proc.info['cmdline'] and 'telegram_utils.py' in proc.info['cmdline']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def iniciar_servicos_auxiliares():
    print("[⚙️] Iniciando serviços auxiliares...")

    # Evita conflito com múltiplas instâncias do bot
    if not is_telegram_running():
        telegram = subprocess.Popen(["python", "telegram_utils.py"])
        print("[✅] Bot Telegram iniciado.")
    else:
        telegram = None
        print("[ℹ️] Bot Telegram já estava rodando.")

    servidor = subprocess.Popen(["python", "servidor_codigo.py"])

    for _ in range(20):
        try:
            if requests.get("http://127.0.0.1:5050/ping").status_code == 200:
                print("[✅] Servidor 2FA pronto.")
                return telegram, servidor
        except:
            time.sleep(1)

    raise RuntimeError("[❌] Servidor de código 2FA não iniciou a tempo.")
    

def login():
    global driver, autenticado
    driver = iniciar_chrome()

    # Primeira visita para setar domínio
    driver.get("https://associados.amazon.com.br/")

    # Tenta restaurar cookies
    if os.path.exists("cookies.pkl"):
        with open("cookies.pkl", "rb") as f:
            for cookie in pickle.load(f):
                if "sameSite" in cookie and cookie["sameSite"] == "None":
                    cookie["sameSite"] = "Strict"
                driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(0.2)
        
        try:
            # tenta localizar o botão de login (mesmo oculto)
            el = driver.find_element(By.XPATH, '//*[@id="nav-flyout-ya-signin"]/a/span')
            html = el.get_attribute("outerHTML")

            if "faça seu login" in html.lower():
                print("[⚠️] Ainda na tela de login. Reexecutando login().")
                sys.exit(0)  # ou return para fora e o loop externo chama login() de novo
            else:
                print("[✅] Login aparentemente bem-sucedido.")
                autenticado = True
                return
        except NoSuchElementException:
            # se não achou nem o elemento, é porque provavelmente está logado
            print("[✅] Elemento ausente — login concluído.")
            autenticado = True
            return
          
            
        
            
        



    telegram_proc, servidor_proc = iniciar_servicos_auxiliares()

    try:
        # Página de login
        driver.get("https://www.amazon.com.br/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fassociados.amazon.com.br%2F&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=amzn_associates_br&openid.mode=checkid_setup&marketPlaceId=A2Q3Y263D00KWC&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ap_email"))).send_keys(EMAIL)
        driver.find_element(By.ID, "continue").click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ap_password"))).send_keys(SENHA)
        driver.find_element(By.ID, "signInSubmit").click()

        print("[🔐] Login enviado, verificando 2FA...")

        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "auth-mfa-otpcode")))
            codigo = esperar_codigo_2fa()
            driver.find_element(By.ID, "auth-mfa-otpcode").send_keys(codigo)
            driver.find_element(By.ID, "auth-signin-button").click()
            print("[✅] Código 2FA enviado.")
        except:
            print("[✔️] 2FA não solicitado.")
            sys.exit(0)

        time.sleep(2)
        with open("cookies.pkl", "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        
        try:
            # tenta localizar o botão de login (mesmo oculto)
            el = driver.find_element(By.XPATH, '//*[@id="nav-flyout-ya-signin"]/a/span')
            html = el.get_attribute("outerHTML")

            if "faça seu login" in html.lower():
                print("[⚠️] Ainda na tela de login. Reexecutando login().")
                return login()  # ou return para fora e o loop externo chama login() de novo
            else:
                print("[✅] Login aparentemente bem-sucedido.")
                autenticado = True
                pass
        except NoSuchElementException:
            # se não achou nem o elemento, é porque provavelmente está logado
            print("[✅] Elemento ausente — login concluído.")
            autenticado = True
            pass
        
    finally:
        print("[🧼] Encerrando serviços auxiliares.")
        if telegram_proc and telegram_proc.poll() is None:
            telegram_proc.terminate()
        if servidor_proc and servidor_proc.poll() is None:
            servidor_proc.terminate()

# Dicionário de expansão semântica
EXPANSOES = {
    "notebook": ["notebook", "laptop", "computador portátil", "macbook"],
    "celular": ["celular", "smartphone", "telefone"],
    "ssd": ["ssd", "disco solido", "armazenamento ssd"],
    "monitor": ["monitor", "tela", "display"],
    "tablet": ["tablet", "ipad", "galaxy tab"],
    "roteador": ["roteador", "wifi", "modem"],
    # ✅ Adicionados:
    "eletronico": ["eletronico", "eletronicos", "produto eletrônico", "acessório tech"],
    "eletrodomestico": ["eletrodomestico", "eletrodomesticos", "geladeira", "microondas", "fogão", "liquidificador"]
}

def normalizar_termo(termo):
    termo = termo.lower().strip()
    termo = unicodedata.normalize("NFKD", termo)
    termo = "".join([c for c in termo if not unicodedata.combining(c)])  # remove acentos
    termo = re.sub(r"[^a-z\s\-]", "", termo)
    return termo

def expandir_termo(termo_normalizado):
    palavras = termo_normalizado.split()
    expandidos = set()
    for palavra in palavras:
        if palavra in EXPANSOES:
            expandidos.update(EXPANSOES[palavra])
        else:
            expandidos.add(palavra)
    return list(expandidos)

@backend.route("/buscar_autenticado", methods=["POST"])
@limiter.limit("40 per minute")  # limite de 5 chamadas/minuto por IP
def buscar_autenticado():
    global driver, autenticado

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    usuario_id = verificar_token(token)
    if not usuario_id:
        return jsonify({"erro": "Token inválido ou expirado"}), 403

    termo_original = sanitizar(request.json.get("termo", ""))

    if driver is None:
        try:
            login()
        except Exception as e:
            return jsonify({"erro": f"Erro ao logar: {e}"}), 500
    if not autenticado:
        return jsonify({"erro": "Não autenticado"}), 401  # ou 403
    
    termo_normalizado = normalizar_termo(termo_original)
    termos_expandidos = expandir_termo(termo_normalizado)
    for termo in termos_expandidos:
        try:
            termo = quote_plus(termo)
            driver.get(f"https://www.amazon.com.br/s?k={termo}")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-component-type='s-search-result']"))
            )
            itens = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")

            resultados = []

            for item in itens:
                try:
                    if 'AdHolder' in item.get_attribute('class'):
                        continue
                    
                    try:
                        nome = item.find_element(By.XPATH, ".//h2").text
                        preco1 = WebDriverWait(item, 2).until(EC.presence_of_element_located((By.XPATH, ".//span[@class='a-price-whole']"))).text
                        preco2 = item.find_element(By.XPATH, ".//span[@class='a-price-fraction']").text
                        preco = f"{preco1},{preco2}".strip()
                    except (NoSuchElementException, TimeoutException):
                        continue
                    # Validação do preço
                    try:
                        int(preco1.replace(".", "").strip())
                        int(preco2.strip())
                    except ValueError:
                        continue
                    
                    # Skip se o preço estiver vazio ou for inválido
                    ##if not preco1.isdigit() or not preco2.isdigit():
                        ##continue

                    link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                    imagem = item.find_element(By.TAG_NAME, "img").get_attribute("src")

                    # === ✅ Adiciona aos resultados ===
                    resultados.append({
                        "nome": nome,
                        "preco": preco,
                        "link": link,
                        "imagem": imagem
                    })
                except (StaleElementReferenceException, NoSuchElementException, Exception) as e:
                    print(f"[⚠️] Item falhou: {e}")
                    print(f"[🧪] HTML item: {item.get_attribute('outerHTML')[:500]}...")  # imprime um trecho do HTML do item
                    continue  # Ignora itens incompletos
            
            if resultados:
                resultados = atualizar_links_produtos(resultados)
                # Converte o preço para número e ordena do menor para o maior
                def extrair_preco(item):
                    try:
                        return float(item["preco"].replace(".", "").replace(",", "."))
                    except:
                        return float('inf')  # Preços inválidos vão para o final

                resultados.sort(key=extrair_preco)

                print(f"[✅] Retornando {len(resultados)} itens ordenados por preço para termo: {termo}")

                return jsonify(resultados)
            
        except Exception as e:
            print(f"[🔥] Falha ao buscar por {termo}: {e}")
            continue

    return jsonify([])  # Nenhum termo retornou resultados

def carregar_cookies(driver):
    driver.get("https://associados.amazon.com.br/")  # Precisa visitar antes de adicionar cookies
    with open("cookies.pkl", "rb") as f:
        cookies = pickle.load(f)
        for cookie in cookies:
            if "sameSite" in cookie and cookie["sameSite"] == "None":
                cookie["sameSite"] = "Strict"
            try:
                driver.add_cookie(cookie)
            except:
                continue
    driver.refresh()

def obter_link_curto(link_original):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--log-level=3")  # Apenas erros graves

    driver = webdriver.Chrome(options=options)

    try:
        carregar_cookies(driver)
        driver.get(link_original)

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Força scroll e interação
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1.5)

        # Simula movimento do mouse
        ActionChains(driver).move_by_offset(300, 300).perform()
        time.sleep(1)

        # Espera até o botão estar clicável
        botao = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="amzn-ss-get-link-button"]'))
        )
        botao.click()

        # Espera pelo campo do shortlink
        campo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'amzn-ss-text-shortlink-textarea'))
        )
        # Espera até o conteúdo dele ser não vazio
        WebDriverWait(driver, 5).until(lambda d: campo.get_attribute("value").strip() != "")
        shortlink = campo.get_attribute("value").strip()

        if not shortlink or not shortlink.startswith("https://amzn.to"):
            raise RuntimeError(f"Shortlink inválido ou vazio: {shortlink}")

        return shortlink

    except Exception as e:
        print(f"[ERRO] {link_original} → {e}")
        return e

    finally:
        driver.quit()

def atualizar_links_produtos(resultados):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(obter_link_curto, produto["link"]): i
            for i, produto in enumerate(resultados)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                novo_link = future.result()
                resultados[idx]["link"] = novo_link
            except Exception as e:
                print(f"[ERRO THREAD] Produto {idx}: {e}")

    return resultados

@backend.route('/ping')
def ping():
    return "pong", 200
    
