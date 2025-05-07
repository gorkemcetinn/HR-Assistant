import os
import re
import json
from langchain.schema import Document
from llm_manager import LLMManager
from config import Config
from langchain_community.document_loaders import PyPDFLoader
from typing import List, Dict, Any, Optional, Union


# Dizin oluşturma
os.makedirs("./generated_graphs", exist_ok=True)

class GraphAgent:
    """Belge içeriğinden grafik oluşturan ve analiz yapan agent"""

    def __init__(self, model_name=None):
        """Agent'ı başlat ve LLM Manager'ı konfigüre et"""
        self.llm_manager = LLMManager()
        self.model_name = model_name or Config.DEFAULT_MODEL
        self.llm = self.llm_manager.get_llm(self.model_name)

    def process_query(self, documents: List[Document], question: str) -> Dict[str, Any]:
        """Kullanıcı sorgusunu işle ve sonuç döndür"""
        # 1. Soruyu analiz et ve grafik gerekip gerekmediğini belirle
        requires_graph = self._check_if_graph_required(documents, question)

        # 2. Grafik gerekmiyorsa metin yanıtı döndür
        if not requires_graph:
            return {
                "answer": "Bu soru için grafiksel analiz gerekmemektedir.",
                "graph": None,
                "data": None
            }

        # 3. Veriyi çıkar
        data = self._extract_data(documents, question)

        # 4. Yeterli veri yoksa bildir
        if not self._is_valid_data(data):
            return {
                "answer": "Sorunuz için uygun sayısal veri bulunamadı. Lütfen daha spesifik bir soru sorun.",
                "graph": None,
                "data": data
            }

        # 5. En uygun grafik tipini belirle
        graph_type = self._determine_graph_type(data, question)

        # 6. Grafiği oluştur
        graph_path = None  # Artık grafik dosyası oluşturulmuyor

        # 7. İnsan dostu yanıt oluştur
        answer = self._format_answer(data, question, graph_path, graph_type)

        return {
            "answer": answer,
            "graph": None,
            "data": data,
            "graph_type": graph_type
        }

    def _check_if_graph_required(self, documents: List[Document], question: str) -> bool:
        """Grafik gerekip gerekmediğine karar verir"""
        # Belge içeriğinden ilk 4000 karakteri al (token limiti için)
        context = "\n\n".join([doc.page_content for doc in documents])[:4000]

        prompt = f"""
        Aşağıdaki belge içeriği ve kullanıcı sorusunu analiz et:

        BELGE İÇERİĞİ:
        {context}

        SORU:
        {question}

        GÖREV:
        Bu soruda sayısal bir veri var mı, varsa grafikle görselleştirmek faydalı olur mu? Şu durumları değerlendir:
        - Zaman serisi verisi (yıllara, aylara göre değişim vb.)
        - Kategoriler arası karşılaştırma gerektiren veriler
        - Yüzdelik dağılımlar
        - Finansal değerlerin görsel karşılaştırması
        - Büyüme, azalma veya trend göstermesi gereken veriler

        Bir seri halinde değilse bile, karşılaştırmalı tekil değerler varsa (örneğin gelir-gider-kâr) grafik faydalıdır.

        Aşağıdaki JSON formatında cevap ver:

        {{
          "grafik_gerekli": true/false,
          "sebep": "Kararının detaylı gerekçesi",
          "olası_grafik_tipi": "Kullanılabilecek grafik tipi önerisi"
        }}

        Sadece JSON yanıtı ver, başka açıklama ekleme.
        """

        response = self._get_llm_response(prompt)

        try:
            json_data = self._extract_json(response)
            return json_data.get("grafik_gerekli", False)
        except Exception as e:
            print(f"Grafik gereklilik analizi hatası: {e}")
            # Hata durumunda varsayılan olarak True döndür - karşılayamadığımız durumlarda grafik oluşturmayı deneyelim
            return True

    def _extract_data(self, documents: List[Document], question: str) -> Dict[str, Any]:
        """Belge içeriğinden soru ile ilgili veriyi çıkarır"""
        # Belge içeriğini birleştir
        context = "\n\n".join([doc.page_content for doc in documents])

        # İlgili sayfaları hızlıca tanımlamak için ön analiz yap
        relevant_pages = self._identify_relevant_pages(documents, question)

        # Eğer belirli sayfalar tanımlandıysa, sadece onları kullan
        if relevant_pages:
            context = "\n\n".join([doc.page_content for i, doc in enumerate(documents) if i in relevant_pages])

        prompt = f"""
        Aşağıdaki belge içeriğinden "{question}" sorusuna cevap olabilecek sayısal verileri çıkarmanız gerekiyor.

        BELGE İÇERİĞİ:
        {context}

        GÖREV:
        1. Yukarıdaki belge içeriğini dikkatle analiz edin
        2. "{question}" sorusunun cevabı olabilecek sayısal verileri tam olarak bulun
        3. Verinin orijinal formatını (tablo, liste, paragraf içinde) koruyarak analiz edin
        4. Sayısal değerleri doğru şekilde ayıklayın (binlik ayırıcıları, ondalık noktaları vb. dikkat edin)
        5. Veriyi aşağıdaki JSON formatında döndürün

        Yanıtınızı aşağıdaki formatı kullanarak verin:
        ```json
        {{
          "labels": ["Etiket1", "Etiket2", ...],
          "values": [Değer1, Değer2, ...],
          "seri_isimleri": ["Seri1", "Seri2", ...] (birden fazla veri serisi varsa),
          "birim": "TL, $, %, adet vb.",
          "veri_tipi": "para, yüzde, sayı vb.",
          "açıklama": "Bu verinin kısa bir açıklaması"
        }}
        ```

        Tablo veya çoklu seri için:
        - Her bir satır veya kategori "labels" dizisinde
        - Her bir sütun veya seri "seri_isimleri" dizisinde
        - "values" çok boyutlu dizi olmalı: [[seri1_değerleri], [seri2_değerleri], ...]

        SADECE JSON yanıtı verin, başka açıklama eklemeyin.
        """

        response = self._get_llm_response(prompt)

        try:
            data = self._extract_json(response)

            # Sayısal verileri temizle ve dönüştür
            data = self._clean_numeric_data(data)

            return data
        except Exception as e:
            print(f"Veri ayıklama hatası: {e}")
            # Boş veri döndür
            return {"labels": [], "values": [], "açıklama": "Veri ayıklanamadı"}

    def _identify_relevant_pages(self, documents: List[Document], question: str) -> List[int]:
        """Soruyla ilgili sayfaları belirler"""
        if len(documents) <= 3:  # Az sayıda sayfa varsa, hepsini kullan
            return list(range(len(documents)))

        prompt = f"""
        Aşağıdaki belge sayfalarından hangilerinin "{question}" sorusuyla ilgili olabileceğini belirleyin.

        {"\n\n".join([f"SAYFA {i + 1}:\n{doc.page_content[:300]}..." for i, doc in enumerate(documents)])}

        GÖREV:
        İlgili sayfaların indekslerini 0'dan başlayarak JSON formatında döndürün:

        ```json
        {{
          "ilgili_sayfalar": [0, 2, 5]
        }}
        ```

        Sadece JSON formatında cevap verin.
        """

        response = self._get_llm_response(prompt)

        try:
            json_data = self._extract_json(response)
            return json_data.get("ilgili_sayfalar", [])
        except:
            # Hata durumunda tüm sayfaları döndür
            return list(range(len(documents)))

    def _clean_numeric_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sayısal verileri temizler ve dönüştürür"""
        # Values'ı temizle
        if "values" in data:
            if isinstance(data["values"], list):
                if data["values"] and isinstance(data["values"][0], list):
                    # Çok boyutlu dizi
                    data["values"] = [[self._parse_numeric_value(v) for v in series] for series in data["values"]]
                else:
                    # Tek boyutlu dizi
                    data["values"] = [self._parse_numeric_value(v) for v in data["values"]]

        return data

    def _parse_numeric_value(self, value: Any) -> float:
        """Sayısal değeri temizler ve float'a çevirir"""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Yaygın biçimlendirmeleri temizle
            value = value.replace("%", "")

            # Türkçe/Avrupa formatı: 1.234,56 -> 1234.56
            if "," in value and "." in value and value.find(".") < value.find(","):
                value = value.replace(".", "").replace(",", ".")
            # Amerikan formatı: 1,234.56 -> 1234.56
            elif "," in value and "." in value:
                value = value.replace(",", "")
            # Sadece virgüllü: 1234,56 -> 1234.56
            elif "," in value and "." not in value:
                value = value.replace(",", ".")

            # Gereksiz karakterleri temizle
            value = re.sub(r"[^\d.-]", "", value)

            try:
                return float(value)
            except:
                return 0.0

        return 0.0

    def _determine_graph_type(self, data: Dict[str, Any], question: str) -> str:
        """Veri ve soruya göre en uygun grafik tipini belirler"""
        prompt = f"""
        Aşağıdaki veri ve soru için en uygun grafik türünü seçin:

        SORU: {question}

        VERİ: {json.dumps(data, ensure_ascii=False)}

        GÖREV:
        1. Veri yapısını analiz edin
        2. Sorunun amacını değerlendirin
        3. En uygun grafik türünü belirleyin

        Mümkün olan grafik türleri:
        - "çizgi": Zaman içindeki değişimleri, trendleri göstermek için
        - "çubuk": Kategoriler arası karşılaştırmalar için
        - "yatay_çubuk": Uzun etiketli kategorileri karşılaştırmak için
        - "pasta": Bir bütünün parçalarının oranlarını göstermek için
        - "çift_eksen": İki farklı ölçekte veri göstermek için
        - "yığın_çubuk": Kategorileri alt gruplara bölerek karşılaştırmak için
        - "alan": Zaman içindeki kümülatif değişimleri göstermek için

        Yanıtınızı aşağıdaki JSON formatında verin:
        ```json
        {{
          "grafik_türü": "seçilen_grafik_türü",
          "gerekçe": "Kısa açıklama"
        }}
        ```

        SADECE JSON yanıtı verin, başka açıklama eklemeyin.
        """

        response = self._get_llm_response(prompt)

        try:
            json_data = self._extract_json(response)
            return json_data.get("grafik_türü", "çubuk")
        except:
            # Varsayılan olarak çubuk grafiği döndür
            return "çubuk"

    def _create_graph(self, data: Dict[str, Any], question: str, graph_type: str) -> Optional[str]:
        """Chart.js kullanılacağı için grafik oluşturulmuyor"""
        return None

    def _format_answer(self, data: Dict[str, Any], question: str, graph_path: Optional[str], graph_type: str) -> str:
        """İnsan dostu bir yanıt oluşturur"""
        prompt = f"""
        Aşağıdaki veri, soru ve grafik bilgilerine dayanarak insan dostu bir yanıt oluşturun:

        SORU: {question}

        VERİ: {json.dumps(data, ensure_ascii=False)}

        OLUŞTURULAN GRAFİK TİPİ: {graph_type}

        GRAFİK OLUŞTURULDU MU?: {'Evet' if graph_path else 'Hayır'}

        GÖREV:
        1. Soruya doğrudan ve net bir yanıt verin
        2. Verilere dayalı en önemli 2-3 bulguyu vurgulayın
        3. Varsa ilginç karşılaştırmaları, trendleri veya anomalileri belirtin
        4. Grafik tipinin neden seçildiğini kısaca açıklayın (ör. "Çubuk grafik kategorileri karşılaştırmak için idealdir")
        5. Yanıtınızı 3-5 cümle ile sınırlı tutun, özlü olun

        Örnek yanıt formatı:
        "2023 yılında şirketin toplam geliri 5.4 milyon TL olarak gerçekleşmiştir. En yüksek gelir %40 ile İstanbul bölgesinden, en düşük gelir ise %15 ile Doğu Anadolu bölgesinden elde edilmiştir. Pasta grafik, bölgesel gelir dağılımını net bir şekilde göstermektedir."
        """

        response = self._get_llm_response(prompt)

        return response.strip()

    def _get_llm_response(self, prompt: str) -> str:
        """LLM'den yanıt alır ve yanıtı string olarak döndürür"""
        response = self.llm.invoke(prompt)

        # AIMessage veya başka bir LangChain mesaj nesnesi ile başa çıkma
        if hasattr(response, 'content'):
            return response.content
        else:
            return str(response)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Metinden JSON içeriğini çıkarır"""
        # JSON blok içinde olabilir
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Doğrudan JSON olabilir
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        # JSON bulunamadı
        raise ValueError("JSON formatı bulunamadı")

    def _is_valid_data(self, data: Dict[str, Any]) -> bool:
        """Verinin grafik oluşturmak için yeterli olup olmadığını kontrol eder"""
        return (
                data and
                "labels" in data and
                "values" in data and
                len(data["labels"]) > 0 and
                len(data["values"]) > 0
        )


def load_pdf_documents(pdf_path: str) -> List[Document]:
    """PDF belgesini yükler"""
    loader = PyPDFLoader(pdf_path)
    return loader.load()


def graph_agent(documents: List[Document], question: str) -> Dict[str, Any]:
    """Geriye uyumluluk için ana agent fonksiyonu"""
    agent = GraphAgent()
    return agent.process_query(documents, question)


if __name__ == "__main__":
    pdf_path = r"C:\Users\Can\PycharmProjects\AssistantAgent\data\abc_sirketi_2024_raporu.pdf"
    docs = load_pdf_documents(pdf_path)

    agent = GraphAgent()

    while True:
        q = input("Soru: ")
        if q.lower() in ["exit", "q"]:
            break

        result = agent.process_query(docs, q)
        print("\nYANIT:", result["answer"])
        print("Grafik tipi:", result.get("graph_type", "belirtilmemiş"))
        print("Chart.js ile çizilecek veri:", json.dumps(result["data"], ensure_ascii=False, indent=2))
