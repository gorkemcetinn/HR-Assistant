import os
import hashlib
import glob
import json
import re
import cv2
import numpy as np
from PIL import Image
import easyocr
from zipfile import ZipFile
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from llm_manager import LLMManager
from config import Config
from AGENT.Documents_Rag.image_selector import ImageSelector
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


load_dotenv()

CHROMA_PERSIST_DIR = "./chroma_db"
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
TEMP_IMAGE_DIR = "./temp_images"
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)


# --- OCR İşlevleri ---

def extract_images_from_docx(docx_path, output_folder):
    """DOCX dosyasından görselleri çıkarır ve belirtilen klasöre kaydeder."""
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    extracted_paths = []

    try:
        with ZipFile(docx_path, 'r') as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]

            for idx, image_file in enumerate(image_files):
                image_data = docx_zip.read(image_file)
                image_name = f"{base_name}_{idx}.jpg"
                image_path = os.path.join(output_folder, image_name)

                with open(image_path, 'wb') as img_file:
                    img_file.write(image_data)
                extracted_paths.append(image_path)

        logging.info(f"✅ {len(image_files)} görsel çıkarıldı: {docx_path}")
        return extracted_paths
    except Exception as e:
        print(f"HATA: Görsel çıkarma başarısız ({docx_path}): {e}")
        return []


def extract_text_with_ocr(image_path):
    """Görsel dosyasından OCR ile metin çıkarır."""
    try:
        reader = easyocr.Reader(['tr'])
        image = Image.open(image_path).convert("RGB")

        # Görüntü ön işleme (daha net OCR için)
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # OCR işlemi
        results = reader.readtext(thresh, detail=0, paragraph=True)
        text = " ".join(results)

        # Temizle
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)

        return text
    except Exception as e:
        print(f"OCR hatası ({image_path}): {e}")
        return ""


def process_docx_images(docx_path):
    """DOCX dosyasındaki görselleri işler ve OCR ile metinleri çıkarır."""
    image_paths = extract_images_from_docx(docx_path, TEMP_IMAGE_DIR)
    ocr_docs = []

    for img_path in image_paths:
        text = extract_text_with_ocr(img_path)
        if text:
            metadata = {
                'source': docx_path,
                'image_source': img_path,
                'content_type': 'ocr_text'
            }
            ocr_docs.append(Document(page_content=text, metadata=metadata))

    return ocr_docs


# --- RAG İşlevleri ---

def calculate_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def load_existing_hashes(hash_file='processed_hashes.json'):
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            return json.load(f)
    return {}


def save_hashes(hashes, hash_file='processed_hashes.json'):
    with open(hash_file, 'w') as f:
        json.dump(hashes, f)


def split_documents(documents):
    if not documents:
        print("HATA: Bölünecek belge bulunmadı!")
        return []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=384,
        chunk_overlap=64,
        length_function=len,
    )
    split_docs = text_splitter.split_documents(documents)

    # Ensure page number is preserved in each chunk
    for doc in split_docs:
        if doc.page_content:
            doc.page_content = re.sub(r'\s+', ' ', doc.page_content.strip().lower())
        # For PDF files, page is usually already in metadata
        if 'page' not in doc.metadata and 'source' in doc.metadata:
            # For non-PDF files, use default page 1 or try to extract from other metadata
            doc.metadata['page'] = doc.metadata.get('chunk_index', 0) // 5 + 1  # Rough estimation: 5 chunks per page

    return split_docs


def get_embeddings_model():
    return HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large-instruct",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )


def create_or_load_vector_db():
    embeddings = get_embeddings_model()
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = chroma_client.get_or_create_collection(name="document_collection")
    db = Chroma(
        client=chroma_client,
        collection_name="document_collection",
        embedding_function=embeddings
    )
    return db


