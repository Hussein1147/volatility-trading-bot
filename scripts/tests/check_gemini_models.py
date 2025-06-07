#!/usr/bin/env python3
"""
Check available Gemini models
"""

import google.generativeai as genai
import os
import sys

# Load .env file
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()

# Configure with API key
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment")
    sys.exit(1)

genai.configure(api_key=api_key)

print("Available Gemini models:")
print("-" * 40)

try:
    # List all available models
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✓ {model.name}")
            print(f"  Display name: {model.display_name}")
            print(f"  Description: {model.description[:100]}..." if model.description else "  No description")
            print()
except Exception as e:
    print(f"Could not list models: {e}")

print("\nTrying different model names:")
print("-" * 40)

# Test different model names
test_models = [
    'gemini-2.5-pro',
    'gemini-2.0-pro',
    'gemini-2.0-flash',
    'gemini-2.0-flash-exp',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-pro'
]

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'test'")
        print(f"✅ {model_name} - Working!")
    except Exception as e:
        print(f"❌ {model_name} - Error: {str(e)[:50]}...")