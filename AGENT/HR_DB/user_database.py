import hashlib
import psycopg2
from config import Config


class UserDatabase:
    """Kullanıcı veritabanı işlemleri sınıfı"""

    def __init__(self, host=None, database=None, username=None, password=None, port=None) -> None:
        """Veritabanı bağlantısını başlatır."""
        self.host = host or Config.DB_HOST
        self.database = database or Config.DB_NAME
        self.username = username or Config.DB_USERNAME
        self.password = password or Config.DB_PASSWORD
        self.port = port or Config.DB_PORT

        self.connection = None
        self._connect()
        self._create_users_table_if_not_exists()
        self._create_auth_tables_if_not_exists()

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
            print("Veritabanı bağlantısı başarılı.")
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {str(e)}")
            raise

    def _create_users_table_if_not_exists(self):
        """Kullanıcılar tablosu yoksa oluşturur"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(128) NOT NULL,
                    fullname VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    salary INTEGER NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.connection.commit()
        except Exception as e:
            print(f"Kullanıcılar tablosu oluşturulurken hata: {str(e)}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _create_auth_tables_if_not_exists(self):
        """Rol ve fonksiyon tablolarını oluşturur (eğer yoksa)."""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS functions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255) NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_functions (
                    role_id INTEGER NOT NULL,
                    function_id INTEGER NOT NULL,
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
                    PRIMARY KEY (role_id, function_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                    PRIMARY KEY (user_id, role_id)
                )
            """)

            self.connection.commit()
        except Exception as e:
            print(f"Yetkilendirme tabloları oluşturulurken hata: {str(e)}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _hash_password(self, password):
        """Şifreyi güvenli şekilde hashler"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password, fullname, email, salary, department):
        """Yeni kullanıcı kaydeder"""
        hashed_password = self._hash_password(password)

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password, fullname, email, salary, department) 
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (username, hashed_password, fullname, email, salary, department))
            result = cursor.fetchone()
            self.connection.commit()
            return result is not None
        except psycopg2.errors.UniqueViolation:
            self.connection.rollback()
            return False
        except Exception as e:
            print(f"Kullanıcı kaydı hatası: {str(e)}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def authenticate_user(self, username, password):
        """Kullanıcı kimlik doğrulaması yapar"""
        hashed_password = self._hash_password(password)  # _hash_password fonksiyonunu kullan (hexdigest döndürür)
        print(f"🔍 Python Tarafında Hashlenen Şifre: {hashed_password}")

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT id, username, fullname, email, salary, department
                FROM users 
                WHERE username = %s AND password = %s
            """, (username, hashed_password))

            user = cursor.fetchone()
            print(f"🔍 SQL sorgu sonucu: {user}")

            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'fullname': user[2],
                    'email': user[3],
                    'salary': user[4],
                    'department': user[5]
                }
            return None
        except Exception as e:
            print(f"❌ Kimlik doğrulama hatası: {str(e)}")
            return None
        finally:
            cursor.close()

    def user_exists(self, username=None, email=None):
        """Kullanıcı adı veya e-posta ile kullanıcının var olup olmadığını kontrol eder"""
        if not username and not email:
            return False

        cursor = self.connection.cursor()
        try:
            query = "SELECT COUNT(*) FROM users WHERE "
            params = []

            if username:
                query += "username = %s"
                params.append(username)

            if email:
                if username:
                    query += " OR "
                query += "email = %s"
                params.append(email)

            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"Kullanıcı kontrolü hatası: {str(e)}")
            return False
        finally:
            cursor.close()

    def assign_role_to_user(self, user_id, role_id):
        """Kullanıcıya bir rol atar."""
        query = "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)"
        rows_affected = self.execute_query(query, (user_id, role_id), fetch=False)
        return rows_affected > 0

    def get_user_roles(self, user_id):
        """Kullanıcının rollerini döndürür."""
        query = """
            SELECT r.id, r.name
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = %s
        """
        rows = self.execute_query(query, (user_id,))
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

    def update_password_hash(self, username, plain_password):
        """Kullanıcının şifresini yeni hash algoritmasıyla günceller"""
        hashed_password = self._hash_password(plain_password)

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                UPDATE users 
                SET password = %s 
                WHERE username = %s
            """, (hashed_password, username))

            self.connection.commit()
            rows_affected = cursor.rowcount

            if rows_affected > 0:
                print(f"✅ {username} kullanıcısının şifresi başarıyla güncellendi.")
                return True
            else:
                print(f"⚠️ {username} kullanıcısı bulunamadı veya şifre güncellenemedi.")
                return False
        except Exception as e:
            print(f"❌ Şifre güncelleme hatası: {str(e)}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def close(self):
        """Veritabanı bağlantısını kapatır"""
        if self.connection:
            self.connection.close()
            print("Veritabanı bağlantısı kapatıldı.")