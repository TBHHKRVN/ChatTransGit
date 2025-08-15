import os
import threading
import time
import requests
from flask import Flask, request, Response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from openai import OpenAI

# ========= Cấu hình OpenAI =========
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Lưu ngôn ngữ của từng user (tạm trong RAM)
user_lang = {}

# Danh sách mã ngôn ngữ hợp lệ
LANG_CODES = {
    "en": "English",
    "vi": "Vietnamese",
    "kr": "Korean",
    "br": "Brazilian Portuguese",
    "jp": "Japanese"
}

# ========= Slack Bolt App =========
app_slack = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# ===== Hàm dịch =====
def translate_text(text, target_lang_code):
    target_lang_name = LANG_CODES.get(target_lang_code, "English")
    prompt = f"Translate the following text into {target_lang_name}:\n\n{text}"
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[Lỗi dịch: {e}]"

# Trả lời khi được mention trong kênh
@app_slack.event("app_mention")
def handle_app_mention(event, say):
    user = event.get("user")
    if user not in user_lang:
        user_lang[user] = "en"
    say(f"Xin chào <@{user}>! 🚀 Ngôn ngữ hiện tại của bạn: {LANG_CODES[user_lang[user]]}")

# Trả lời tin nhắn trực tiếp (DM) gửi cho bot
@app_slack.event("message")
def handle_dm_events(event, say, logger):
    if event.get("channel_type") != "im":
        return
    if event.get("subtype") == "bot_message":
        return

    user = event.get("user")
    text = event.get("text", "").strip()
    if not text:
        return

    # Nếu user chưa có lang thì mặc định EN
    if user not in user_lang:
        user_lang[user] = "en"

    # Xử lý lệnh setlang
    if text.lower().startswith("setlang"):
        parts = text.split()
        if len(parts) == 2 and parts[1].lower() in LANG_CODES:
            user_lang[user] = parts[1].lower()
            say(f"✅ Ngôn ngữ của bạn đã được đặt thành: {LANG_CODES[user_lang[user]]}")
        else:
            say(f"⚠️ Cú pháp: setlang <{'/'.join(LANG_CODES.keys())}>")
        return

    # Dịch tin nhắn sang ngôn ngữ đã chọn
    translated = translate_text(text, user_lang[user])
    say(f"💬 ({LANG_CODES[user_lang[user]]}): {translated}")

# ========= Flask App (HTTP) =========
flask_app = Flask(__name__)
handler = SlackRequestHandler(app_slack)

@flask_app.route("/slack/events", methods=["POST", "GET"])
def slack_events():
    if request.headers.get("X-Slack-Retry-Num"):
        pass

    if request.method == "POST":
        data = request.get_json(silent=True, force=True) or {}
        if data.get("type") == "url_verification" and "challenge" in data:
            return Response(data["challenge"], status=200, mimetype="text/plain")
        return handler.handle(request)

    return "OK", 200

@flask_app.route("/")
def home():
    return "✅ Slack Bot is running on Railway!"

@flask_app.route("/healthz")
def health():
    return {"status": "ok"}, 200

# ========= Keep Awake =========
def keep_awake():
    url = os.environ.get("KEEP_AWAKE_URL")
    if not url:
        print("⚠️ KEEP_AWAKE_URL chưa được set, bỏ qua keep-awake")
        return
    if not url.endswith("/"):
        url = url + "/"
    while True:
        try:
            requests.get(url, timeout=8)
            print(f"💤 keep-awake ping: {url}")
        except Exception as e:
            print(f"⚠️ keep-awake error: {e}")
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=keep_awake, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
