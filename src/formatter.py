import os
import re
import pandas as pd
import math

try: import pdfplumber
except ImportError: pdfplumber = None

try: from docx import Document
except ImportError: Document = None

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text_content = ""
    if ext == ".pdf" and pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        except Exception: pass
    elif ext in [".docx", ".doc"] and Document:
        try:
            doc = Document(file_path)
            text_content = "\n".join([p.text for p in doc.paragraphs])
        except Exception: pass
    return text_content.strip()

def run_formatter():
    print("==================================================")
    print(" 📦 知識庫打包與切割管線")
    print("==================================================\n")
    
    excel_files = [f for f in os.listdir('.') if f.startswith('crawler_output_') and f.endswith('.xlsx')]
    if not excel_files:
        print("❌ 找不到分析完的 Excel 檔案！")
        return
        
    print("=== 📂 請選擇要打包的 Excel 分析結果 ===")
    for i, f in enumerate(excel_files, 1): print(f" [{i}] {f}")
    try:
        choice = int(input("請輸入編號："))
        selected_excel = excel_files[choice - 1]
    except (ValueError, IndexError): return

    domain = selected_excel.replace("crawler_output_", "").replace(".xlsx", "")
    txt_filename = f"crawler_output_{domain}.txt"
    download_folder = f"downloads_{domain}"
    ai_txt_out = f"AI知識庫_{domain}.txt"

    print(f"\n🎯 鎖定網域目標：{domain}")
    print("⏳ 正在組裝專用知識庫，請稍候...")

    raw_text_dict = {}
    if os.path.exists(txt_filename):
        with open(txt_filename, 'r', encoding='utf-8', errors='ignore') as f:
            raw_articles = f.read().split("==================== 來源網址：")
        for article in raw_articles:
            if not article.strip(): continue
            parts = article.split("\n", 1)
            raw_text_dict[parts[0].split("(深度")[0].strip()] = parts[1].strip() if len(parts) > 1 else ""

    try: df = pd.read_excel(selected_excel)
    except Exception as e:
        print(f"❌ 讀取 Excel 失敗：{e}")
        return

    col_url = df.columns[0]
    col_category = "分類標籤" if "分類標籤" in df.columns else df.columns[2]
    col_keywords = "關鍵字" if "關鍵字" in df.columns else df.columns[3]
    col_summary = "文章摘要" if "文章摘要" in df.columns else df.columns[4]
    col_attachment = "附件檔名" if "附件檔名" in df.columns else None

    total_count = len(df)
    success_count = 0

    with open(ai_txt_out, "w", encoding="utf-8", errors="ignore") as f_out:
        for idx, row in df.iterrows():
            current_idx = idx + 1
            print(f"   ➤ 處理進度: [{current_idx}/{total_count}]", end="\r")
            try:
                url = str(row[col_url]).strip()
                category = str(row[col_category])
                keywords = str(row[col_keywords])
                summary = str(row[col_summary])
                web_raw = raw_text_dict.get(url, "")
                web_raw_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', web_raw)

                attachment_raw = ""
                att_name = ""
                if col_attachment and pd.notna(row[col_attachment]) and str(row[col_attachment]).strip() not in ["", "無", "nan"]:
                    att_name = str(row[col_attachment]).strip()
                if not att_name:
                    attachment_match = re.search(r'存至\s+([^\n\s]+\.(pdf|docx|doc))', web_raw, re.IGNORECASE)
                    if attachment_match: att_name = os.path.basename(attachment_match.group(1).strip())
                if att_name:
                    full_file_path = os.path.join(download_folder, att_name)
                    if os.path.exists(full_file_path):
                        att_text = extract_text_from_file(full_file_path)
                        if att_text: attachment_raw = f"\n\n【附件原始內文】：\n{att_text}"

                f_out.write("==================================================\n")
                f_out.write(f"【來源網址】：{url}\n")
                f_out.write(f"【戰略分類】：{category}\n")
                f_out.write(f"【焦點關鍵字】：{keywords}\n")
                f_out.write(f"【課程核心摘要】：{summary}\n\n")
                f_out.write(f"【網頁原始內文】：\n{web_raw_clean}")
                f_out.write(f"{attachment_raw}\n")
                f_out.write("==================================================\n\n")
                success_count += 1
            except Exception: pass

    print(f"\n✅ 成功產出基礎知識庫，共處理 {success_count} 筆資料。")

    try:
        parts_input = input("\n👉 請問你要把檔案切成幾份上傳？ (直接按 Enter 預設為 2 份): ")
        parts = int(parts_input) if parts_input.strip() else 2
        parts = max(2, parts)
    except ValueError:
        print("輸入無效，自動設定為 2 份。")
        parts = 2

    with open(ai_txt_out, 'r', encoding='utf-8', errors='ignore') as f:
        raw_blocks = f.read().split("【來源網址】：")
    valid_articles = ["【來源網址】：" + b for b in raw_blocks if "【戰略分類】" in b]

    total = len(valid_articles)
    if total == 0:
        print("❌ 找不到有效文章進行切割。")
        return
        
    chunk_size = math.ceil(total / parts)
    print("\n⏳ 開始切割檔案...")
    for p in range(parts):
        chunk = valid_articles[p * chunk_size : (p + 1) * chunk_size]
        if not chunk: break
        out_name = f"AI知識庫_{domain}_Part{p+1}.txt"
        with open(out_name, 'w', encoding='utf-8') as f:
            f.write("==================================================\n" + "".join(chunk))
        print(f" 📦 產出 {out_name} (包含 {len(chunk)} 篇)")
    
    print("\n🎉 打包切割任務圓滿結束！")