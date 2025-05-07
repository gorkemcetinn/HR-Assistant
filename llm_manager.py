# llm_manager.py
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config import Config


class LLMManager:
    """LLM modelleri yönetim sınıfı"""

    def __init__(self):
        """LLM Manager sınıfını başlatır"""
        self.openrouter_api_key = Config.OPENROUTER_API_KEY
        self.gemini_api_key = Config.GEMINI_API_KEY
        self.available_models = Config.AVAILABLE_MODELS
        self.default_model = Config.DEFAULT_MODEL

    def get_llm(self, model_name=None):
        """Belirtilen model adına göre LLM döndürür"""
        if not model_name or model_name not in self.available_models:
            model_name = self.default_model

        model_config = self.available_models[model_name]
        api_type = model_config.get("api_type", "openrouter")

        if api_type == "gemini":
            # Gemini API için ChatGoogleGenerativeAI kullanılır
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.gemini_api_key,
                temperature=0.7,
                convert_system_message_to_human=True
            )
        else:
            # OpenRouter API için ChatOpenAI kullanılır
            return ChatOpenAI(
                model_name=model_name,
                openai_api_key=self.openrouter_api_key
            )

    def is_valid_model(self, model_name):
        """Model adının geçerli olup olmadığını kontrol eder"""
        return model_name in self.available_models

    def get_model_display_name(self, model_name):
        """Model adına karşılık gelen ekran adını döndürür"""
        if model_name in self.available_models:
            return self.available_models[model_name]["display_name"]
        return "Bilinmeyen Model"

    def get_available_models_list(self):
        """Kullanılabilir modellerin listesini döndürür"""
        return [
            {
                "id": model_id,
                "name": model_info["display_name"],
                "api_type": model_info["api_type"]
            }
            for model_id, model_info in self.available_models.items()
        ]