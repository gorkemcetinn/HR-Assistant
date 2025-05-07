from config import Config
import psycopg2

class AuthDatabase:
    """Rol ve fonksiyon yönetimi için veritabanı işlemleri."""

    def __init__(self, host=None, database=None, username=None, password=None, port=None):
        """Veritabanı bağlantısını başlatır."""
        self.host = host or Config.DB_HOST
        self.database = database or Config.DB_NAME
        self.username = username or Config.DB_USERNAME
        self.password = password or Config.DB_PASSWORD
        self.port = port or Config.DB_PORT

        self.connection = None
        self._connect()

    def _connect(self):
        """Veritabanına bağlantı oluşturur."""
        try:
            self.connection = psycopg2.connect(
        host=Config.DB_HOST,
        database=Config.DB_NAME,
        user=Config.DB_USERNAME,
        password=Config.DB_PASSWORD,
        port=Config.DB_PORT
            )
            print("✅ Bağlantı başarılı!")
        except Exception as e:
            print("❌ Bağlantı hatası:", e)

    def execute_query(self, query, params=None, fetch=True):
        """SQL sorgusunu çalıştırır ve sonuçları döndürür."""
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

    def add_role(self, role_name):
        """Yeni bir rol ekler."""
        query = "INSERT INTO roles (name) VALUES (%s) RETURNING id"
        result = self.execute_query(query, (role_name,))
        return result is not None and len(result) > 0

    def add_function(self, name, description=None):
        """Yeni bir fonksiyon ekler."""
        query = "INSERT INTO functions (name, description) VALUES (%s, %s) RETURNING id"
        result = self.execute_query(query, (name, description))
        return result is not None and len(result) > 0

    def assign_function_to_role(self, role_id, function_id):
        """Bir fonksiyonu belirli bir role atar."""
        query = "INSERT INTO role_functions (role_id, function_id) VALUES (%s, %s)"
        rows_affected = self.execute_query(query, (role_id, function_id), fetch=False)
        return rows_affected > 0

    def assign_role_to_user(self, user_id, role_id):
        """Kullanıcıya bir rol atar."""
        query = "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)"
        rows_affected = self.execute_query(query, (user_id, role_id), fetch=False)
        return rows_affected > 0

    def get_role_functions(self, role_id):
        """Belirli bir role atanmış fonksiyonları getirir."""
        query = """
            SELECT f.id, f.name, f.description
            FROM functions f
            JOIN role_functions rf ON f.id = rf.function_id
            WHERE rf.role_id = %s
        """
        rows = self.execute_query(query, (role_id,))
        return [tuple(row) for row in rows]

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

    def get_users_by_role(self, role_id):
        """Belirli bir role sahip kullanıcıları getirir."""
        query = """
            SELECT u.id, u.username, u.fullname, u.email, u.salary, u.department
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.role_id = %s
        """
        rows = self.execute_query(query, (role_id,))
        return [tuple(row) for row in rows]

    def get_all_roles(self):
        """Tüm rolleri getirir."""
        query = "SELECT * FROM roles"
        rows = self.execute_query(query)
        return [tuple(row) for row in rows]

    def get_all_functions(self):
        """Tüm fonksiyonları getirir."""
        query = "SELECT * FROM functions"
        rows = self.execute_query(query)
        return [tuple(row) for row in rows]

    def get_users_with_roles(self):
        """Tüm kullanıcıları ve sahip oldukları rolleri getirir."""
        query = """
            SELECT u.id, u.username, u.fullname, u.email, u.salary, u.department, r.name as role
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
        """
        rows = self.execute_query(query)
        return [tuple(row) for row in rows]

    def get_role_users_and_functions(self, role_id):
        """Belirli bir role sahip kullanıcıları ve o role atanmış fonksiyonları getirir."""
        query_users = """
            SELECT u.id, u.username, u.fullname, u.email, u.salary, u.department
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.role_id = %s
        """
        users = self.execute_query(query_users, (role_id,))

        query_functions = """
            SELECT f.id, f.name, f.description
            FROM functions f
            JOIN role_functions rf ON f.id = rf.function_id
            WHERE rf.role_id = %s
        """
        functions = self.execute_query(query_functions, (role_id,))

        return {
            "users": [tuple(user) for user in users],
            "functions": [tuple(func) for func in functions]
        }

    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.connection:
            self.connection.close()
            print("Auth veritabanı bağlantısı kapatıldı.")