import os
import fitz  # PyMuPDF
import pdfplumber



def extract_images_and_tables(
    data_folder: str = "data",
    output_folder: str = "static/images",
    pad: int = 5,
    resolution: int = 200
) -> None:
    """
    """
    # Tek klasör altında hem görseller hem tablolar için klasör oluştur
    os.makedirs(output_folder, exist_ok=True)

    # "data" klasöründeki tüm PDF dosyalarını tara
    for entry in os.listdir(data_folder):
        if not entry.lower().endswith('.pdf'):
            continue
        pdf_path = os.path.join(data_folder, entry)
        pdf_doc = fitz.open(pdf_path)

        # 1. Gömülü görselleri çıkar
        for page_num, page in enumerate(pdf_doc, start=1):
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                base_image = pdf_doc.extract_image(xref)
                img_bytes = base_image["image"]
                ext = base_image["ext"]
                filename = f"{entry[:-4]}_page{page_num}_img{img_index}.{ext}"
                out_path = os.path.join(output_folder, filename)
                # Var olan dosyayı tekrar oluşturma
                if not os.path.exists(out_path):
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)

        # 2. Tablo alanlarını tespit et ve kırp
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                for tbl_index, table in enumerate(page.find_tables(), start=1):
                    # Tablo bbox'unu al ve kenar boşluğu ekle
                    x0, y0, x1, y1 = table.bbox
                    x0_p = max(x0 - pad, 0)
                    y0_p = max(y0 - pad, 0)
                    x1_p = min(x1 + pad, page.width)
                    y1_p = min(y1 + pad, page.height)

                    # Cropping
                    crop = page.within_bbox((x0_p, y0_p, x1_p, y1_p))
                    im = crop.to_image(resolution=resolution)
                    filename = f"{entry[:-4]}_page{page_num}_table{tbl_index}.png"
                    out_path = os.path.join(output_folder, filename)
                    # Var olan dosyayı tekrar oluşturma
                    if not os.path.exists(out_path):
                        im.save(out_path, format="PNG")

        pdf_doc.close()

if __name__ == "__main__":
    extract_images_and_tables()