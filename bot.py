"""Bot Telegram autonome. Démarrage Railway : python bot.py

Variables requises : BOT_TOKEN et une URL publique HTTPS dans MINI_APP_URL
ou RAILWAY_PUBLIC_DOMAIN. SNAPCHAT_URL est facultative.
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MINI_APP_HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mini-app</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body {
      display: grid;
      min-height: 100vh;
      margin: 0;
      padding: 24px;
      box-sizing: border-box;
      place-items: center;
      text-align: center;
      font: 16px system-ui, sans-serif;
      color: var(--tg-theme-text-color, #17202a);
      background: var(--tg-theme-bg-color, #fff);
    }
    p { color: var(--tg-theme-hint-color, #687786); }
  </style>
</head>
<body>
  <main>
    <h1>Bienvenue dans la mini-app</h1>
    <p>Personnalise cette page pour ton service.</p>
  </main>
  <script>
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  </script>
</body>
</html>
"""


def https_url(name, value):
    if not value:
        raise ValueError(f"La variable {name} est obligatoire.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{name} doit être une URL publique en HTTPS.")
    return value


def get_mini_app_url():
    url = os.environ.get("MINI_APP_URL")
    if not url:
        domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if domain:
            url = domain if domain.startswith("https://") else f"https://{domain}"
    return https_url("MINI_APP_URL ou RAILWAY_PUBLIC_DOMAIN", url)


class MiniAppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b"ok"
            content_type = "text/plain; charset=utf-8"
        elif self.path == "/" or self.path.startswith("/?"):
            body = MINI_APP_HTML.encode("utf-8")
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        pass


class TelegramBot:
    def __init__(self, token, mini_app_url, snapchat_url):
        self.api_url = f"https://api.telegram.org/bot{token}/"
        self.keyboard = {
            "inline_keyboard": [
                [{"text": "👻 Snapchat", "url": snapchat_url}],
                [
                    {
                        "text": "✈️ Telegram",
                        "url": "https://t.me/+d2YlPdxm-SQyNTBk",
                    }
                ],
                [{"text": "🛒 Boutique", "web_app": {"url": mini_app_url}}],
            ]
        }

    def call_api(self, method, payload):
        request = Request(
            self.api_url + method,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=65) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get(
                    "description", f"HTTP {error.code}"
                )
            except (ValueError, AttributeError):
                detail = f"HTTP {error.code}"
            raise RuntimeError(f"Erreur de l'API Telegram : {detail}") from None
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(
                f"Connexion à Telegram impossible ({type(error).__name__})."
            ) from None

        if not result.get("ok"):
            raise RuntimeError(
                f"Erreur de l'API Telegram : {result.get('description', 'réponse invalide')}."
            )
        return result["result"]

    def run(self):
        offset = None
        while True:
            try:
                payload = {"timeout": 50, "allowed_updates": ["message"]}
                if offset is not None:
                    payload["offset"] = offset
                updates = self.call_api(
                    "getUpdates", payload
                )
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    if message.get("text", "").split(maxsplit=1)[0:1] == ["/start"]:
                        self.call_api(
                            "sendMessage",
                            {
                                "chat_id": message["chat"]["id"],
                                "text": (
                                    "Bienvenue sur la boutique de danslazone591 !\n"
                                    "🥳\n\n"
                                    "Accédez à notre shop,\n"
                                    "Rejoignez notre canal Telegram ou notre "
                                    "Snapchat 📲\n\n"
                                    "Nous vous proposons un large choix de "
                                    "produits afin de vous satisfaire.\n"
                                    "En cas de problème, n'oubliez pas de "
                                    "rejoindre tous nos réseaux pour toujours "
                                    "nous retrouver !"
                                ),
                                "reply_markup": self.keyboard,
                            },
                        )
            except (RuntimeError, KeyError, TypeError, ValueError) as error:
                print(f"Erreur du bot : {error}", file=sys.stderr, flush=True)
                time.sleep(5)


def main():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("La variable BOT_TOKEN est obligatoire.")

    mini_app_url = get_mini_app_url()
    snapchat_url = https_url(
        "SNAPCHAT_URL",
        os.environ.get(
            "SNAPCHAT_URL", "https://www.snapchat.com/add/danslazone.591"
        ).strip(),
    )
    port = int(os.environ.get("PORT", "3000"))

    server = ThreadingHTTPServer(("0.0.0.0", port), MiniAppHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Mini-app et endpoint de santé démarrés sur le port {port}.", flush=True)

    bot = TelegramBot(token, mini_app_url, snapchat_url)
    print("Bot Telegram démarré en long polling.", flush=True)
    try:
        bot.run()
    except KeyboardInterrupt:
        print("Arrêt demandé.", flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Impossible de démarrer : {error}", file=sys.stderr, flush=True)
        sys.exit(1)
