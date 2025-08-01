#!/usr/bin/env python3
"""Main entry point for the WhatsApp Chatbot application."""

import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_whatsapp_api_connection():
    """Test the WhatsApp API connection."""
    try:
        # Get API credentials from environment
        access_token = os.getenv('WHATSAPP_API_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        
        if not access_token or not phone_number_id:
            logger.error("Missing WhatsApp API credentials in .env file")
            return False
        
        # Debug info (show first/last few characters of token for security)
        token_preview = f"{access_token[:10]}...{access_token[-10:]}" if len(access_token) > 20 else "***"
        logger.info(f"Using token: {token_preview}")
        logger.info(f"Using phone number ID: {phone_number_id}")
        
        # WhatsApp Business API endpoint for getting phone number info
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info("Testing WhatsApp API connection...")
        logger.info(f"Request URL: {url}")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ WhatsApp API connection successful!")
            logger.info(f"Phone number: {data.get('display_phone_number', 'N/A')}")
            logger.info(f"Verified name: {data.get('verified_name', 'N/A')}")
            return True
        else:
            logger.error(f"❌ WhatsApp API connection failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
            # More specific error handling
            if response.status_code == 401:
                logger.error("🔍 401 Error suggests:")
                logger.error("   - Token might be expired")
                logger.error("   - Token might be malformed")
                logger.error("   - Token might not have the right permissions")
            elif response.status_code == 404:
                logger.error("🔍 404 Error suggests:")
                logger.error("   - Phone Number ID might be incorrect")
                logger.error("   - Phone Number ID might not exist")
            
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


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


def main():
    """Main function."""
    logger.info("Starting WhatsApp Chatbot...")
    
    # Test API connection
    if not test_whatsapp_api_connection():
        logger.error("Failed to connect to WhatsApp API. Please check your credentials.")
        return 1
    
    # Ask user if they want to send a test message
    print("\n" + "="*50)
    print("WhatsApp API Connection Test Successful!")
    print("="*50)
    
    send_test = input("Would you like to send a test message? (y/n): ").lower().strip()
    
    if send_test in ['y', 'yes']:
        # Get recipient phone number
        recipient = input("Enter recipient phone number (with country code, e.g., +1234567890): ").strip()
        
        if recipient:
            # Send test message
            if send_test_message(recipient):
                logger.info("🎉 Test completed successfully!")
            else:
                logger.error("❌ Test message failed!")
        else:
            logger.info("No phone number provided. Skipping test message.")
    else:
        logger.info("Skipping test message.")
    
    logger.info("Ready to handle WhatsApp messages!")
    return 0


if __name__ == "__main__":
    exit(main()) 