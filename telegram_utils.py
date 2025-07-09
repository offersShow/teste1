import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Configurações do bot
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = 8038387449
ENDPOINT_CODIGO = 'https://127.0.0.1:5050/receber_codigo'


# Envia mensagem inicial solicitando código 2FA
def enviar_mensagem_inicio():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': USER_ID,
        'text': '🔐 Por favor, envie o código 2FA recebido no site.'
    }
    try:
        requests.post(url, json=payload)
        print("[BOT] Mensagem inicial enviada.")
    except Exception as e:
        print("[❌] Erro ao enviar mensagem inicial:", e)


# Manipulador de mensagens recebidas
async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if update.effective_user.id != USER_ID:
        await update.message.reply_text("❌ Acesso negado. Este bot só aceita mensagens do usuário autorizado.")
        return

    if texto.isdigit() and len(texto) in [4, 5, 6]:
        try:
            resp = requests.post(ENDPOINT_CODIGO, json={"codigo": texto})
            if resp.ok:
                await update.message.reply_text("✅ Código 2FA recebido com sucesso.")
                print("[BOT] Código enviado ao backend.")
            else:
                await update.message.reply_text("❌ Erro ao enviar o código para o sistema.")
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao enviar: {e}")
    else:
        await update.message.reply_text("❗ Envie apenas o código de verificação (somente números).")


# Inicia o bot e escuta mensagens
def iniciar_bot():
    enviar_mensagem_inicio()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("[BOT] Bot do Telegram rodando. Aguardando código...")
    application.run_polling()


if __name__ == "__main__":
    iniciar_bot()