def process_new_documents(directory, hash_db='processed_hashes.json'):
    processed_hashes = load_existing_hashes(hash_db)
    new_documents = []
    db = create_or_load_vector_db()
    collection = db.get()
    existing_count = len(collection['ids']) if collection and collection['ids'] else 0
    print(f"Mevcut vektör veritabanında {existing_count} belge parçası bulunuyor.")

    for filepath in glob.glob(f"{directory}/*"):
        if not filepath.endswith(('.pdf', '.docx', '.xlsx')):
            continue

        file_hash = calculate_file_hash(filepath)
        if file_hash in processed_hashes:
            logging.info(f"Dosya zaten işlenmiş: {filepath}")
            continue

        logging.info(f"Yeni dosya bulundu: {filepath}")
        docs = []

        # Doküman içeriğini yükle
        if filepath.endswith('.pdf'):
            loader = PyPDFLoader(filepath)
            docs = loader.load()
            for doc in docs:
                if 'page' in doc.metadata:
                    doc.metadata['page'] += 1  # Sayfa numarasını düzelt
            # PDF loader automatically adds page numbers to metadata
        elif filepath.endswith('.docx'):
            # DOCX dosyası için metin içeriği
            loader = Docx2txtLoader(filepath)
            docs = loader.load()
            for doc in docs:
                if 'page' in doc.metadata:
                    doc.metadata['page'] += 1  # Sayfa numarasını düzelt

            # Add page estimation for DOCX (approximate)
            for i, doc in enumerate(docs):
                doc.metadata['page'] = i // 3 + 1  # Rough estimation: 3 chunks per page

            # DOCX dosyasındaki görselleri işle
            ocr_docs = process_docx_images(filepath)
            if ocr_docs:
                logging.info(f"OCR: {filepath} dosyasından {len(ocr_docs)} görselde metin bulundu")
                # Add page numbers to OCR docs too
                for i, doc in enumerate(ocr_docs):
                    doc.metadata['page'] = doc.metadata.get('page', i + 1)
                docs.extend(ocr_docs)
        elif filepath.endswith('.xlsx'):
            loader = UnstructuredExcelLoader(filepath, mode='elements')
            docs = loader.load()
            # Add sheet information as page for Excel
            for i, doc in enumerate(docs):
                sheet = doc.metadata.get('sheet', '')
                doc.metadata['page'] = f"Sheet: {sheet}" if sheet else i + 1

        if docs:
            chunks = split_documents(docs)

            for i, chunk in enumerate(chunks):
                # Ensure we preserve existing metadata including page numbers
                chunk.metadata.update({
                    'source': filepath,
                    'chunk_index': i,
                    'file_name': os.path.basename(filepath)
                })
                new_documents.append(chunk)

            processed_hashes[file_hash] = filepath

    if new_documents:
        logging.info(f"{len(new_documents)} yeni belge parçası ChromaDB'ye ekleniyor...")
        db.add_documents(new_documents)
        logging.info("Belgeler başarıyla eklendi.")

    save_hashes(processed_hashes, hash_db)
    return db


def create_retriever_from_db(db, k=20):
    return db.as_retriever(search_kwargs={"k": k})


