from utils.db import TOKEN
from routes.web_panel import app
from telegram.request import HTTPXRequest


tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)


#function for webhook
Application = None
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    if Application is not None:
        return Application.update_webhook(tg_request)
    return "Bot is not ready", 503
