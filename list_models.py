# list_models.py
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

client = Anthropic(api_key=api_key)

def print_models():
    models = client.models.list()
    print("Available models for this key:")
    for m in models.data:
        print("-", m.id, " | display name:", m.display_name)

if __name__ == "__main__":
    print_models()
