import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Khởi tạo Slack Bolt App với token & signing secret
app_slack = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Event khi bot được mention
@app_slack.event("app_mention")
def handle_app_mention(event, say):
    user = event["user"]
    say(f"Xin chào <@{user}>! 🚀 Mình đang chạy trên Railway 24/7!")

# Flask app để Railway serve
flask_app = Flask(__name__)
handler = SlackRequestHandler(app_slack)

@flask_app.route("/slack/events", methods=["POST", "GET"])
def slack_events():
    if request.method == "POST":
        data = request.get_json(silent=True, force=True) or {}
        print("📩 Incoming Slack event:", data)  # Debug log

        # Slack URL verification
        if data.get("type") == "url_verification" and "challenge" in data:
            return data["challenge"], 200, {"Content-Type": "text/plain"}

        # Các sự kiện khác → để Slack Bolt xử lý
        return handler.handle(request)

    return "OK", 200  # GET request (test ping)

@flask_app.route("/")
def home():
    return "✅ Slack Bot is running on Railway!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
