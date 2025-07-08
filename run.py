# run.py
import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Aqui você importa os Flask‑apps **sem** o “.py” no nome:
from app import front as front_app
from app_login_backend import backend as backend_app

# Monta o back_app sob o prefixo /api, mantendo o front_app na raiz
application = DispatcherMiddleware(front_app, {
    '/api': backend_app
})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # 'application' é o WSGI que engloba os dois apps
    run_simple('0.0.0.0', port, application, use_reloader=True)
