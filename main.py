# main.py
from app import FlaskApp
import os


import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='langchain_google_genai.chat_models')
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Uygulamanın ana giriş noktası"""


    for k in ["DB_HOST", "DB_NAME", "DB_USERNAME", "DB_PASSWORD"]:
        value = os.environ.get(k)
        try:
            value.encode("utf-8").decode("utf-8")
        except UnicodeDecodeError as e:
            print(f"HATA! {k} değişkeninde sorun var: {e}")

    print(">>> main başladı")
    try:
        app = FlaskApp()
        logging.info("Flask uygulaması başlatıldı")
        app.run(debug=False)
    except Exception as e:
        logging.error(f"Hata oluştu: {str(e)}")



if __name__ == '__main__':
    main()

'''
def main():
    """Uygulamanın ana giriş noktası"""
    logger = Logger()
    logger.info("Uygulama başlatıldı")
    try:
        app = FlaskApp()
        app.run(debug=True)
        pass
    except Exception as e:
            logger.error(f"Hata oluştu: {str(e)}", exc_info=True)

    app = FlaskApp()
    app.run(debug=True)

if __name__ == '__main__':
    main()
'''