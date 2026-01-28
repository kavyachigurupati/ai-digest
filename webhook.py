import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()
# print(os.getenv('TEAMS_WEBHOOK_URL'))
# Get webhook URL from environment variable
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL')
# Your Teams webhook URL

# Simple test message
test_message = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Hello from Python! 👋",
                        "weight": "Bolder",
                        "size": "Large"
                    },
                    {
                        "type": "TextBlock",
                        "text": "This is a test message to verify the webhook is working.",
                        "wrap": True
                    }
                ]
            }
        }
    ]
}

# Send the message
response = requests.post(
    TEAMS_WEBHOOK_URL,
    headers={"Content-Type": "application/json"},
    data=json.dumps(test_message)
)

# Check response
if response.status_code == 202:
    print("✅ Message sent successfully!")
else:
    print(f"❌ Failed. Status code: {response.status_code}")
    print(f"Response: {response.text}")