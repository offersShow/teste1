from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
import html
import re
from redis import Redis

# === 🔐 Configurações globais ===
SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-segura")
TOKEN_TTL_SECONDS = 3600  # 1 hora

SELF = [
    "'self'",
    "https://offersshow.github.io/teste1/",
]
csp = {
    "default-src": SELF,
    "connect-src": SELF + [
        "https://meu-backend-flask-posa.onrender.com"
    ],
    "style-src": SELF,
    "style-src-elem": SELF,
    "font-src": SELF,
    "img-src": SELF + [
        "data:",  # para favicons ou imagens base64
        # Adicione aqui os domínios de imagem que você usa
        "https://images-na.ssl-images-amazon.com",
        "https://m.media-amazon.com"
    ],
    "script-src": SELF
}

# === 🛡️ Talisman: headers de segurança HTTP ===
def configurar_talisman(app):
    Talisman(app, content_security_policy=csp)

# Conexão com Redis
redis_connection = Redis(host="localhost", port=6379)

# === 🚦 Rate limiting ===
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

def configurar_limiter(app):
    limiter.init_app(app)

# === ✅ Geração e verificação de tokens (exemplo com itsdangerous) ===
serializer = URLSafeTimedSerializer(SECRET_KEY)

def gerar_token(usuario_id):
    return serializer.dumps({"usuario_id": usuario_id})

def verificar_token(token):
    try:
        dados = serializer.loads(token, max_age=TOKEN_TTL_SECONDS)
        return dados.get("usuario_id")
    except SignatureExpired:
        print("[⚠️] Token expirado")
        return None
    except BadSignature:
        print("[❌] Token inválido")
        return None

# === 🧼 Sanitização simples de entradas ===
def sanitizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = html.escape(texto)
    texto = re.sub(r"[<>\"'%;(){}]", "", texto)
    return texto.strip()

# Exporta os símbolos
__all__ = [
    "configurar_talisman",
    "configurar_limiter",
    "verificar_token",
    "gerar_token",
    "sanitizar",
    "limiter"
]
