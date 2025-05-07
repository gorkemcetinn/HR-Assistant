# agent.py
from langchain.agents import initialize_agent, AgentType
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from llm_manager import LLMManager
from AGENT.HR_DB.tools import ToolFactory
from config import Config




class AgentWithMemory:
    """Hafıza yönetimini sağlayan agent sınıfı"""

    def __init__(self, default_model=None, flask_app=None):
        """Agent sınıfını başlatır"""
        self.memory = InMemoryChatMessageHistory()
        self.llm_manager = LLMManager()
        self.tool_factory = ToolFactory()
        self.tools = self.tool_factory.create_tools()
        self.current_model = default_model or Config.DEFAULT_MODEL
        self.llm = self.llm_manager.get_llm(self.current_model)
        self.agent = self._initialize_agent()


    def _initialize_agent(self):
        """LLM ve araçlarla yeni bir agent oluşturur"""
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True, # ✅ Hata yakalama aktif
            verbose=True
        )


    def change_model(self, model_name):
        """Kullanılan modeli değiştirir"""
        if self.llm_manager.is_valid_model(model_name):
            self.current_model = model_name
            self.llm = self.llm_manager.get_llm(model_name)
            self.agent = self._initialize_agent()
            return True
        return False

    def clear_memory(self):
        """Sohbet hafızasını temizler"""
        self.memory = InMemoryChatMessageHistory()  # Yeni bir boş hafıza oluştur
        return True

    def get_chat_history(self):
        """Sohbet geçmişinden son mesajları al"""
        messages = self.memory.messages
        if not messages:
            return "Henüz konuşma geçmişi yok."

        formatted_history = ""
        for message in messages:
            if isinstance(message, HumanMessage):
                formatted_history += f"İnsan: {message.content}\n"
            elif isinstance(message, AIMessage):
                formatted_history += f"AI: {message.content}\n"

        return formatted_history

    def process(self, user_id, user_input):
        """Kullanıcı girdisini işle ve yanıt ver"""
        # Geçmiş mesajları al
        chat_history = self.get_chat_history()

        # Kullanıcı mesajını hafızaya ekle
        self.memory.add_user_message(user_input)

        # Agent'a geçmiş ve güncel mesajı gönder
        agent_input = f"""
    🔍 **Kullanıcı ID:** {user_id}

    **Konuşma Geçmişi:**
    {chat_history}

    **Kullanıcının Son Mesajı:** {user_input}

    Yanıtını oluştururken konuşma geçmişindeki bilgileri göz önünde bulundur.
    Soruları yanıtlarken elinde olmayan bir fonksiyon ise diğer fonskiyonları kullanarak çözebiliyorsan eğer çözmeye çalış.
    Sadece ilgili soruları cevapla.
    """

        try:
            # Agent'ı çağır ve user_id'yi ToolFactory fonksiyonlarına geçir
            response = self.agent.invoke({"input": agent_input, "user_id": user_id})
            output = response["output"]

            # Eğer çıktı HTML tabloysa, tekrar tabloya çevirmeye çalışma
            if isinstance(output, str) and output.strip().startswith("<table"):
                self.memory.add_ai_message("İşte tablo verisi gösterildi.")
                return {
                    "type": "table",
                    "message": "İşte tablo verisi:",
                    "data": output
                }

            # Tekrarlanan cümleleri temizle
            if isinstance(output, str):
                # Cümleyi noktalama işaretlerine göre böl
                import re
                sentences = re.split(r'(?<=[.!?])\s+', output)

                # Tekrarlayan cümleleri tespit et ve temizle
                clean_sentences = []
                for i, sentence in enumerate(sentences):
                    # Eğer bu cümle daha önce eklenmediyse veya son cümle değilse
                    if sentence not in clean_sentences:
                        clean_sentences.append(sentence)
                    # Eğer bu cümle bir önceki cümlenin içinde varsa
                    elif i > 0 and sentence in sentences[i - 1]:
                        continue

                # Temizlenmiş cümleleri birleştir
                output = ' '.join(clean_sentences)

                # Tekrarlayan kelime gruplarını tespit et ve temizle
                words = output.split()
                if len(words) > 10:
                    for length in range(3, 10):  # 3 ile 10 kelime arası grupları kontrol et
                        for i in range(len(words) - length * 2 + 1):
                            phrase1 = ' '.join(words[i:i + length])
                            phrase2 = ' '.join(words[i + length:i + length * 2])
                            if phrase1 == phrase2:
                                # Tekrarlayan grubu çıkar
                                words = words[:i + length] + words[i + length * 2:]
                                break

                # Tekrar birleştir
                output = ' '.join(words)



            # Çalışan listesi geliyorsa, bunu algıla ve JSON formatına dönüştür
            if "Get Employees" in agent_input and isinstance(output, list):
                result = {
                    "type": "table",
                    "message": "İşte tüm çalışanların listesi:",
                    "data": output
                }
                output = result

            # AI yanıtını hafızaya ekle (sadece metin kısmını)
            if isinstance(output, dict):
                self.memory.add_ai_message(output.get("message", "İşlem tamamlandı."))
            else:
                self.memory.add_ai_message(output)

            return output

        except Exception as e:
            error_message = f"Bir hata oluştu: {str(e)}"
            return {"status": "error", "message": error_message}

    def close(self):
        """Kaynakları serbest bırakır"""
        if hasattr(self, 'tool_factory'):
            self.tool_factory.close()
