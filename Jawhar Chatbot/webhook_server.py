#!/usr/bin/env python3
"""Flask webhook server for receiving WhatsApp messages."""

import os
import json
import logging
import hashlib
import hmac
import random
import requests
import tempfile
import base64
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
from langdetect import detect, LangDetectException
import re
import openai

# Command keywords will be defined here for new commands

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# WhatsApp webhook verification token (you can set this in .env)
WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN', 'samidi')

# Message deduplication storage
processed_messages = set()
MAX_PROCESSED_MESSAGES = 1000  # Keep last 1000 message IDs in memory

# In-memory user database and pending registration state
users = {}  # {phone_number: name}
pending_registrations = {}  # {phone_number: True}

# Store last responses for each user to enable "repeat message" functionality
last_responses = {}  # {phone_number: last_response_text}

# Google Sheets web app URL
GOOGLE_SHEETS_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzp1Nhosh26AL96Ox1pKAGlXkUW4mctTDY5Xf9CiyUE0qxTfjnwLms0qkn5isFPWLpvyQ/exec"

# Audio response settings - disabled
ENABLE_AUDIO_RESPONSES = False

# Ensure you have OPENAI_API_KEY in your .env file
openai.api_key = os.getenv('OPENAI_API_KEY')

def verify_webhook_signature(payload, signature):
    """Verify the webhook signature from WhatsApp."""
    try:
        # Get the app secret from environment
        app_secret = os.getenv('WHATSAPP_APP_SECRET')
        if not app_secret:
            logger.warning("No app secret found, skipping signature verification")
            return True
        
        # Create expected signature
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False


def process_message(message_data):
    """Process incoming WhatsApp message."""
    try:
        # Extract message details
        from_number = message_data.get('from')
        message_type = message_data.get('type')
        timestamp = message_data.get('timestamp')
        message_id = message_data.get('id')
        
        # Check if this message has already been processed
        if message_id in processed_messages:
            logger.info(f"🔄 Skipping duplicate message: {message_id}")
            return
        
        # Check if message is too old (more than 5 minutes)
        try:
            message_time = datetime.fromtimestamp(int(timestamp))
            current_time = datetime.now()
            time_diff = current_time - message_time
            
            if time_diff > timedelta(minutes=5):
                logger.info(f"⏰ Skipping old message from {time_diff.total_seconds():.0f}s ago: {message_id}")
                # Still add to processed set to avoid reprocessing
                processed_messages.add(message_id)
                return
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp: {timestamp}")
        
        # Add message to processed set
        processed_messages.add(message_id)
        
        # Clean up old messages if set gets too large
        if len(processed_messages) > MAX_PROCESSED_MESSAGES:
            # Remove oldest messages (this is a simple approach)
            processed_messages.clear()
            logger.info("🧹 Cleaned up processed messages cache")
        
        logger.info(f"📨 Received message from {from_number}")
        logger.info(f"   Type: {message_type}")
        logger.info(f"   Timestamp: {timestamp}")
        logger.info(f"   Message ID: {message_id}")
        
        if message_type == 'text':
            text = message_data.get('text', {}).get('body', '')
            logger.info(f"   Text: {text}")
            
            # Generate response
            response_result = generate_response(text, from_number)
            
            # If generate_response returns None, it already handled the response
            if response_result is None:
                return
            
            # Send response
            send_response(from_number, response_result)
            
        elif message_type == 'image':
            logger.info("   Image received - not supported")
            send_response(from_number, "Image processing is not available.")
            
        elif message_type == 'document':
            logger.info("   Document received")
            send_response(from_number, "Document processing is not available.")
            
        else:
            logger.info(f"   Unsupported message type: {message_type}")
            send_response(from_number, f"I received your {message_type} message!")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")


# OpenAI response function removed - bot will only respond to specific commands


