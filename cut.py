# -*- coding: utf-8 -*-
import os
import math

def main():
    print("==================================================")
    print(" ✂️ NotebookLM 知識庫無損切割器 (保證文章不斷尾)")
    print("==================================================\n")

    # 1. 自動抓取資料夾內所有的 AI知識庫 TXT 檔
    txt_files = [f for f in os.listdir('.') if f.startswith('AI知識庫_') and f.endswith('.txt')]
    
    if not txt_files:
        print("❌ 找不到開頭為 'AI知識庫_' 的 txt 檔案！請確認檔案位置。")
        return

    print("=== 📂 請選擇要切割的知識庫檔案 ===")
    for i, f in enumerate(txt_files, 1):
        print(f" [{i}] {f}")
        
    try:
        choice = int(input("請輸入編號："))
        selected_file = txt_files[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ 輸入錯誤，程式結束。")
        return

    print(f"\n讀取檔案中：{selected_file} ...")
    
    # 2. 讀取並以「【來源網址】：」為節點進行智慧分割
    with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 依照每篇文章的開頭標籤切開
    raw_blocks = content.split("【來源網址】：")
    
    valid_articles = []
    # 過濾掉開頭的空白段落，將文章重新組裝回來
    for block in raw_blocks:
        if "【戰略分類】" in block:
            valid_articles.append("【來源網址】：" + block)

    total_articles = len(valid_articles)
    print(f"✅ 成功辨識出 {total_articles} 篇完整的課程資料！")

    if total_articles == 0:
        print("❌ 找不到有效文章，請確認檔案格式是否正確。")
        return

    # 3. 詢問要切成幾份
    try:
        parts_input = input("👉 請問你要把檔案切成幾份？ (直接按 Enter 預設為 2 份): ")
        parts = int(parts_input) if parts_input.strip() else 2
    except ValueError:
        parts = 2
        print("輸入無效，將自動切成 2 份。")

    if parts < 2:
        print("至少要切成 2 份喔！自動設定為 2 份。")
        parts = 2

    # 4. 計算每一份要裝幾篇文章，並產出檔案
    chunk_size = math.ceil(total_articles / parts)
    base_name = selected_file.replace('.txt', '')

    print("\n⏳ 開始切割檔案...")
    
    for p in range(parts):
        start_idx = p * chunk_size
        end_idx = min(start_idx + chunk_size, total_articles)
        
        chunk_articles = valid_articles[start_idx:end_idx]
        if not chunk_articles:
            break
            
        out_name = f"{base_name}_Part{p+1}.txt"
        
        # 加上開頭的分隔線，保持原本的格式
        final_text = "==================================================\n" + "".join(chunk_articles)
        
        with open(out_name, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(final_text)
            
        print(f" 📦 產出 {out_name} (包含第 {start_idx + 1} 到 {end_idx} 篇，共 {len(chunk_articles)} 篇)")

    print("\n🎉 切割完成！現在你可以把 Part1 和 Part2 分別上傳到 NotebookLM 了！")

if __name__ == "__main__":
    main()