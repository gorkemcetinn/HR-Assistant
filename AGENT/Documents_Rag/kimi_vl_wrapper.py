import base64
import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env içeriğini yükle
load_dotenv()

class KimiVLWrapper:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        # self.api_url = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1/chat/completions")
        self.model = "google/gemma-3-27b-it:free"
        logging.info(f"✅ İmage Selector API key yüklendi mi? => {bool(self.api_key)}")

    def encode_image(self, image_path):
        """Görseli base64 formatına çevir"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def ask(self, image_path, question):
        image_base64 = self.encode_image(image_path)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "AssistantAgent"
        }

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Tüm yanıtlarını yalnızca Türkçe dilinde ver. Yanıtlarında İngilizce kullanmaktan kaçın."},
                {"role": "user", "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ]}
            ],
            "temperature": 0.6
        }

        response = requests.post(self.api_url, headers=headers, json=body)
        print("🔧 RAW RESPONSE:", response.text)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