def generate_response(user_message, from_number):
    """Generate response for user message."""
    user_message_lower = user_message.lower().strip()

    # If user is pending registration, treat this message as their name
    if pending_registrations.get(from_number):
        name = user_message.strip()
        reg_result = register_user_in_sheet(from_number, name)
        pending_registrations.pop(from_number, None)
        if reg_result and reg_result.get("status") == "success":
            return f"✅ Thank you, {name}! You have been registered successfully."
        else:
            return f"❌ Sorry, there was a problem registering you. Please try again later."

    # Check for introduction/greeting messages
    greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'salam', 'marhaba']
    if any(greeting in user_message_lower for greeting in greeting_keywords):
        # Check if user is registered
        user_result = find_user_in_sheet(from_number)
        if user_result and user_result.get("status") == "success" and user_result.get("user_found"):
            user_name = user_result.get("name", "there")
            return (f"👋 Hello {user_name}! Welcome back. How can I help you today?")
        else:
            # User is not registered - prompt for name and set pending registration
            pending_registrations[from_number] = True
            return ("👋 Hello and welcome!\n"
                    "I'm Jawhar, your friendly recycling assistant. ♻️\n"
                    "Whether you are unsure about what to recycle, where to take items, or how to reduce waste I'm here to make it easy. 🌍✨\n"
                    "I noticed you haven't registered yet - no worries! It's quick and easy.\n"
                    "To get registered reply with your name.")
    # No other commands implemented yet
    return None


def send_response(to_number, message, use_audio=False):
    """Send text response to WhatsApp user."""
    logger.info(f"[DEBUG] Entered send_response with to_number: {to_number}, message: {message}")
    try:
        access_token = os.getenv('WHATSAPP_API_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        logger.debug(f"[DEBUG] send_response: access_token={access_token[:6]}...{access_token[-4:] if access_token else None}, phone_number_id={phone_number_id}")
        if not access_token or not phone_number_id:
            logger.error("Missing WhatsApp API credentials")
            return False
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        logger.info(f"[DEBUG] Sending message payload to WhatsApp: {payload}")
        logger.info(f"[DEBUG] Request headers: {headers}")
        logger.info(f"[DEBUG] Request URL: {url}")
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"[DEBUG] WhatsApp API response status: {response.status_code}")
        logger.info(f"[DEBUG] WhatsApp API response text: {response.text}")
        if response.status_code == 200:
            logger.info(f"✅ Response sent to {to_number}")
            logger.info(f"[DEBUG] Exiting send_response with success")
            return True
        else:
            logger.error(f"❌ Failed to send response: {response.status_code}")
            logger.error(f"Response: {response.text}")
            logger.info(f"[DEBUG] Exiting send_response with failure")
            return False
    except Exception as e:
        logger.error(f"Error sending response: {e}")
        logger.info(f"[DEBUG] Exiting send_response with exception")
        return False


