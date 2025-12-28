import os
import httpx

TELEGRAM_API = "https://api.telegram.org"

class TelegramClient:
    def __init__(self):
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]

    def send_message(self, chat_id: int, text: str) -> None:
        url = f"{TELEGRAM_API}/bot{self.token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        with httpx.Client(timeout=30) as c:
            r = c.post(url, json=payload)
            r.raise_for_status()
