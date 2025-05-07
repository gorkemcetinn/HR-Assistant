# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from AGENT.SQL_Agent.agent import AgentWithMemory
from config import Config
from llm_manager import LLMManager
from AGENT.HR_DB.user_database import UserDatabase
from AGENT.HR_DB.auth_database import AuthDatabase
from AGENT.HR_DB.hr_tools import HRTools  # Dosyanın en üst kısmında zaten olabilir ama yoksa ekle
import secrets
from AGENT.Documents_Rag.read_rag import answer_query,process_new_documents, create_retriever_from_db, create_qa_chain
from AGENT.Documents_Rag.image_selector import ImageSelector
import os
from extract_image import extract_images_and_tables

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class FlaskApp:
    """Flask uygulama sınıfı"""

    def __init__(self):
        """Flask uygulamasını başlatır"""
        self.app = Flask(__name__)
        self.app.secret_key = Config.SECRET_KEY or secrets.token_hex(16)  # Session için gizli anahtar
        CORS(self.app)  # Cross-Origin isteklerine izin ver
        # 1) data/ içindeki tüm PDF'lerden görsel/tablo çıkart
        extract_images_and_tables(
            data_folder = "data",
            output_folder = "static/images",
            pad = 5,
            resolution = 200
        )
        self.agent = AgentWithMemory()
        self.llm_manager = LLMManager()
        self.user_db = UserDatabase(
            host=Config.DB_HOST,
            database=Config.DB_NAME,
            username=Config.DB_USERNAME,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        self.auth_db = AuthDatabase(
            host=Config.DB_HOST,
            database=Config.DB_NAME,
            username=Config.DB_USERNAME,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        # RAG bileşenlerini başlat
        self.initialize_rag()

        self.initialize_image_selector()

        self._register_routes()

    def initialize_image_selector(self):
        """ImageSelector sınıfını başlatır"""
        try:
            self.image_selector = ImageSelector(image_folder="static/images")
            self.image_selector.prepare_images()
            logging.info("✅ ImageSelector başarıyla başlatıldı.")
        except Exception as e:
            logging.error(f"❌ ImageSelector başlatılamadı: {e}")
            self.image_selector = None

    def veri_to_tablo_html(self, metin: str):
        """Markdown benzeri metinsel tabloyu HTML tabloya çevirir"""
        logging.info("✅ veri_to_tablo_html fonksiyonu çalıştı")

        try:
            satirlar = [satir.strip() for satir in metin.strip().split("\n") if satir.strip()]
            if len(satirlar) < 2:
                return "<p>Tablo yapısı eksik</p>"

            basliklar = [b.strip() for b in satirlar[0].split("|") if b.strip()]
            html = "<table class='table table-bordered'><thead><tr>"
            for baslik in basliklar:
                html += f"<th>{baslik}</th>"
            html += "</tr></thead><tbody>"

            for satir in satirlar[2:]:  # 1. satır başlık, 2. satır ayraç (----), sonrası veriler
                hucreler = [h.strip() for h in satir.split("|") if h.strip()]
                html += "<tr>" + "".join(f"<td>{hucre}</td>" for hucre in hucreler) + "</tr>"

            html += "</tbody></table>"
            return html

        except Exception as e:
            logging.error(f"❌ Tabloya çevirme hatası: {e}")
            return "<p>Veri işlenemedi</p>"

    # Bu kısmı app.py içindeki `initialize_rag` fonksiyonu ile değiştirin
    def initialize_rag(self, model_name=None):
        """ChromaDB tabanlı RAG sistemini başlatır"""
        try:

            documents_dir = "./data"

            # ChromaDB veritabanını oluştur veya var olanı yükle
            db = process_new_documents(documents_dir)
            logging.info(f"ChromaDB veritabanı başarıyla yüklendi.")

            if not db:
                logging.info("UYARI: ChromaDB veritabanı oluşturulamadı.")
                self.rag_initialized = False
                return

            # ChromaDB retriever oluştur
            self.retriever = create_retriever_from_db(db)
            if not self.retriever:
                logging.info("HATA: Retriever oluşturulamadı.")
                self.rag_initialized = False
                return

            # Model adı verilmediyse şu anki agent modelini kullan
            if model_name is None:
                model_name = self.agent.current_model

            # QA zinciri oluştur (model adını parametre olarak geçir)
            self.qa_chain = create_qa_chain(self.retriever, model_name)
            if not self.qa_chain:
                logging.info("HATA: QA zinciri oluşturulamadı.")
                self.rag_initialized = False
                return

            logging.info(f"RAG sistemi {model_name} modeli ile başarıyla başlatıldı.")
            self.rag_initialized = True

        except Exception as e:
            logging.info(f"RAG başlatılırken hata: {e}")
            import traceback
            traceback.print_exc()
            self.rag_initialized = False

    def _register_routes(self):
        """API route'larını kaydeder"""

        # Oturum kontrolü dekoratörü
        def login_required(f):
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login'))
                return f(*args, **kwargs)

            decorated_function.__name__ = f.__name__
            return decorated_function

        @self.app.route('/api/get-employees', methods=['GET'])
        @login_required
        def get_employees():
            """Personel listesini döndüren endpoint (sadece admin ve manager erişebilir)"""
            user_id = session.get('user_id')
            roles = session.get('roles', [])

            if 'admin' not in roles and 'manager' not in roles:
                return jsonify({'status': 'error', 'message': 'Yetkisiz erişim'}), 403

            hr = HRTools(
                host=Config.DB_HOST,
                database=Config.DB_NAME,
                port=Config.DB_PORT
            )
            employees = hr.get_employees_raw(user_id)

            if isinstance(employees, str):  # örneğin: ❌ Yetkisiz erişim!
                return jsonify({'status': 'error', 'message': employees})

            return jsonify({
                'status': 'success',
                'employees': [
                        {
                        'username': emp[1],
                        'fullname': emp[3],
                        'email': emp[4],
                        'salary': emp[5],
                        'department': emp[6],
                        } for emp in employees
                ]
            })

        def role_required(required_role):
            """Belirli bir rolü gerektiren yetkilendirme dekoratörü"""

            def decorator(f):
                def decorated_function(*args, **kwargs):
                    if 'user_id' not in session:
                        return jsonify({"status": "error", "message": "Oturum açılmamış."}), 401

                    user_id = session.get('user_id')
                    user_roles = [role[1] for role in self.auth_db.get_user_roles(user_id)]  # Kullanıcının rolleri

                    if required_role not in user_roles:
                        return jsonify({"status": "error", "message": "Yetkisiz erişim."}), 403

                    return f(*args, **kwargs)

                decorated_function.__name__ = f.__name__
                return decorated_function

            return decorator



        @self.app.route('/')
        @login_required
        def index():
            return render_template('index.html', user=session.get('user'))

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if 'user_id' in session:
                return redirect(url_for('index'))

            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')

                logging.info(f"🔍 Giriş denemesi: Kullanıcı: {username}, Şifre: {password}")

                if not username or not password:
                    logging.info("⚠️ Kullanıcı adı veya şifre boş!")
                    return render_template('login.html', error='Kullanıcı adı ve şifre gereklidir.')

                user = self.user_db.authenticate_user(username, password)

                logging.info(f"🔍 Kullanıcı veritabanından döndü: {user}")

                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['fullname'] = user['fullname']
                    session['user'] = user

                    user_roles = [role[1] for role in self.auth_db.get_user_roles(user['id'])]
                    session['roles'] = user_roles

                    logging.info(f"✅ Giriş başarılı: {user['username']}")
                    return redirect(url_for('index'))
                else:
                    logging.info("❌ Giriş başarısız: Geçersiz kullanıcı adı veya şifre")
                    return render_template('login.html', error='Geçersiz kullanıcı adı veya şifre.')

            return render_template('login.html')


        @self.app.route('/api/clear-chat', methods=['POST'])
        @login_required
        def clear_chat():
            """Sohbet geçmişini temizler"""
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"status": "error", "message": "Kullanıcı kimliği bulunamadı!"}), 401

            # Agent'ın hafızasını temizle
            self.agent.clear_memory()

            return jsonify({
                "status": "success",
                "message": "Sohbet geçmişi başarıyla temizlendi."
            })

        @self.app.route('/logout')
        def logout():
            user_id = session.get('user_id')
            if user_id:
                # Çıkış yapmadan önce agent'ın hafızasını temizle
                self.agent.clear_memory()

            session.clear()
            return redirect(url_for('login'))



        @self.app.route('/dashboard')
        def dashboard():
            if 'fullname' in session:
                return render_template('index.html')
            return redirect(url_for('login'))

        @self.app.route('/api/roles', methods=['GET'])
        @login_required
        def get_roles():
            """Tüm rolleri getirir"""
            roles = self.auth_db.get_all_roles()
            return jsonify({"roles": roles})

        @self.app.route('/api/functions', methods=['GET'])
        @login_required
        def get_functions():
            """Tüm fonksiyonları getirir"""
            functions = self.auth_db.get_all_functions()
            functions_list = [{"id": f[0], "name": f[1], "description": f[2]} for f in functions]
            return jsonify({"functions": functions_list})

        @self.app.route('/api/assign-role', methods=['POST'])
        @login_required
        @role_required("admin")
        def assign_role():
            """Kullanıcıya rol atar"""
            data = request.json
            user_id = data.get('user_id')
            role_id = data.get('role_id')

            if self.auth_db.assign_role_to_user(user_id, role_id):
                return jsonify({"status": "success", "message": "Rol başarıyla atandı."})
            else:
                return jsonify({"status": "error", "message": "Rol atama başarısız."})

        @self.app.route('/api/assign-function-to-role', methods=['POST'])
        @login_required
        @role_required("admin")
        def assign_function_to_role():
            """Bir fonksiyonu role atar"""
            data = request.json
            role_id = data.get('role_id')
            function_id = data.get('function_id')

            if self.auth_db.assign_function_to_role(role_id, function_id):
                return jsonify({"status": "success", "message": "Fonksiyon başarıyla role atandı."})
            else:
                return jsonify({"status": "error", "message": "Fonksiyon atama başarısız."})

        @self.app.route('/api/user-roles/<int:user_id>', methods=['GET'])
        @login_required
        @role_required("admin")
        def get_user_roles(user_id):
            """Belirli bir kullanıcının rollerini döndürür"""
            roles = self.auth_db.get_user_roles(user_id)
            return jsonify({"roles": roles})

        @self.app.route('/api/role-functions/<int:role_id>', methods=['GET'])
        @login_required
        def get_role_functions(role_id):
            """Belirli bir role atanmış fonksiyonları getirir"""
            functions = self.auth_db.get_role_functions(role_id)
            return jsonify({"functions": functions})

        @self.app.route('/api/users-by-role/<int:role_id>', methods=['GET'])
        @login_required
        @role_required("admin")
        def get_users_by_role(role_id):
            """Belirli bir role sahip kullanıcıları getirir"""
            users = self.auth_db.get_users_by_role(role_id)
            return jsonify({"users": users})




        @self.app.route('/api/models', methods=['GET'])
        @login_required
        def get_models():
            """Kullanılabilir modellerin listesini döndürür"""
            models = self.llm_manager.get_available_models_list()
            return jsonify({
                "status": "success",
                "models": models
            })


        @self.app.route('/api/change-model', methods=['POST'])
        @login_required
        def change_model():
            data = request.json
            model_name = data.get('model', Config.DEFAULT_MODEL)

            if self.agent.change_model(model_name):
                model_info = Config.AVAILABLE_MODELS[model_name]
                return jsonify({
                    "status": "success",
                    "message": f"Model başarıyla değiştirildi: {model_info['display_name']} ({Config.API_TYPES[model_info['api_type']]})"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "Geçersiz model seçimi"
                })

        @self.app.route('/api/chat', methods=['POST'])
        @login_required
        def chat():
            data = request.json
            user_message = data.get('message', '')
            model_name = data.get('model', self.agent.current_model)
            mode = data.get('mode', 'sql')  # Varsayılan mod SQL

            # Kullanıcı kimliğini session'dan al
            user_id = session.get('user_id')



            if not user_id:
                return jsonify({"status": "error", "message": "Kullanıcı kimliği bulunamadı!"}), 401

            # Eğer model değiştiyse güncelle
            if model_name != self.agent.current_model:
                self.agent.change_model(model_name)

            if not user_message:
                return jsonify({"status": "error", "message": "Mesaj boş olamaz"})


            # Agent'ı çağır ve yanıtı al - user_id'yi iletmek için process fonksiyonunu güncelleyin
            response = self.agent.process(user_id, user_message)

            return jsonify({"response": response})

        @self.app.route('/document-viewer')
        @login_required
        def document_viewer():
            """Belgeleri görüntüleme endpoint'i"""
            file_name = request.args.get('file', '')
            page = request.args.get('page', '1')

            # Güvenlik: dosya adında path traversal saldırılarını önle
            if '..' in file_name or file_name.startswith('/'):
                return "Geçersiz dosya adı", 400

            # Dosya türünü belirle
            file_path = os.path.join('data', file_name)
            if not os.path.exists(file_path):
                return "Dosya bulunamadı", 404

            file_extension = os.path.splitext(file_name)[1].lower()

            # PDF dosyaları için
            if file_extension == '.pdf':
                return render_template('pdf_viewer.html',
                                       file_path=f"/static/documents/{file_name}",
                                       page=page,
                                       file_name=file_name)

            # DOCX, XLSX gibi dosyalar için
            # Bu dosyaları HTML olarak çevirip göstermek için ek işlemler gerekebilir
            # Basit bir çözüm: Bu dosyaları PDF'e çevirip göstermek veya statik HTML'e dönüştürmek

            return render_template('document_viewer.html',
                                   file_path=file_path,
                                   file_name=file_name,
                                   page=page,
                                   file_type=file_extension[1:])  # .pdf -> pdf

        @self.app.route('/api/user-functions', methods=['GET'])
        @login_required
        def get_user_functions():
            """Giriş yapan kullanıcının erişim yetkisi olan fonksiyonları döndürür."""
            if 'user_id' not in session:
                return jsonify({'status': 'error', 'message': 'Oturum bulunamadı.'}), 401

            user_id = session.get('user_id')

            try:
                # Kullanıcının rollerini al
                user_roles = [role[0] for role in self.auth_db.get_user_roles(user_id)]

                # Kullanıcının tüm rollerine ait fonksiyonları topla
                all_functions = []
                for role_id in user_roles:
                    role_functions = self.auth_db.get_role_functions(role_id)
                    all_functions.extend(role_functions)

                # Benzersiz fonksiyonları al (aynı fonksiyon farklı rollerde olabilir)
                unique_functions = {}
                for func in all_functions:
                    func_id = func[0]
                    if func_id not in unique_functions:
                        unique_functions[func_id] = {
                            "id": func_id,
                            "name": func[1],
                            "description": func[2]
                        }

                return jsonify({
                    'status': 'success',
                    'functions': list(unique_functions.values())
                })

            except Exception as e:
                logging.info(f"❌ Kullanıcı fonksiyonları alınırken hata: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Fonksiyon listesi alınırken bir hata oluştu: {str(e)}'
                }), 500

        @self.app.route('/api/document-chat', methods=['POST'])
        @login_required
        def document_chat():
            data = request.json
            user_message = data.get('message', '')
            model_name = request.json.get('model', self.agent.current_model)
            visual_mode = data.get('visual_mode', 'with_image')  # Get visual mode from request

            if not user_message:
                return jsonify({"status": "error", "message": "Mesaj boş olamaz"})

            # Check for image relevance if image selector is initialized and visual mode is enabled
            image_path = None
            if hasattr(self, 'image_selector') and self.image_selector and visual_mode == 'with_image':
                try:
                    # Find most relevant image based on the query
                    relevant_image_path = self.image_selector.select_best_image(user_message)

                    # Use the image if it meets similarity threshold (threshold is applied in the select_best_image method)
                    if relevant_image_path:
                        # Convert to relative path for the frontend
                        image_path = relevant_image_path.replace(os.path.abspath(os.curdir), '').lstrip('\\/')
                        # Make sure the path uses forward slashes
                        image_path = image_path.replace('\\', '/')
                        logging.info(f"✅ İlgili görsel bulundu: {image_path}")
                except Exception as e:
                    logging.error(f"❌ Görsel seçim hatası: {e}")

            if not hasattr(self, 'rag_initialized') or not self.rag_initialized:
                self.initialize_rag(model_name)
                if not self.rag_initialized:
                    return jsonify({
                        "response": "Döküman sistemi başlatılamadı.",
                        "image_path": image_path  # Still return image if we found one
                    })

            try:
                self.qa_chain = create_qa_chain(self.retriever, model_name)
                result = answer_query(user_message, self.retriever, self.qa_chain, model_name)

                relevance_score = result.get("relevance_score", 0.0)
                answer = result.get("answer", "Yanıt alınamadı.")
                confidence = result.get("confidence", 0.0)
                used_model = result.get("model", model_name)
                sources = result.get("sources", [])

                # Grafik verilerini al (varsa)
                graph_data = result.get("graph_data", None)
                graph_type = result.get("graph_type", None)

                # If we found an image in answer_query that hasn't been found here, use it
                if image_path is None and "image_path" in result:
                    image_path = result["image_path"]

                if relevance_score < 0.2:
                    return jsonify({
                        "response": "Bu soruyla ilgili belgelerde yeterli bilgi bulunamadı.",
                        "model": used_model,
                        "image_path": image_path  # Still return image if we found one
                    })

                # Format sources for display in UI
                formatted_sources = []
                for source in sources:
                    file_name = source.get('file_name', 'Bilinmeyen')
                    page = source.get('page', 'Bilinmeyen Sayfa')
                    content_type = source.get('content_type', '')
                    relevance = source.get('relevance', 0.0)

                    if relevance > 0.4:  # Only include relevant sources
                        source_text = f"{file_name} (Sayfa {page})"
                        if content_type == 'ocr_text':
                            source_text += " [OCR]"

                        formatted_sources.append({
                            "text": source_text,
                            "file": file_name,
                            "page": page,
                            "relevance": relevance
                        })

                # Create HTML for source links
                source_html = ""
                if formatted_sources:
                    source_html = "<div class='document-sources mt-3'><h5>Kaynaklar:</h5><ul>"
                    for src in formatted_sources:
                        source_html += f"<li><a href='#' class='source-link' data-file='{src['file']}' data-page='{src['page']}'>{src['text']}</a></li>"
                    source_html += "</ul></div>"

                # Append source information to response
                final_response = answer
                if source_html:
                    final_response += f"\n\n{source_html}"

                response_data = {
                    "response": final_response,
                    "model": used_model,
                    "relevance_score": relevance_score,
                    "confidence": confidence,
                    "sources": formatted_sources,
                    "image_path": image_path  # Include image path in response
                }

                # Eğer grafik verileri varsa, yanıta ekle
                if graph_data and graph_type:
                    response_data["graph_data"] = graph_data
                    response_data["graph_type"] = graph_type

                return jsonify(response_data)

            except Exception as e:
                logging.error(f"❌ Soru işlenirken hata: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "response": "Soru cevaplanırken bir hata oluştu. Lütfen tekrar deneyin.",
                    "image_path": image_path  # Still return image if we found one
                })

    def run(self, debug=False, host='0.0.0.0', port=5000):
        """Flask uygulamasını çalıştırır"""
        try:
            self.app.run(debug=debug, host=host, port=port)
        finally:
            self.cleanup()

    def cleanup(self):
        """Uygulama kapanırken kaynakları temizler"""
        if hasattr(self, 'agent'):
            self.agent.close()
        if hasattr(self, 'user_db'):
            self.user_db.close()
        if hasattr(self, 'auth_db'):
            self.auth_db.close()