@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook endpoint for WhatsApp."""
    try:
        # Get verification parameters
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        logger.info(f"🔐 Webhook verification request:")
        logger.info(f"   Mode: {mode}")
        logger.info(f"   Token: {token}")
        logger.info(f"   Challenge: {challenge}")
        
        # Verify the webhook
        if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
            logger.info("✅ Webhook verified successfully!")
            return challenge
        else:
            logger.error("❌ Webhook verification failed!")
            return 'Forbidden', 403
            
    except Exception as e:
        logger.error(f"Error in webhook verification: {e}")
        return 'Internal Server Error', 500


@app.route('/webhook', methods=['POST'])
def receive_message():
    """Receive incoming WhatsApp messages."""
    try:
        # Temporarily disable signature verification for testing
        # signature = request.headers.get('X-Hub-Signature-256')
        # if signature and not verify_webhook_signature(request.data, signature):
        #     logger.error("❌ Invalid webhook signature")
        #     return 'Unauthorized', 401
        
        # Parse the webhook data
        data = request.get_json()
        logger.info(f"📥 Received webhook data: {json.dumps(data, indent=2)}")
        
        # Extract messages
        if 'object' in data and data['object'] == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('value', {}).get('messages'):
                        for message in change['value']['messages']:
                            process_message(message)
        
        return make_response(jsonify({"status": "ok"}), 200)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Always return 200 OK to Meta
        return make_response(jsonify({"status": "ok"}), 200)


@app.route('/')
def home():
    """Home page."""
    return '''
    <h1>WhatsApp Chatbot Webhook</h1>
    <p>Your webhook server is running!</p>
    <p>Webhook URL: <code>/webhook</code></p>
    <p>Status: ✅ Active</p>
    '''


def register_user_in_sheet(phone, name):
    payload = {
        "action": "register",
        "phone": phone,
        "name": name
    }
    try:
        response = requests.post(GOOGLE_SHEETS_WEBAPP_URL, json=payload, timeout=5)
        print("Sheets register response:", response.text)  # Debug print
        
        # Try to parse as JSON first, fallback to text
        try:
            return response.json()
        except json.JSONDecodeError:
            # If not JSON, treat as text response
            return {"status": "success", "message": response.text.strip()}
            
    except Exception as e:
        logger.error(f"Error registering user in Google Sheets: {e}")
        return {"status": "error", "message": str(e)}

def find_user_in_sheet(phone):
    payload = {
        "action": "find",
        "phone": phone
    }
    try:
        response = requests.post(GOOGLE_SHEETS_WEBAPP_URL, json=payload, timeout=5)
        print("Sheets find response:", response.text)  # Debug print
        
        # Try to parse as JSON first, fallback to text
        try:
            return response.json()
        except json.JSONDecodeError:
            # If not JSON, treat as text response
            return {"status": "success", "message": response.text.strip()}
            
    except Exception as e:
        logger.error(f"Error looking up user in Google Sheets: {e}")
        return {"status": "error", "message": str(e)}

def check_balance_in_sheet(phone):
    """Check user's points balance in Google Sheets."""
    payload = {
        "action": "check_balance",
        "phone": phone
    }
    try:
        response = requests.post(GOOGLE_SHEETS_WEBAPP_URL, json=payload, timeout=5)
        print("Sheets balance response:", response.text)  # Debug print
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid response format"}
            
    except Exception as e:
        logger.error(f"Error checking balance in Google Sheets: {e}")
        return {"status": "error", "message": str(e)}

def update_points_in_sheet(phone, points_to_add, admin_secret):
    """Update user's points in Google Sheets (admin only)."""
    payload = {
        "action": "update_points",
        "phone": phone,
        "points": points_to_add,
        "admin_secret": admin_secret
    }
    try:
        response = requests.post(GOOGLE_SHEETS_WEBAPP_URL, json=payload, timeout=5)
        print("Sheets update points response:", response.text)  # Debug print
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid response format"}
            
    except Exception as e:
        logger.error(f"Error updating points in Google Sheets: {e}")
        return {"status": "error", "message": str(e)}

# Audio and image processing functions removed

def handle_introduction(from_number):
    """Handle introduction and check if user is registered."""
    try:
        # Check if user exists in Google Sheets
        user_result = find_user_in_sheet(from_number)
            
        if user_result and user_result.get("status") == "success" and user_result.get("user_found"):
            # User is registered
            user_name = user_result.get("name", "there")
            return (f"👋 Hello {user_name}! Welcome back. How can I help you today?")
        else:
            # User is not registered - send multiple welcome messages
            return handle_new_user_welcome(from_number)
            
    except Exception as e:
        logger.error(f"Error handling introduction: {e}")
        return handle_new_user_welcome(from_number)

def handle_new_user_welcome(from_number):
    """Send multiple welcome messages for new users."""
    messages = [
        "👋 Hello and welcome!",
        "I'm Jawhar, your friendly recycling assistant. ♻️",
        "Whether you are unsure about what to recycle, where to take items, or how to reduce waste I'm here to make it easy. 🌍✨",
        "I noticed you haven't registered yet - no worries! It's quick and easy.",
        "To get registered reply with your name."
    ]
    
    # Send each message separately
    for message in messages:
        send_response(from_number, message)
        time.sleep(0.5)  # Small delay between messages
    
    return None  # Return None since we handled the response manually

# Helper functions for new commands will be added here 

# Command response functions will be added here for new commands

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False) 