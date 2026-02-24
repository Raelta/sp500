import requests
import json
from datetime import datetime
import os

def send_google_chat_notification(webhook_url, status, details=None):
    """
    Sends a notification to a Google Chat Webhook.
    
    Args:
        webhook_url (str): The Google Chat Webhook URL.
        status (str): The status of the job (e.g., "SUCCESS", "FAILURE").
        details (dict, optional): A dictionary of details to include in the message.
    """
    if not webhook_url:
        print("Warning: No Google Chat Webhook URL provided. Skipping notification.")
        return

    # Emoji mapping for status
    status_emoji = "✅" if status == "SUCCESS" else "❌"
    
    # Build the message text
    message_text = f"{status_emoji} **Cloud Job {status}**\n"
    message_text += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    if details:
        message_text += "\n**Details:**\n"
        for key, value in details.items():
            message_text += f"• {key}: {value}\n"

    payload = {
        "text": message_text
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        print(f"Notification sent to Google Chat. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending Google Chat notification: {e}")
