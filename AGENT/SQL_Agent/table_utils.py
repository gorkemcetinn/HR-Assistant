def create_table(rows, columns=None):
    """Verilen veriyle HTML tablo oluşturur (küçük boyutlu)"""
    if not rows:
        return "Görüntülenecek veri bulunamadı."

    # Eğer her satır bir sözlükse, kolon adlarını otomatik al
    if not columns:
        if isinstance(rows[0], dict):
            columns = list(rows[0].keys())
            rows = [[row[col] for col in columns] for row in rows]
        else:
            columns = [f"{i + 1}" for i in range(len(rows[0]))]

    html = "<table border='1' style='border-collapse: collapse; font-size: 12px; '>"
    html += "<thead><tr>"
    for col in columns:
        html += f"<th style='padding: 4px 6px;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for row in rows:
        html += "<tr>"
        for cell in row:
            html += f"<td style='padding: 4px 6px;'>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html
