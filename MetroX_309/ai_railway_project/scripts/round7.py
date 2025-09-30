import requests

# Your ngrok-exposed API endpoint
URL = "https://245cd493af69.ngrok-free.app/ask"

# --- Option 1: Send JSON body ---
resp_json = requests.post(URL, json={"question": "What year was the World Wide Web proposed?"})
print("JSON request:", resp_json.text)

# --- Option 2: Send raw text body ---
resp_text = requests.post(URL, data="What year was the World Wide Web proposed?")
print("Raw text request:", resp_text.text)
