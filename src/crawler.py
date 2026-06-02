import os
import requests
import hashlib
import re
import urllib3
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import trafilatura
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin, unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ... (輔助函式 setup_environment, is_same_domain, normalize_url, is_file_link, get_filename_from_cd, download_file, get_content_hash 保持不變，與上版相同) ...
def setup_environment(domain_name):
    clean_domain = domain_name[4:] if domain_name.startswith('www.') else domain_name
    folder_name = f"downloads_{clean_domain}"
    if not os.path.exists(folder_name): os.makedirs(folder_name)
    return folder_name

def is_same_domain(url, seed_domain):
    target_netloc = urlparse(url).netloc
    clean_target = target_netloc[4:] if target_netloc.startswith('www.') else target_netloc
    clean_seed = seed_domain[4:] if seed_domain.startswith('www.') else seed_domain
    return clean_target == clean_seed

def normalize_url(url):
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")
    query = parse_qs(parsed.query)
    for param in ['Lang', 'utm_source', 'utm_medium', 'fbclid']: query.pop(param, None)
    parsed = parsed._replace(query=urlencode(query, doseq=True))
    return urlunparse(parsed)

def is_file_link(url):
    url_lower = url.lower()
    file_extensions = ('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar', '.odt', '.ods')
    if url_lower.split('?')[0].endswith(file_extensions): return True
    if "action=downloadfile" in url_lower or "download.php" in url_lower: return True
    return False

def get_filename_from_cd(cd):
    if not cd: return None
    fname = re.findall('filename="?([^"]+)"?', cd)
    if len(fname) > 0: return fname[0]
    fname = re.findall("filename\*\=utf-8\'\'(.+)", cd, re.IGNORECASE)
    if len(fname) > 0: return unquote(fname[0])
    return None

def download_file(url, download_dir):
    try:
        with requests.get(url, stream=True, timeout=30, verify=False) as r:
            r.raise_for_status()
            cd = r.headers.get('content-disposition')
            real_filename = get_filename_from_cd(cd)
            base_name = real_filename if real_filename else url.split('/')[-1].split('?')[0]
            if not base_name: base_name = "downloaded_file"
            base_name = re.sub(r'[^a-zA-Z0-9.\-\u4e00-\u9fa5]', '_', unquote(base_name))
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:6]
            name, ext = os.path.splitext(base_name)
            if not ext: ext = ".bin"
            allowed_exts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.rar', '.odt', '.ods']
            if ext.lower() not in allowed_exts:
                print(f"    -> 🛡️ 安全攔截：副檔名 {ext} 不在白名單內，放棄下載")
                return None
            safe_name = f"{name}_{url_hash}{ext}"
            file_path = os.path.join(download_dir, safe_name)
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return file_path
    except Exception as e:
        print(f"    -> ❌ 下載失敗 {url} : {e}")
        return None

def get_content_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def run_crawler(config):
    print("="*50)
    print("🤖 歡迎使用智慧網頁爬蟲 (自動化管線版)")
    print("="*50)
    
    seed_url = input("👉 請輸入目標網址: ").strip()
    if not seed_url.startswith("http"): seed_url = "https://" + seed_url
    depth_input = input("👉 請輸入爬取深度 (輸入數字，或 'all' 代表無限): ").strip().lower()
    MAX_DEPTH = float('inf') if depth_input in ['all', '-1'] else int(depth_input) if depth_input.isdigit() else 1
    
    seed_domain = urlparse(seed_url).netloc
    clean_domain = seed_domain[4:] if seed_domain.startswith('www.') else seed_domain
    OUTPUT_FILE = f"crawler_output_{clean_domain}.txt"
    download_dir = setup_environment(seed_domain)
    queue = [(seed_url, 0)]
    visited_urls = set([normalize_url(seed_url)])
    seen_content_hashes = set()
    success_count = 0
    
    print(f"\n🚀 啟動爬蟲！目標網域：{clean_domain} | 儲存位置：./{download_dir}/")
    print("-" * 50)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        with open(OUTPUT_FILE, "a+", encoding="utf-8") as file:
            while queue:
                current_url, current_depth = queue.pop(0)
                print(f"\n[{len(visited_urls)} visited] 處理中 (深度 {current_depth}): {current_url}")
                html_content = ""
                is_download_trigger = False
                try:
                    page.goto(current_url, wait_until="domcontentloaded", timeout=15000)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    page.add_style_tag(content="* { display: block !important; visibility: visible !important; opacity: 1 !important; }")
                    page.wait_for_timeout(500)
                    html_content = page.content()
                except PlaywrightTimeoutError:
                    print("  -> ⚠️ 網頁載入超時，嘗試擷取當下已渲染畫面...")
                    try: html_content = page.content()
                    except: pass
                except Exception as e:
                    if "Download is starting" in str(e):
                        print("  -> 🎣 觸發隱藏下載陷阱！自動轉交下載器處理...")
                        is_download_trigger = True
                        saved_path = download_file(current_url, download_dir)
                        if saved_path: file.write(f"\n📎 【附件下載紀錄】：已將此隱藏檔案存至 {saved_path} (來源: {current_url})\n")
                    else:
                        print(f"  -> 🔴 發生錯誤: {e}")

                if current_depth < MAX_DEPTH and not is_download_trigger:
                    try:
                        all_hrefs = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                        for href in all_hrefs:
                            full_url = urljoin(current_url, href)
                            if "javascript:" in full_url or "mailto:" in full_url: continue
                            if not is_same_domain(full_url, seed_domain): continue
                            if is_file_link(full_url):
                                print(f"  -> 📎 發現檔案連結，準備下載...")
                                saved_path = download_file(full_url, download_dir)
                                if saved_path: file.write(f"\n📎 【附件下載紀錄】：在頁面 {current_url} 發現檔案，存至 {saved_path} (來源: {full_url})\n")
                                continue
                            clean_url = normalize_url(full_url)
                            if clean_url not in visited_urls:
                                visited_urls.add(clean_url)
                                queue.append((full_url, current_depth + 1))
                    except Exception: pass

                if html_content and not is_download_trigger:
                    extracted_json_str = trafilatura.extract(html_content, favor_precision=False, include_formatting=True, output_format="json", target_language="zh")
                    if extracted_json_str:
                        data = json.loads(extracted_json_str)
                        text_content = data.get('text', '')
                        if text_content.strip():
                            content_hash = get_content_hash(text_content)
                            if content_hash in seen_content_hashes:
                                print("  -> 🛡️ 觸發防禦：內容重複，略過寫入")
                            else:
                                seen_content_hashes.add(content_hash)
                                file.write(f"\n{'='*20} 來源網址：{current_url} (深度 {current_depth}) {'='*20}\n")
                                if data.get('title'): file.write(f"【網頁主標題】：{data['title']}\n")
                                file.write("\n--- 正文開始 ---\n")
                                file.write(text_content + "\n")
                                success_count += 1
                                print("  -> 🟢 成功：寫入文章內容！")
                        else: print("  -> 🟡 略過：網頁無實質文字")
                    else: print("  -> 🟡 略過：無法萃取主文")
        browser.close()
        print("\n" + "=" * 40)
        print(f"🎉 任務圓滿結束！總共造訪了 {len(visited_urls)} 個網址，寫入 {success_count} 篇內文。")