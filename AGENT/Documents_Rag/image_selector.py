import os
import json
from AGENT.Documents_Rag.kimi_vl_wrapper import KimiVLWrapper
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ImageSelector:
    def __init__(self, image_folder="static/images", cache_file="image_cache.json"):
        self.image_folder = image_folder
        self.cache_file = cache_file
        self.kimi = KimiVLWrapper()
        self.text_encoder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        #intfloat/multilingual-e5-large-instruct bu modelin türkçe dil desteği daha iyi seviyede
        self.keyword_extractor = KeyBERT(model=self.text_encoder)
        self.image_data = []

    def cosine_similarity(self, vec1, vec2):
        if np.linalg.norm(vec1) * np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1 / np.linalg.norm(vec1), vec2 / np.linalg.norm(vec2))

    def load_cache(self):
        if not os.path.exists(self.cache_file):
            return {}

        with open(self.cache_file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_cache(self, cache_data):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def prepare_images(self):
        self.image_data = []
        image_files = [f for f in os.listdir(self.image_folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        logging.info(f"{len(image_files)} görsel hazırlanıyor...")

        cache = self.load_cache()
        updated = False

        for filename in image_files:
            full_path = os.path.join(self.image_folder, filename)

            desc = None
            embedding = None

            if filename in cache:
                desc = cache[filename].get("description", "")
                embedding = np.array(cache[filename].get("embedding", []))
                logging.info(f"Cache kullanıldı ({filename})")
            else:
                try:
                    desc = self.kimi.ask(
                        full_path,
                        """Lütfen yalnızca Türkçe dilinde yanıt ver. 
                                    Görseli detaylı ve kapsamlı bir şekilde analiz et.
                                    - Görselin amacı nedir? 
                                    - İçeriğinde hangi ögeler yer alıyor? 
                                    - Hangi kuralları veya kullanım senaryolarını içeriyor? 
                                    Bu sorulara madde madde kısa ve net açıklamalar yaparak cevap ver. 
                                    Son olarak, tüm maddeleri değerlendirerek görselin genel amacı hakkında mantıklı bir sonuç çıkar.""")
                    if not desc:
                        logging.info(f"⚠️ Açıklama alınamadı ({filename}), atlanıyor.")
                        continue

                    embedding = self.text_encoder.encode(desc).tolist()
                    cache[filename] = {
                        "description": desc,
                        "embedding": embedding
                    }
                    updated = True
                    logging.info(f"Açıklama alındı ({filename}): {desc}")

                except Exception as e:
                    logging.error(f"❌ Açıklama hatası ({filename}): {e}")
                    continue

            if desc and embedding is not None:
                self.image_data.append({
                    "path": full_path,
                    "filename": filename,
                    "description": desc,
                    "embedding": np.array(embedding)
                })

        if updated:
            self.save_cache(cache)

    def extract_keywords(self, text, top_n=3):
        keywords = self.keyword_extractor.extract_keywords(
            text,
            top_n=top_n,
            stop_words=None ,
            use_mmr=True,
            diversity=0.4
        )
        return [kw for kw, score in keywords]

    def select_best_image(self, user_question):
        if not self.image_data:
            logging.info("⚠️ Görseller henüz hazırlanmadı!")
            return None

        try:
            question_vec = self.text_encoder.encode(user_question)
            scores = []

            for item in self.image_data:
                sim = self.cosine_similarity(question_vec, item["embedding"])
                scores.append((item["path"], sim, item["description"]))

            scores = sorted(scores, key=lambda x: x[1], reverse=True)

            logging.info("\nEn İyi Eşleşmeler:")
            for i, (path, sim, desc) in enumerate(scores[:3]):
                keywords = self.extract_keywords(desc)
                logging.info(f"{i + 1}. {os.path.basename(path)} (benzerlik: {sim:.2f}) ➜ Anahtar Kelimeler: {keywords}")

            return scores[0][0] if scores and scores[0][1] >= 0.40 else None

        except Exception as e:
            logging.error(f"❌ Sıralama hatası: {e}")
            return None


if __name__ == "__main__":
    selector = ImageSelector("static/images")
    selector.prepare_images()

    while True:
        soru = input("\nSoru girin (çıkmak için 'exit'): ")
        if soru.lower() in ["exit", "quit", "q"]:
            break

        sonuc = selector.select_best_image(soru)
        logging.info(f"\n✅ En uygun görsel: {sonuc}")
