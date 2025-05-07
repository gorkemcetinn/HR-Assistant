Bu proje yapay zeka araçlarını kullanarak yapılmıştır. Langchain framework'ünü kullanrak yapılmıştır. 
Bu proje içerisinde SQL Asistanı ve Döküman Asistanı olarak adlandırdığımız iki adet agent bulunmaktadır. 
SQL Asistanı verilen promptlara göre kod yazmadan database ve langchain tools olarak tanımladığımız SQL sorgularını çalıştırmaktadır. 
Döküman Asistanı ise verilen dökümanların içerisindeki text'leri ChromaDB üzerinde kaydedip daha sonra fotoğraflar var ise bunların üzerindeki yazıları da OCR ile okuyup bunları da ChromaDB'ye kaydedip
sorgular için hazır hale getirmektedir. Aynı zamanda bu agent içerisinde fotoğrafların alakalık düzeyini ölçerek girilen prompt'a göre en uygun görseli seçen bir yapı ve girilen prompt eğer analiz ve grafik
oluşturmayı gerektiriyorsa da dökümanlar içerisindeki verileri analiz edip buradaki verilere göre bir çok çeşit grafik oluşturabilen bir yapı da bulunmaktadır.