def create_qa_chain(retriever, model_name=None):
    logging.info(f" QA Zinciri Oluşturuluyor - Model: {model_name}")
    if not retriever:
        logging.info("HATA: Retriever oluşturulamadı!")
        return None

    template = """
        Sen bir güvenlik belgeleri analiz asistanısın. Belgelerdeki bilgiye dayalı ve doğru yanıtlar ver.
        Şu kurallara dikkat et:

        1. **Her kelimeyi dikkate al**. Eğer belgelerde herhangi bir bilgiye dair en ufak bir kelime varsa, bu kelimenin ilgili olduğu tüm bilgileri tam ve eksiksiz bir şekilde sağlamalısın.
        2. **Alakasız cevaplar verme**. Sadece soru ile doğrudan bağlantılı olan bilgileri sunmalısın. Alakasız bilgiler, yanıtını geçersiz kılar.
        3. **Kesik bilgi verme**. Cevapların tam, eksiksiz ve kesilmeden olmalıdır. Bir bilgi parçası tamamlanmış bir şekilde verilmelidir.
        4. **Kaynak bilgisi verme**. Cevaplar verirken kaynaklara atıfta bulunma. Bu sadece bilgiyi sunmanın basit bir yolu olmalıdır.
        5. **Yanıtlar mümkün olduğunca ayrıntılı olmalı**. Sorulara, belgelerde yer alan tüm ayrıntılarla yanıt verilmeli ve yalnızca belgelerden alınan bilgiyle sınırlı olmalıdır.

        ### Belgeler:
        {context}

        ### Soru:
        {question}

        ### Yönergeler:
        1. Belgelerde yer alan bilgileri **olduğu gibi** ver. Cevaplar eksiksiz ve net olmalıdır. **Kaynak ekleme veya atıf yapma**.
        2. Belgelerde yer alan tüm **bilgileri kesik veya eksik** vermemelisin. Cevaplar her zaman tam ve açık olmalı.
        3. Eğer sorunun cevabı belgeler arasında **bulunmuyorsa**, şu şekilde yanıt ver: `"Bu sorunun cevabı belgeler arasında bulunamadı."`
        4. **İlgililik skoru ve güvenilirlik skorunu değerlendirin**: 
           - İlgililik skoru: Belgeler soruyla ne kadar ilgili (0.0-1.0 arası)
           - Güvenilirlik: Cevabınızın ne kadar güvenilir olduğu (0.0-1.0 arası)
        5. **Cevabınızda kullandığınız her bir bilgi parçasının hangi belge ve hangi sayfada olduğunu belirtmelisin**, ancak kaynak belirtme (yani sayfa numarası veya belge adı) yapmamalısın.

        Cevabınızı aşağıdaki JSON formatında verin:
        {{
          "model": "{model_name}",
          "relevance_score": (0.0-1.0 arası bir değer),
          "answer": "Belgelere dayalı cevabınız (kaynak referansları olmadan)",
          "confidence": (0.0-1.0 arası bir değer),
          "sources": [
            {{
              "file_name": "belge1.pdf",
              "page": 5,
              "relevance": 0.8
            }},
            // Diğer kaynaklar...
          ]
        }}
    """

    try:
        llm_manager = LLMManager()
        if not model_name:
            model_name = Config.DEFAULT_MODEL
        display_name = llm_manager.get_model_display_name(model_name)
        logging.info(f" Kullanılan Model: {display_name} ({model_name})")
        llm = llm_manager.get_llm(model_name)
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"],
            partial_variables={"model_name": model_name}
        )
        from langchain.chains import LLMChain
        qa_chain = LLMChain(llm=llm, prompt=prompt)
        return qa_chain

    except Exception as e:
        logging.error(f"QA zinciri oluşturulurken hata: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_json_from_response(response):
    try:
        if isinstance(response, dict):
            return response
        content = str(response)
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if json_match:
            return json.loads(json_match.group(1))
        json_match = re.search(r"\{[\s\S]*?\}", content)
        if json_match:
            return json.loads(json_match.group(0))
        return {
            "relevance_score": 0.0,
            "answer": content,
            "confidence": 0.0,
            "model": Config.DEFAULT_MODEL
        }
    except Exception as e:
        print(f"JSON çıkarma hatası: {e}")
        return {
            "relevance_score": 0.0,
            "answer": f"Yanıt işlenirken hata: {str(e)}",
            "confidence": 0.0,
            "model": Config.DEFAULT_MODEL
        }


# --- Grafik Ajanı İşlevleri ---

def check_if_graph_required(documents, question, model_name=None):
    """Soru için grafik gerekip gerekmediğini kontrol eder"""
    # Belge içeriğinden kısa bir özet oluştur
    context = "\n\n".join([doc.page_content for doc in documents])[:4000]

    try:
        llm_manager = LLMManager()
        if not model_name:
            model_name = Config.DEFAULT_MODEL
        llm = llm_manager.get_llm(model_name)

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

        response = llm.invoke(prompt)
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        # JSON yanıtını çıkar
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
            return result

        return {"grafik_gerekli": False, "sebep": "JSON yanıtı alınamadı"}

    except Exception as e:
        print(f"Grafik gereklilik analizi hatası: {e}")
        return {"grafik_gerekli": False, "sebep": f"Hata: {str(e)}"}


def extract_graph_data(documents, question, model_name=None):
    """Belge içeriğinden grafik için veri çıkarır"""
    context = "\n\n".join([doc.page_content for doc in documents])[:6000]

    try:
        llm_manager = LLMManager()
        if not model_name:
            model_name = Config.DEFAULT_MODEL
        llm = llm_manager.get_llm(model_name)

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

        response = llm.invoke(prompt)
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        # JSON yanıtını çıkar
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                return None

        # Sayısal verileri temizle
        if "values" in data:
            if isinstance(data["values"], list):
                if data["values"] and isinstance(data["values"][0], list):
                    # Çok boyutlu dizi
                    data["values"] = [[float(str(v).replace(",", ".")) if isinstance(v, (int, float, str)) else 0
                                       for v in series]
                                      for series in data["values"]]
                else:
                    # Tek boyutlu dizi
                    data["values"] = [float(str(v).replace(",", ".")) if isinstance(v, (int, float, str)) else 0
                                      for v in data["values"]]

        return data

    except Exception as e:
        print(f"Grafik veri çıkarma hatası: {e}")
        return None


def determine_graph_type(data, question, model_name=None):
    """Veri ve soruya göre en uygun grafik tipini belirler"""
    if not data:
        return "çubuk"  # Varsayılan olarak çubuk grafik

    try:
        llm_manager = LLMManager()
        if not model_name:
            model_name = Config.DEFAULT_MODEL
        llm = llm_manager.get_llm(model_name)

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

        response = llm.invoke(prompt)
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        # JSON yanıtını çıkar
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                return "çubuk"

        return result.get("grafik_türü", "çubuk")

    except Exception as e:
        print(f"Grafik türü belirleme hatası: {e}")
        return "çubuk"


def analyze_graph_potential(documents, question, model_name=None):
    """Belgeler ve soru için grafik potansiyelini analiz eder"""
    graph_required = check_if_graph_required(documents, question, model_name)

    if not graph_required.get("grafik_gerekli", False):
        return {
            "grafik_gerekli": False,
            "sebep": graph_required.get("sebep", "Grafik gerekmiyor"),
            "veri": None,
            "grafik_türü": None
        }

    data = extract_graph_data(documents, question, model_name)
    if not data or not data.get("labels") or not data.get("values"):
        return {
            "grafik_gerekli": False,
            "sebep": "Veri çıkarılamadı",
            "veri": None,
            "grafik_türü": None
        }

    graph_type = determine_graph_type(data, question, model_name)

    return {
        "grafik_gerekli": True,
        "sebep": graph_required.get("sebep", "Grafik gerektiren veri bulundu"),
        "veri": data,
        "grafik_türü": graph_type
    }


def answer_query(query, retriever, qa_chain, model_name=None):
    # Initialize image selector
    query = query.strip().lower()
    image_selector = ImageSelector(image_folder="static/images")
    image_selector.prepare_images()

    # Find the most relevant image for the query
    relevant_image_path = image_selector.select_best_image(query)

    # Get the relative path for frontend use if an image was found
    image_rel_path = None
    if relevant_image_path and os.path.exists(relevant_image_path):
        # Convert the absolute path to a relative path for the frontend
        image_rel_path = relevant_image_path.replace(os.path.abspath(os.curdir), '').lstrip('\\/')
        # Make sure the path starts with 'static/'
        if not image_rel_path.startswith('static/'):
            image_rel_path = os.path.join('static', os.path.basename(relevant_image_path))

        # Use forward slashes for web paths
        image_rel_path = image_rel_path.replace('\\', '/')
        logging.info(f"✅ İlgili görsel bulundu: {image_rel_path}")

    relevant_docs = retriever.invoke(query)
    if not relevant_docs:
        result = {
            "model": model_name or Config.DEFAULT_MODEL,
            "relevance_score": 0.0,
            "answer": "Bu soruyla ilgili belge bulunamadı.",
            "confidence": 0.0,
            "sources": []
        }
        # Add image path to result
        if image_rel_path:
            result["image_path"] = image_rel_path
        return result

    # Process docs and gather source information
    context_parts = []
    source_info = []
    relevant_docs_list = []  # Belgeleri sakla

    for i, doc in enumerate(relevant_docs[:20]):
        file_name = os.path.basename(doc.metadata.get('source', 'Bilinmeyen'))
        page = doc.metadata.get('page', 'Bilinmeyen Sayfa')
        content_type = doc.metadata.get('content_type', '')

        # Belgeyi listeye ekle
        relevant_docs_list.append(doc)

        # Create source info for this document chunk
        source_entry = {
            "file_name": file_name,
            "page": page,
            "content_type": content_type,
            "relevance": 0.9 - (i * 0.1)  # Rough estimation of relevance based on retriever order
        }

        # Only add unique sources
        if not any(
                s["file_name"] == source_entry["file_name"] and s["page"] == source_entry["page"] for s in source_info):
            source_info.append(source_entry)

        # Create context entry with source info
        source_text = f"[{file_name}, Sayfa {page}]"
        if content_type == 'ocr_text':
            source_text += " [OCR metin]"

        context_parts.append(f"{source_text}\n{doc.page_content}")

    context = "\n\n".join(context_parts)

    # Grafik analizi yap
    graph_analysis = analyze_graph_potential(relevant_docs_list, query, model_name)

    try:
        response = qa_chain.invoke({
            "context": context,
            "question": query,
            "model_name": model_name or Config.DEFAULT_MODEL
        })

        if isinstance(response, dict) and 'text' in response:
            response_dict = extract_json_from_response(response['text'])
        else:
            response_dict = extract_json_from_response(response)

        # Add model name and source information
        response_dict["model"] = model_name or Config.DEFAULT_MODEL

        # If LLM didn't return source information, add it from our metadata
        if "sources" not in response_dict or not response_dict["sources"]:
            response_dict["sources"] = source_info

        # Add image path to result if we found a relevant image
        if image_rel_path:
            response_dict["image_path"] = image_rel_path

        # Grafik bilgilerini yanıta ekle
        if graph_analysis.get("grafik_gerekli", False):
            response_dict["graph_data"] = graph_analysis["veri"]
            response_dict["graph_type"] = graph_analysis["grafik_türü"]

        return response_dict

    except Exception as e:
        print(f"Soru cevaplama sırasında hata: {e}")
        import traceback
        traceback.print_exc()
        result = {
            "model": model_name or Config.DEFAULT_MODEL,
            "relevance_score": 0.0,
            "answer": f"Soru cevaplanırken bir hata oluştu: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }
        # Add image path to result if we found a relevant image
        if image_rel_path:
            result["image_path"] = image_rel_path
        return result