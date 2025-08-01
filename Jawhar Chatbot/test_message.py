#!/usr/bin/env python3
"""Simple script to send a test WhatsApp message."""

import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_test_message(recipient_phone_number: str, message: str = "Hello! This is a test message from your WhatsApp chatbot."):
    """Send a test message to a phone number."""
    try:
        # Get API credentials from environment
        access_token = os.getenv('WHATSAPP_API_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        
        if not access_token or not phone_number_id:
            logger.error("Missing WhatsApp API credentials in .env file")
            return False
        
        # WhatsApp Business API endpoint for sending messages
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Prepare the message payload
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        logger.info(f"Sending test message to {recipient_phone_number}...")
        logger.info(f"Message: {message}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Test message sent successfully!")
            logger.info(f"Message ID: {data.get('messages', [{}])[0].get('id', 'N/A')}")
            return True
        else:
            logger.error(f"❌ Failed to send test message: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Send test message to the specified number
    recipient = "+96891224954"
    message = "Hello! This is a test message from your WhatsApp chatbot. 🚀"
    
    logger.info("Starting WhatsApp test message...")
    
    if send_test_message(recipient, message):
        logger.info("🎉 Test message sent successfully!")
    else:
        logger.error("❌ Failed to send test message!") 