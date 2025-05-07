from langchain.tools import Tool
from AGENT.HR_DB.hr_tools import HRTools
from config import Config
import re


class ToolFactory:
    """Langchain için araçları oluşturan fabrika sınıfı"""

    def __init__(self):
        """ToolFactory sınıfını başlatır"""
        self.hr_tools = HRTools(Config.DB_HOST, Config.DB_NAME, Config.DB_PORT)


    def check_permission(self, user_id, function_name):
        """Kullanıcının yetkisini kontrol eder"""
        return self.hr_tools.db.has_permission(user_id, function_name)

    def get_employees_tool(self, user_id):
        """Veritabanındaki tüm çalışanları getirir"""
        print(f"✅ get_employees_tool çağrıldı. Kullanıcı ID: {user_id}")  # Debugging için ekledik
        try:
            return self.hr_tools.get_employees(user_id)
        except Exception as e:
            return f"Hata: Çalışanları getirirken bir sorun oluştu. Hata: {str(e)}"

    def update_salary_tool(self, input_text, user_id=None):
        """Çalışanın maaşını günceller (Yetki kontrolü ile)"""
        print(f"✅ update_salary_tool çağrıldı. Kullanıcı ID: {user_id}, Güncellenecek Bilgi: {input_text}")

        try:
            # user_id boşsa, sistemden al (örneğin bir oturumdan)
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            # Yetki kontrolü
            if not self.check_permission(user_id, "update_salary"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            # Girdinin formatına göre ayrıştırma yap
            input_text = input_text.strip()

            if "," in input_text:
                parts = [p.strip() for p in input_text.split(",")]
            else:
                parts = input_text.split()

            # En az 3 parça olmalı: Ad, Soyad, Yeni Maaş (Departman isteğe bağlı)
            if len(parts) < 3:
                return {"status": "error",
                        "message": "Giriş formatı hatalı! Beklenen format: 'Ad Soyad YeniMaaş' veya 'Ad, Soyad, YeniMaaş, Departman'"}

            # İlk iki eleman ad ve soyad, ortadaki maaş, eğer varsa sonuncusu departman
            first_name = parts[0]
            last_name = parts[1]
            department = parts[3] if len(parts) > 3 else None  # Eğer departman verilmişse al, yoksa None

            # Maaş bilgisini al
            salary_parts = parts[2:3]  # Maaş üçüncü eleman
            new_salary = "".join(salary_parts)  # Maaş sayısal olmalı

            # Maaşın gerçekten bir sayı olup olmadığını kontrol et
            if not new_salary.isdigit():
                return {"status": "error", "message": "Maaş yalnızca sayısal bir değer olmalıdır!"}

            new_salary = int(new_salary)  # Maaşı integer'a çevir

            # Eğer departman belirtilmemişse, çalışanın departmanını al
            if department is None:
                employees = self.hr_tools.get_employee_by_name(first_name, last_name)
                if not employees:
                    return {"status": "error", "message": "❌ Bu isimde bir çalışan bulunamadı!"}
                if len(employees) > 1:
                    return {"status": "error",
                            "message": f"⚠️ '{first_name} {last_name}' için birden fazla çalışan bulundu! Lütfen departman belirtin."}
                department = employees[0]["department"]

            print(
                f"➡️ Ayrıştırıldı: first_name={first_name}, last_name={last_name}, new_salary={new_salary}, department={department}")

            # Maaşı güncelle
            result = self.hr_tools.update_salary(user_id, first_name, last_name, new_salary, department)
            return {"status": "success", "message": "✅ Maaş başarıyla güncellendi."} if result else {
                "status": "error", "message": "❌ Maaş güncellenemedi."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}


    def get_employees_by_department_tool(self, input_text, user_id=None):
        """Belirli bir departmandaki çalışanları getirir"""
        print(f"✅ get_employees_by_department_tool çağrıldı. Kullanıcı ID: {user_id}, Girdi: {input_text}")

        try:
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            if not self.check_permission(user_id, "get_employees_by_department"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            department = input_text.strip()
            result = self.hr_tools.get_employees_by_department(user_id, department)

            return {"status": "success", "data": result} if result else {
                "status": "error", "message": "❌ Bu departmanda çalışan bulunamadı."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def add_employee_tool(self, input_text, user_id=None):
        """Yeni bir çalışan ekler (Yetki kontrolü ile, rol ataması dahil)"""
        print(f"✅ add_employee_tool çağrıldı. Kullanıcı ID: {user_id}, Çalışan Bilgisi: {input_text}")

        try:
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            if not self.check_permission(user_id, "add_employee"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            input_text = input_text.strip()
            parts = [p.strip() for p in input_text.split(",")] if "," in input_text else input_text.split()

            # 5 parça bekleniyor: Ad, Soyad, Maaş, Departman, Rol
            if len(parts) != 5:
                return {"status": "error",
                        "message": "Giriş formatı hatalı! Beklenen format: 'Ad, Soyad, Maaş, Departman, Rol'"}

            first_name, last_name, salary_text, department, role_name = parts

            if not salary_text.isdigit():
                return {"status": "error", "message": "Maaş yalnızca sayısal bir değer olmalıdır!"}
            salary = int(salary_text)

            print(
                f"➡️ Ayrıştırıldı: first_name={first_name}, last_name={last_name}, salary={salary}, department={department}, role={role_name}")

            result = self.hr_tools.add_employee(user_id, first_name, last_name, salary, department, role_name)
            return {"status": "success",
                    "message": "✅ Çalışan başarıyla eklendi. (Varsayılan şifre: 123456)"} if result else {
                "status": "error", "message": "❌ Çalışan eklenemedi."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}


    def delete_employee_tool(self, input_text, user_id=None):
        """Gelen veriyi parse edip SQL'den çalışanı siler (Yetki kontrolü ile)"""
        print(f"✅ delete_employee_tool çağrıldı. Kullanıcı ID: {user_id}, Silinecek Çalışan: {input_text}")

        try:
            # user_id boşsa, sistemden al (örneğin bir oturumdan)
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            # Yetki kontrolü
            if not self.check_permission(user_id, "delete_employee"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            # Girdiyi temizle
            input_text = input_text.strip()

            # Giriş formatına göre ayrıştır
            parts = [p.strip() for p in input_text.split(",")] if "," in input_text else input_text.split()

            # En az 2 parça olmalı (Ad, Soyad)
            if len(parts) < 2:
                return {"status": "error",
                        "message": "Giriş formatı hatalı! Beklenen format: 'Ad Soyad' veya 'Ad, Soyad, Departman'"}

            # Ad ve soyadı al
            first_name = parts[0]
            last_name = parts[1]
            department = parts[2] if len(parts) > 2 else None  # Eğer departman verilmişse al, yoksa None

            print(f"➡️ Ayrıştırıldı: first_name={first_name}, last_name={last_name}, department={department}")

            # Eğer departman verilmişse direkt silme işlemini yap
            if department:
                result = self.hr_tools.delete_employee(user_id, first_name, last_name, department)
                return {"status": "success", "message": "✅ Çalışan başarıyla silindi."} if result else {
                    "status": "error", "message": "❌ Çalışan silinemedi."
                }

            # Eğer departman bilgisi verilmemişse, çalışanın hangi departmanda olduğunu öğren
            employees = self.hr_tools.get_employee_by_name(first_name, last_name)  # Ad ve soyadı ile arama yap

            # Eğer hiç eşleşme yoksa
            if not employees:
                return {"status": "error", "message": "❌ Bu isimde bir çalışan bulunamadı!"}

            # Eğer birden fazla çalışan varsa hata ver
            if len(employees) > 1:
                return {"status": "error",
                        "message": f"⚠️ '{first_name} {last_name}' için birden fazla çalışan bulundu! Lütfen departman belirtin."}

            # Eğer sadece bir çalışan varsa, onun departmanını al ve sil
            department = employees[0]["department"]
            result = self.hr_tools.delete_employee(user_id, first_name, last_name, department)

            return {"status": "success", "message": "✅ Çalışan başarıyla silindi."} if result else {
                "status": "error", "message": "❌ Çalışan silinemedi."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def get_current_user_id(self):
        """Oturum açmış olan kullanıcı kimliğini döndürür"""
        try:
            # Burada oturumdan kullanıcı kimliği alınabilir (Flask, FastAPI vb. sistemlerden)
            from flask import session
            return session.get("user_id")
        except:
            return None

    def get_highest_paid_employee_tool(self, user_id):
        """En yüksek maaşlı çalışanı getirir (Yetki kontrolü ile)"""
        if not self.check_permission(user_id, "get_highest_paid_employee"):
            return "❌ Yetkisiz erişim!"
        return self.hr_tools.get_highest_paid_employee(user_id)

    def get_lowest_paid_employee_tool(self, user_id):
        """En düşük maaşlı çalışanı getirir"""
        print(f"✅ get_lowest_paid_employee_tool çağrıldı. Kullanıcı ID: {user_id}")
        try:
            return self.hr_tools.get_lowest_paid_employee(user_id)
        except Exception as e:
            return f"Hata: En düşük maaşlı çalışan getirilirken bir sorun oluştu. Hata: {str(e)}"

    def get_average_salary_tool(self, user_id):
        """Şirketteki ortalama maaşı hesaplar"""
        print(f"✅ get_average_salary_tool çağrıldı. Kullanıcı ID: {user_id}")
        try:
            return self.hr_tools.get_average_salary(user_id)
        except Exception as e:
            return f"Hata: Ortalama maaş hesaplanırken bir sorun oluştu. Hata: {str(e)}"

    def get_total_salary_by_department_tool(self, user_id):
        """Her departmandaki toplam maaşı getirir (Yetki kontrolü ile)"""
        if not self.check_permission(user_id, "get_total_salary_by_department"):
            return "❌ Yetkisiz erişim!"
        return self.hr_tools.get_total_salary_by_department(user_id)

    def get_department_with_most_employees_tool(self, user_id):
        """En fazla çalışana sahip departmanı getirir"""
        print(f"✅ get_department_with_most_employees_tool çağrıldı. Kullanıcı ID: {user_id}")
        try:
            return self.hr_tools.get_department_with_most_employees(user_id)
        except Exception as e:
            return f"Hata: En fazla çalışana sahip departman getirilirken bir sorun oluştu. Hata: {str(e)}"

    def get_employee_count_by_department_tool(self, user_id=None):
        """Her departmandaki çalışan sayısını getirir"""
        print(f"✅ get_employee_count_by_department_tool çağrıldı. Kullanıcı ID: {user_id}")

        try:
            # user_id boşsa, sistemden al (örneğin bir oturumdan)
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            # Yetki kontrolü
            if not self.check_permission(user_id, "get_employee_count_by_department"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            # Veriyi getir
            department_counts = self.hr_tools.get_employee_count_by_department(user_id)

            return {"status": "success", "data": department_counts} if department_counts else {
                "status": "error", "message": "❌ Departman bilgisi alınamadı."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def get_user_data_tool(self, user_id=None):
        """Sadece giriş yapan kullanıcının verilerini getirir"""
        print(f"✅ get_user_data_tool çağrıldı. Kullanıcı ID: {user_id}")

        try:
            # user_id boşsa, sistemden al (örneğin bir oturumdan)
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            # Kullanıcı verilerini getir
            user_data = self.hr_tools.get_user_data(user_id)

            return {"status": "success", "data": user_data} if user_data else {
                "status": "error", "message": "❌ Kullanıcı verisi alınamadı."
            }

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def increase_all_salaries_tool(self, input_text, user_id=None):
        """Tüm çalışanların maaşlarına yüzde oranında zam yapar"""
        print(f"✅ increase_all_salaries_tool çağrıldı. Kullanıcı ID: {user_id}, Girdi: {input_text}")

        try:
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            if not self.check_permission(user_id, "increase_all_salaries"):
                return {"status": "error", "message": "❌ Yetkisiz erişim!"}

            # % işareti varsa temizle ve sayıyı al
            match = re.search(r"(\d+)", input_text)
            if not match:
                return {"status": "error", "message": "Lütfen geçerli bir yüzde oranı belirtin!"}

            percentage = float(match.group(1))

            result = self.hr_tools.increase_all_salaries(user_id, percentage)

            return {"status": "success",
                    "message": f"✅ Tüm maaşlara %{percentage} zam yapıldı. Etkilenen kişi sayısı: {result}"} \
                if result else {"status": "error", "message": "❌ Maaşlar güncellenemedi."}

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def change_password_tool(self, input_text, user_id=None):
        """Kullanıcının kendi şifresini değiştirmesini sağlar"""
        print(f"✅ change_password_tool çağrıldı. Kullanıcı ID: {user_id}, Girdi: {input_text}")

        try:
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    return {"status": "error", "message": "Kullanıcı kimliği alınamadı."}

            parts = [p.strip() for p in input_text.split(",")]
            if len(parts) != 2:
                return {"status": "error", "message": "Beklenen format: 'EskiŞifre, YeniŞifre'"}

            old_password, new_password = parts
            result = self.hr_tools.change_password(user_id, old_password, new_password)

            return result

        except Exception as e:
            import traceback
            print(f"Hata: {str(e)}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Hata oluştu: {str(e)}"}

    def create_tools(self):
        """LangChain için tüm araçları oluşturur ve döndürür"""
        return [
            Tool(
                name="Get Employees",
                func=lambda user_id: self.get_employees_tool(user_id),
                description="Veritabanındaki tüm çalışanları listeler. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Add Employee",
                func=lambda input_text: self.add_employee_tool(input_text),
                description="Yeni bir çalışan ekler. Kullanıcı yetkisini kontrol eder. "
                            "Beklenen format: 'Ad, Soyad, Maaş, Departman, Rol' (Şifre varsayılan olarak 123456 atanır.)"
            ),
            Tool(
                name="Update Salary",
                func=lambda input_text: self.update_salary_tool(input_text),
                description="Çalışanın maaşını günceller. Kullanıcı yetkisini kontrol eder. "
                            "Beklenen format: 'Ad Soyad YeniMaaş' veya 'Ad, Soyad, YeniMaaş, Departman'"
            ),
            Tool(
                name="Delete Employee",
                func=lambda input_text: self.delete_employee_tool(input_text),
                description="Çalışanı siler. Kullanıcı yetkisini kontrol eder. "
                            "Beklenen format: 'Ad, Soyad, Departman'"
            ),
            Tool(
                name="Get Highest Paid Employee",
                func=lambda user_id: self.get_highest_paid_employee_tool(user_id),
                description="En yüksek maaşlı çalışanı getirir. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get Lowest Paid Employee",
                func=lambda user_id: self.get_lowest_paid_employee_tool(user_id),
                description="En düşük maaşlı çalışanı getirir. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get Average Salary",
                func=lambda user_id: self.get_average_salary_tool(user_id),
                description="Şirketteki ortalama maaşı hesaplar. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get Total Salary By Department",
                func=lambda user_id: self.get_total_salary_by_department_tool(user_id),
                description="Her departmandaki toplam maaşı getirir. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get Department With Most Employees",
                func=lambda user_id: self.get_department_with_most_employees_tool(user_id),
                description="En fazla çalışana sahip departmanı getirir. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get Employee Count By Department",
                func=lambda user_id: self.get_employee_count_by_department_tool(user_id),
                description="Her departmandaki çalışan sayısını getirir. Kullanıcı yetkisini kontrol eder."
            ),
            Tool(
                name="Get User Data",
                func=lambda user_id: self.get_user_data_tool(user_id),
                description="Sadece giriş yapan kullanıcının verilerini getirir. Kullanıcı kimliğini gerektirir."
            ),
            Tool(
                name="Increase All Salaries",
                func=lambda input_text: self.increase_all_salaries_tool(input_text),
                description="Tüm çalışanların maaşlarına belirtilen oranda zam yapar. "
            ),
            Tool(
                name="Get Employees By Department",
                func=lambda input_text: self.get_employees_by_department_tool(input_text),
                description="Belirli bir departmandaki çalışanları listeler. Girdi olarak departman adı beklenir. "
            ),
            Tool(
                name="Change Password",
                func=lambda input_text: self.change_password_tool(input_text),
                description="Kullanıcının kendi şifresini değiştirmesini sağlar. "
                            "Beklenen format: 'EskiŞifre, YeniŞifre'"
            )

        ]

    def close(self):
        """Kaynakları serbest bırakır"""
        if hasattr(self, 'hr_tools'):
            self.hr_tools.close()