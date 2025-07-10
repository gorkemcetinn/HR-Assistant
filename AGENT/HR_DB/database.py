import psycopg2
import hashlib
from datetime import datetime
from AGENT.SQL_Agent.table_utils import create_table  # Zaten başta eklediysen atla
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HRDatabase:
    """İnsan Kaynakları (HR) veritabanı işlemleri sınıfı"""

    def __init__(self, host=None, database=None, username=None, password=None, port=None) -> None:
        """Veritabanı bağlantısını başlatır"""
        self.host = host or Config.DB_HOST
        self.database = database or Config.DB_NAME
        self.username = username or Config.DB_USERNAME
        self.password = password or Config.DB_PASSWORD
        self.port = port or Config.DB_PORT

        self.connection = None
        self._connect()

    def _connect(self):
        """Veritabanına bağlantı oluşturur"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.username,
                password=self.password,
                port=self.port
            )
            logging.info("✅ Veritabanı bağlantısı başarılı.")
        except Exception as e:
            logging.error(f"❌ Veritabanı bağlantı hatası: {str(e)}")
            raise

    def get_employees_raw(self, user_id):
        """Çalışan listesini ham veri olarak döndürür (agent değil, frontend kullanır)"""
        if not self.has_permission(user_id, "get_employees"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT * FROM users"
        rows = self.execute_query(query)
        return [tuple(row) for row in rows]

    def execute_query(self, query, params=None, fetch=True):
        """SQL sorgusunu çalıştırır ve sonuçları döndürür"""
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch:
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()

    def has_permission(self, user_id, function_name):
        """Kullanıcının belirli bir fonksiyonu çalıştırma yetkisi olup olmadığını kontrol eder"""
        if not user_id:
            return False

        query = """
            SELECT 1 FROM role_functions rf
            JOIN functions f ON rf.function_id = f.id
            JOIN user_roles ur ON rf.role_id = ur.role_id
            WHERE ur.user_id = %s AND f.name = %s
        """
        result = self.execute_query(query, (user_id, function_name))

        # Yetkilendirme sorgusunu ekrana yazdıralım
        logging.info(f"🔍 Kullanıcı ID: {user_id}, Fonksiyon: {function_name}, Yetki Sonucu: {result}")

        return len(result) > 0

    def get_employees(self, user_id):
        """Çalışan listesini getirir"""
        if not self.has_permission(user_id, "get_employees"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT * FROM users"
        rows = self.execute_query(query)
        return create_table(rows) if rows else "❌ Kayıt bulunamadı."

    def add_employee(self, user_id, first_name, last_name, salary, department, role_name):
        """Yeni çalışan ekler, users tablosuna ekler ve role atar"""
        if not self.has_permission(user_id, "add_employee"):
            return "❌ Yetkisiz erişim!"

        # Varsayılan şifre
        password = "123456"

        # Şifreyi hashle
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # fullname, username, email, created_at oluştur
        fullname = f"{first_name} {last_name}"
        username = f"{first_name.lower()}.{last_name.lower()}"
        email = f"{username}@example.com"
        created_at = datetime.now()

        # Kullanıcı zaten var mı kontrol et
        query_check = "SELECT id FROM users WHERE email = %s"
        existing_user = self.execute_query(query_check, (email,))
        if existing_user:
            logging.info(f"⚠️ Kullanıcı zaten kayıtlı: {email}")
            return False

        # users tablosuna ekle ve eklenen satırın ID'sini döndür (PostgreSQL RETURNING özelliği)
        query_user = """
            INSERT INTO users (fullname, username, email, password, salary, department, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(query_user,
                                    (fullname, username, email, hashed_password, salary, department, created_at))

        # Eklenen kullanıcının ID'sini al
        if not result:
            logging.error("❌ Yeni kullanıcı eklenirken hata oluştu.")
            return False

        new_user_id = result[0][0]

        # role_id al
        query_role = "SELECT id FROM roles WHERE name = %s"
        role_result = self.execute_query(query_role, (role_name,))
        if not role_result:
            logging.error(f"❌ Rol bulunamadı: {role_name}")
            return False
        role_id = role_result[0][0]

        # user_roles tablosuna ekle
        query_user_role = "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)"
        self.execute_query(query_user_role, (new_user_id, role_id), fetch=False)

        return True

    def update_salary(self, user_id, first_name, last_name, new_salary, department):
        """Çalışanın maaşını günceller (users tablosu üzerinden)"""
        if not self.has_permission(user_id, "update_salary"):
            return "❌ Yetkisiz erişim!"

        fullname = f"{first_name} {last_name}"

        query = """
            UPDATE users
            SET salary = %s
            WHERE fullname = %s AND department = %s
        """
        rows_affected = self.execute_query(query, (new_salary, fullname, department), fetch=False)

        logging.info(f"🔍 Güncellenen Satır: {rows_affected}")
        return rows_affected

    def delete_employee(self, user_id, first_name, last_name, department):
        """Çalışanı users ve user_roles tablolarından tamamen siler"""
        if not self.has_permission(user_id, "delete_employee"):
            return "❌ Yetkisiz erişim!"

        try:
            fullname = f"{first_name} {last_name}"

            # 1. users tablosundan user_id'yi al
            query_get_user = """
                SELECT id FROM users 
                WHERE fullname = %s AND department = %s
            """
            user_result = self.execute_query(query_get_user, (fullname, department))
            if not user_result:
                logging.error("❌ Çalışan bulunamadı.")
                return 0

            target_user_id = user_result[0][0]

            # 2. user_roles tablosundan sil
            self.execute_query("DELETE FROM user_roles WHERE user_id = %s", (target_user_id,), fetch=False)

            # 3. users tablosundan sil
            rows_affected = self.execute_query("DELETE FROM users WHERE id = %s", (target_user_id,), fetch=False)

            return rows_affected

        except Exception as e:
            logging.error(f"❌ Silme işlemi sırasında hata: {str(e)}")
            return 0

    def get_employees_by_department(self, user_id, department):
        """Belirli bir departmandaki çalışanları getirir"""
        if not self.has_permission(user_id, "get_employees_by_department"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT * FROM users WHERE department = %s"
        rows = self.execute_query(query, (department,))
        return create_table(rows) if rows else "❌ Bu departmanda çalışan bulunamadı."

    def get_highest_paid_employee(self, user_id):
        if not self.has_permission(user_id, "get_highest_paid_employee"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT * FROM users ORDER BY salary DESC LIMIT 1"
        rows = self.execute_query(query)
        return tuple(rows[0]) if rows else None

    def get_lowest_paid_employee(self, user_id):
        if not self.has_permission(user_id, "get_lowest_paid_employee"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT * FROM users ORDER BY salary ASC LIMIT 1"
        rows = self.execute_query(query)
        return tuple(rows[0]) if rows else None

    def increase_all_salaries(self, user_id, percentage):
        if not self.has_permission(user_id, "increase_all_salaries"):
            return "❌ Yetkisiz erişim!"
        try:
            query = "UPDATE users SET salary = salary + (salary * %s / 100)"
            rows_affected = self.execute_query(query, (percentage,), fetch=False)
            logging.info(f"✅ {rows_affected} çalışanın maaşı %{percentage} oranında artırıldı.")
            return rows_affected
        except Exception as e:
            logging.error(f"❌ Maaş artırma sırasında hata: {str(e)}")
            return 0

    def get_average_salary(self, user_id):
        if not self.has_permission(user_id, "get_average_salary"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT AVG(salary) AS average_salary FROM users"
        result = self.execute_query(query)
        return result[0][0] if result else 0

    def get_employee_by_name(self, first_name, last_name):
        fullname = f"{first_name} {last_name}"
        query = "SELECT id, fullname, salary, department FROM users WHERE fullname = %s"
        rows = self.execute_query(query, (fullname,))
        column_names = ['id', 'fullname', 'salary', 'department']
        return [dict(zip(column_names, row)) for row in rows] if rows else []

    def get_employee_count_by_department(self, user_id):
        if not self.has_permission(user_id, "get_employee_count_by_department"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT department, COUNT(*) AS employee_count FROM users GROUP BY department ORDER BY employee_count DESC"
        rows = self.execute_query(query)
        return [(row[0], row[1]) for row in rows]

    def get_total_salary_by_department(self, user_id):
        if not self.has_permission(user_id, "get_total_salary_by_department"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT department, SUM(salary) AS total_salary FROM users GROUP BY department ORDER BY total_salary DESC"
        rows = self.execute_query(query)
        return [(row[0], row[1]) for row in rows]

    def get_department_with_most_employees(self, user_id):
        if not self.has_permission(user_id, "get_department_with_most_employees"):
            return "❌ Yetkisiz erişim!"
        query = "SELECT department, COUNT(*) AS employee_count FROM users GROUP BY department ORDER BY employee_count DESC LIMIT 1"
        rows = self.execute_query(query)
        return rows[0] if rows and rows[0][1] > 0 else "⚠️ Departman bilgisi bulunamadı."

    def get_user_data(self, user_id):
        if not user_id:
            return "❌ Kullanıcı kimliği gereklidir!"
        query = "SELECT * FROM users WHERE id = %s"
        rows = self.execute_query(query, (user_id,))
        return tuple(rows[0]) if rows else "❌ Kullanıcı bulunamadı!"

    def change_password(self, user_id, old_password, new_password):
        """Kendi şifresini değiştirir"""
        try:
            # 1. Eski şifre hash'le
            hashed_old_password = hashlib.sha256(old_password.encode()).hexdigest()

            # 2. Mevcut şifreyi al
            query = "SELECT password FROM users WHERE id = %s"
            result = self.execute_query(query, (user_id,))

            if not result or result[0][0] != hashed_old_password:
                return {"status": "error", "message": "❌ Eski şifre yanlış veya kullanıcı bulunamadı."}

            # 3. Yeni şifreyi hash'le
            hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()

            # 4. Şifreyi güncelle
            update_query = "UPDATE users SET password = %s WHERE id = %s"
            rows_affected = self.execute_query(update_query, (hashed_new_password, user_id), fetch=False)

            return {"status": "success", "message": "✅ Şifre başarıyla güncellendi."} if rows_affected > 0 else {
                "status": "error", "message": "❌ Şifre güncellenirken hata oluştu."
            }

        except Exception as e:
            return {"status": "error", "message": f"Hata: {str(e)}"}

    def close(self):
        """Veritabanı bağlantısını kapatır"""
        if self.connection:
            self.connection.close()
            logging.info("🔴 Veritabanı bağlantısı kapatıldı.")
