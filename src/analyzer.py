import os
import re
import json
import time
import pandas as pd
from openai import OpenAI

try: import pdfplumber
except ImportError: pdfplumber = None

try: from docx import Document
except ImportError: Document = None

# ... (輔助函式 extract_text_from_file, clean_and_parse_json 保持不變) ...
def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text_content = ""
    if ext == ".pdf":
        if pdfplumber is None: return ""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        except Exception: pass
    elif ext in [".docx", ".doc"]:
        if Document is None: return ""
        try:
            doc = Document(file_path)
            text_content = "\n".join([p.text for p in doc.paragraphs])
        except Exception: pass
    return text_content.strip()

def clean_and_parse_json(raw_text):
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return json.loads(raw_text)
    except Exception: raise ValueError("無法解析 JSON")

def select_inputs_via_cli():
    all_files = os.listdir(".")
    txt_files = [f for f in all_files if f.endswith(".txt")]
    folders = [f for f in all_files if os.path.isdir(f)]
    if not txt_files:
        print("❌ 當前目錄下沒有找到可供分析的純文字檔！")
        return None, None
    print("\n=== 📂 請選擇您要分析的文字檔 (.txt) ===")
    for i, f in enumerate(txt_files, 1): print(f" [{i}] {f}")
    while True:
        try:
            choice_txt = int(input("請輸入編號："))
            if 1 <= choice_txt <= len(txt_files):
                selected_txt = txt_files[choice_txt - 1]
                break
        except ValueError: pass
        print("⚠️ 輸入錯誤，請輸入正確的數字編號。")
        
    print("\n=== 📁 請選擇下載的附件所存放的資料夾 ===")
    print(" [0] 🚫 本次不處理任何附件")
    for i, f in enumerate(folders, 1): print(f" [{i}] {f}")
    while True:
        try:
            choice_folder = int(input("請輸入編號："))
            if choice_folder == 0:
                selected_folder = None
                break
            elif 1 <= choice_folder <= len(folders):
                selected_folder = folders[choice_folder - 1]
                break
        except ValueError: pass
        print("⚠️ 輸入錯誤，請輸入正確的數字編號。")
    return selected_txt, selected_folder

def run_two_step_pipeline(config):
    print("==================================================")
    print(" 🧠 啟動 AI 情資結構化分析管線")
    print("==================================================")
    
    input_txt, attachment_folder = select_inputs_via_cli()
    if not input_txt: return
    
    base_name = os.path.splitext(input_txt)[0]
    output_excel = f"{base_name}.xlsx"
    client = OpenAI(base_url=config["api_base"], api_key=config["api_key"])

    print(f"\n🚀 開始執行分析管線...")
    print(f"📄 輸入文字檔：{input_txt}")
    print(f"📂 附件資料夾：{attachment_folder if attachment_folder else '（未啟用）'}")
    print(f"📊 輸出報表點：{output_excel}\n")

    with open(input_txt, 'r', encoding='utf-8') as f: content = f.read()
    raw_articles = content.split("==================== 來源網址：")
    articles_to_process = [a for a in raw_articles if a.strip()]
    total_count = len(articles_to_process)

    final_rows = []
    categories_str = json.dumps(config["categories"], ensure_ascii=False)
    system_prompt_a = f"{config['prompt_role_a']}\n可選分類: {categories_str}\n請輸出 JSON:\n{{\"Reasoning\":\"\",\"Category\":\"\",\"Keywords\":[],\"Summary\":\"\"}}"

    for idx, article_raw in enumerate(articles_to_process):
        current_num = idx + 1
        print(f"⏳ [{current_num}/{total_count}] 正在處理中...")
        url_line = "未知網址"
        reasoning, category, keywords, summary, status, attachment_name, note_msg = "", "", "", "", "成功", "無", ""
        
        try:
            parts = article_raw.split("\n", 1)
            url_line = parts[0].split("(深度")[0].strip()
            text_content = parts[1].strip() if len(parts) > 1 else ""
            cleaned_web_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text_content)

            response_a = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": system_prompt_a},
                    {"role": "user", "content": f"網址：{url_line}\n內文：\n{cleaned_web_text[:2000]}"}
                ],
                temperature=0.1
            )
            json_a = clean_and_parse_json(response_a.choices[0].message.content)

            reasoning = json_a.get("Reasoning", "")
            category = json_a.get("Category", "")
            summary = json_a.get("Summary", "")
            kw_list = json_a.get("Keywords", [])
            keywords = ", ".join(kw_list) if isinstance(kw_list, list) else str(kw_list)

            attachment_match = re.search(r'存至\s+([^\n\s]+\.(pdf|docx|doc|xlsx|xls|odt))', text_content, re.IGNORECASE)
            
            if category == "Noise_Trash":
                note_msg = "網頁判定為雜訊，跳過附件分析"
                print("   🛑 網頁初審為雜訊，跳過附件以節省效能。")
            elif attachment_match and attachment_folder:
                attachment_name = os.path.basename(attachment_match.group(1).strip())
                full_file_path = os.path.join(attachment_folder, attachment_name)
                if os.path.exists(full_file_path):
                    file_text = extract_text_from_file(full_file_path)
                    file_char_len = len(file_text)
                    if file_char_len > 3000:
                        note_msg = "檔案過長跳過分析"
                        print(f"   ⚠️ 附件字數過長 ({file_char_len} 字)，保留網頁初審。")
                    elif file_char_len > 0 and not file_text.startswith("["):
                        print(f"   🔍 偵測到安全長度附件 ({file_char_len} 字)，啟動複審優化...")
                        system_prompt_b = f"{config['prompt_role_b']}\n初步分析:\n{json.dumps(json_a, ensure_ascii=False)}\n可選分類:{categories_str}"
                        response_b = client.chat.completions.create(
                            model=config["model"],
                            messages=[
                                {"role": "system", "content": system_prompt_b},
                                {"role": "user", "content": f"檔名：{attachment_name}\n內文：\n{file_text}"}
                            ],
                            temperature=0.1
                        )
                        json_b = clean_and_parse_json(response_b.choices[0].message.content)
                        reasoning = json_b.get("Reasoning", reasoning)
                        category = json_b.get("Category", category)
                        summary = json_b.get("Summary", summary)
                        kw_list_b = json_b.get("Keywords", [])
                        keywords = ", ".join(kw_list_b) if isinstance(kw_list_b, list) else str(kw_list_b)
                        note_msg = "附件成功融合優化"
            
            print(f"✅ [{current_num}/{total_count}] 分析成功！標籤：[{category}]")
        except Exception as e:
            status = "失敗"
            print(f"❌ [{current_num}/{total_count}] 發生錯誤：{str(e)}")

        final_rows.append({
            "來源網址": url_line,
            "推論過程": reasoning,
            "分類標籤": category,
            "關鍵字": keywords,
            "文章摘要": summary,
            "附件檔名": attachment_name,
            "處理狀態": status,
            "檔案備註": note_msg
        })

        if current_num % 10 == 0:
            pd.DataFrame(final_rows).to_excel(output_excel, index=False)
            print(f"💾 自動備份：已儲存前 {current_num} 篇資料。")
        time.sleep(0.3)

    pd.DataFrame(final_rows).to_excel(output_excel, index=False)
    print(f"\n🎉 全數分析完畢！報表已儲存至：{output_excel}")