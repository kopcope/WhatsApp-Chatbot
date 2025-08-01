#!/usr/bin/env python3
"""
Test script to directly test multi-command functionality
"""

import sys
import os

# Add current directory to path to import webhook_server functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the generate_response function
from webhook_server import generate_response

def test_multi_commands():
    """Test the multi-command functionality directly"""
    
    test_cases = [
        {
            "input": "What's my balance and please send it in a voice message",
            "description": "Balance check with voice response"
        },
        {
            "input": "My account details with audio response",
            "description": "Account info with audio response"
        },
        {
            "input": "Show balance and speak it",
            "description": "Balance check with speak command"
        },
        {
            "input": "Hello and please send it as voice",
            "description": "Greeting with voice response"
        },
        {
            "input": "What's my balance",
            "description": "Simple balance check (text response)"
        }
    ]
    
    print("🧪 Testing Multi-Command Functionality Directly\n")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Input: '{test_case['input']}'")
        
        try:
            # Test the generate_response function directly
            result = generate_response(test_case['input'], "96891224954")
            
            if isinstance(result, tuple):
                response, use_audio = result
                print(f"   ✅ Response: '{response[:100]}...'")
                print(f"   ✅ Use Audio: {use_audio}")
                print(f"   ✅ Format: {'🎵 AUDIO' if use_audio else '📝 TEXT'}")
            else:
                print(f"   ⚠️  Response: '{result[:100]}...' (old format)")
                print(f"   ⚠️  Use Audio: False (default)")
                print(f"   ⚠️  Format: 📝 TEXT")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("   ✅ Test completed")

if __name__ == "__main__":
    test_multi_commands() 