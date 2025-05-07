# logging_helper.py (yeni dosya)
import logging
import sys
import os
from datetime import datetime


class Logger:
    """Uygulama için loglama yardımcısı"""

    def __init__(self, log_level=logging.INFO):
        """Logger sınıfını başlatır"""
        self.logger = logging.getLogger("hr_app")
        self.logger.setLevel(log_level)

        # Log dosyası için dizin oluştur
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Log dosyası adı
        log_file = os.path.join(log_dir, f"hr_app_{datetime.now().strftime('%Y%m%d')}.log")

        # Konsola loglama
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)

        # Dosyaya loglama
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

    def info(self, message):
        """Bilgi mesajı loglar"""
        self.logger.info(message)

    def warning(self, message):
        """Uyarı mesajı loglar"""
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        """Hata mesajı loglar"""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=True):
        """Kritik hata mesajı loglar"""
        self.logger.critical(message, exc_info=exc_info)

# Örnek kullanım
# from logging_helper import Logger
# logger = Logger()
# logger.info("Uygulama başlatıldı")
# try:
#     # Bir işlem...
#     pass
# except Exception as e:
#     logger.error(f"Hata oluştu: {str(e)}", exc_info=True)