from flask import Flask, request

app = Flask(__name__)

codigo_2fa = None

@app.route('/receber_codigo', methods=['POST'])
def receber_codigo():
    global codigo_2fa
    data = request.get_json()
    if not data or 'codigo' not in data:
        return {'status': 'erro', 'mensagem': 'Código não fornecido'}, 400

    codigo_2fa = data['codigo']
    print(f"[✅] Código 2FA recebido: {codigo_2fa}")
    return {'status': 'ok'}

@app.route('/obter_codigo', methods=['GET'])
def obter_codigo():
    if codigo_2fa:
        return {'codigo': codigo_2fa}
    else:
        return {'codigo': None}, 204

if __name__ == '__main__':
    @app.route('/ping')
    def ping():
        return "pong", 200
    port = int(os.environ.get("PORT", 5050))
    app.run(host='0.0.0.0', port=port)

