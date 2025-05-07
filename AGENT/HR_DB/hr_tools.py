from AGENT.HR_DB.database import HRDatabase
from config import Config


class HRTools:
    """İnsan Kaynakları (HR) araçları sınıfı"""

    def __init__(self, host=None, database=None, port=None) -> None:
        """HR Araçları sınıfını başlatır ve veritabanı bağlantısını oluşturur"""
        self.host = host or Config.DB_HOST
        self.database = database or Config.DB_NAME
        self.port = port or Config.DB_PORT
        self.db = HRDatabase(self.host, self.database, port=self.port)

    def get_employees(self, user_id):
        """Çalışan listesini getirir"""
        return self.db.get_employees(user_id)

    def get_employees_raw(self, user_id):
        return self.db.get_employees_raw(user_id)

    def add_employee(self, user_id, first_name: str, last_name: str, salary: int, department: str, role_name: str):
        """Yeni çalışan ekler, varsayılan şifre ile (123456)"""
        return self.db.add_employee(user_id, first_name, last_name, salary, department, role_name)

    def update_salary(self, user_id, first_name: str, last_name: str, new_salary: int, department: str):
        """Çalışanın maaşını günceller"""
        return self.db.update_salary(user_id, first_name, last_name, new_salary, department)

    def delete_employee(self, user_id, first_name: str, last_name: str, department: str):
        """
        Çalışanı employees, users ve user_roles tablolarından tamamen siler
        """
        return self.db.delete_employee(user_id, first_name, last_name, department)

    def get_employees_by_department(self, user_id, department: str):
        """Belirli bir departmandaki çalışanları getirir"""
        return self.db.get_employees_by_department(user_id, department)

    def get_highest_paid_employee(self, user_id):
        """En yüksek maaşlı çalışanı getirir"""
        return self.db.get_highest_paid_employee(user_id)

    def get_lowest_paid_employee(self, user_id):
        """En düşük maaşlı çalışanı getirir"""
        return self.db.get_lowest_paid_employee(user_id)

    def get_average_salary(self, user_id):
        """Şirketteki ortalama maaşı hesaplar"""
        return self.db.get_average_salary(user_id)

    def get_employee_count_by_department(self, user_id):
        """Her departmandaki çalışan sayısını getirir"""
        return self.db.get_employee_count_by_department(user_id)

    def get_total_salary_by_department(self, user_id):
        """Her departmandaki toplam maaşı getirir"""
        return self.db.get_total_salary_by_department(user_id)

    def get_employee_by_name(self, first_name, last_name):
        """Ad ve soyada göre çalışan(lar)ı getirir"""
        return self.db.get_employee_by_name(first_name, last_name)

    def get_department_with_most_employees(self, user_id):
        """En fazla çalışana sahip departmanı getirir"""
        return self.db.get_department_with_most_employees(user_id)

    def get_user_data(self, user_id):
        """Sadece giriş yapan kullanıcının verilerini getirir"""
        return self.db.get_user_data(user_id)

    def increase_all_salaries(self, user_id, percentage: float):
        """Tüm çalışanların maaşlarını belirtilen yüzde oranında artırır"""
        return self.db.increase_all_salaries(user_id, percentage)

    def change_password(self, user_id, old_password: str, new_password: str):
        """Kullanıcının kendi şifresini değiştirmesini sağlar"""
        return self.db.change_password(user_id, old_password, new_password)

    def close(self):
        """Kaynakları serbest bırakır"""
        self.db.close()