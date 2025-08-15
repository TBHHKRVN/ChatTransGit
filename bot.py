import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

app_slack = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

@ app_slack.event("app_mention")
def handle_app_mention(event, say):
    user = event["user"]
    say(f"Xin chào <@{user}>! 🚀 Mình đang chạy trên Railway 24/7!")

flask_app = Flask(__name__)
handler = SlackRequestHandler(app_slack)

@flask_app.route("/slack/events", methods=["POST", "GET"])
def slack_events():
    # Trả challenge ngay khi Slack verify
    if request.method == "POST":
        data = request.get_json(silent=True, force=True) or {}
        if data.get("type") == "url_verification" and "challenge" in data:
            return data["challenge"], 200, {"Content-Type": "text/plain"}
        # Các request còn lại để Bolt xử lý (events thực tế)
        return handler.handle(request)
    return "OK", 200  # GET: để Slack/you test nhanh

@flask_app.route("/")
def home():
    return "✅ Slack Bot is running on Railway!"