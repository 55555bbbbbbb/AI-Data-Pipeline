import json
from src.crawler import run_crawler
from src.analyzer import run_two_step_pipeline
from src.formatter import run_formatter

def main():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("1. 執行爬蟲")
    print("2. 執行 AI 分析")
    print("3. 執行資料格式化與切割")
    choice = input("請選擇: ")

    if choice == '1':
        run_crawler(config)
    elif choice == '2':
        run_two_step_pipeline(config)
    elif choice == '3':
        run_formatter()

if __name__ == "__main__":
    main()