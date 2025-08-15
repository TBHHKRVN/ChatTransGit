import os
import threading
import time
import requests
from flask import Flask, request, Response
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler


# ========= Slack Bolt App =========
app_slack = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# Trả lời khi được mention trong kênh
@app_slack.event("app_mention")
def handle_app_mention(event, say):
    user = event.get("user")
    say(f"Xin chào <@{user}>! 🚀 Mình đang chạy trên Railway 24/7!")


# Trả lời tin nhắn trực tiếp (DM) gửi cho bot
@app_slack.event("message")
def handle_dm_events(event, say, logger):
    # Chỉ xử lý DM (channel_type = "im"), bỏ qua tin do bot gửi (subtype=bot_message)
    if event.get("channel_type") != "im":
        return
    if event.get("subtype") == "bot_message":
        return
    user = event.get("user")
    text = event.get("text", "").strip()
    if not text:
        return
    say(f"Chào <@{user}>! Bạn vừa nói: “{text}”. Mình đang online ✅")


# ========= Flask App (HTTP) =========
flask_app = Flask(__name__)
handler = SlackRequestHandler(app_slack)


@flask_app.route("/slack/events", methods=["POST", "GET"])
def slack_events():
    # Slack đôi khi sẽ retry, tránh log rác/loop
    if request.headers.get("X-Slack-Retry-Num"):
        # Trả 200 để Slack dừng retry (nếu bạn đã xử lý theo idempotency)
        pass

    if request.method == "POST":
        data = request.get_json(silent=True, force=True) or {}

        # Bước verify URL lần đầu từ Slack
        if data.get("type") == "url_verification" and "challenge" in data:
            # Slack yêu cầu trả về challenge dạng text/plain
            return Response(data["challenge"], status=200, mimetype="text/plain")

        # Các event thực tế giao cho Slack Bolt xử lý
        return handler.handle(request)

    # GET: healthcheck đơn giản
    return "OK", 200


@flask_app.route("/")
def home():
    return "✅ Slack Bot is running on Railway!"


@flask_app.route("/healthz")
def health():
    return {"status": "ok"}, 200


# ========= Keep Awake (tùy chọn) =========
def keep_awake():
    """
    Ping chính domain của app để hạn chế việc service bị sleep.
    Set biến môi trường KEEP_AWAKE_URL = https://<project>.up.railway.app/
    """
    url = os.environ.get("KEEP_AWAKE_URL")
    if not url:
        print("⚠️  KEEP_AWAKE_URL chưa được set, bỏ qua keep-awake")
        return
    # Đảm bảo có dấu gạch chéo cuối cho đẹp (không bắt buộc)
    if not url.endswith("/"):
        url = url + "/"

    while True:
        try:
            requests.get(url, timeout=8)
            print(f"💤 keep-awake ping: {url}")
        except Exception as e:
            print(f"⚠️  keep-awake error: {e}")
        time.sleep(300)  # 5 phút/ping


if __name__ == "__main__":
    # Chạy keep-awake ở thread nền (nếu có cấu hình URL)
    threading.Thread(target=keep_awake, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
