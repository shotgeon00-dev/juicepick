import time
import os
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
import sys
import io

# Windows에서 출력 인코딩 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import re

# Firebase 초기화 함수 (기존 key.json 활용)
def init_firebase():
    if not os.path.exists("key.json"):
        print("❌ key.json 파일이 없습니다! 크롤러 실행을 위해 key.json이 필요합니다.")
        return False
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })
    return True

def start_juicebox_test():
    print("🚀 쥬스박스(Juicebox) 테스트 수집 시작 (1~2페이지만 진행)")
    
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    # Headless 모드로 실행 (화면을 보려면 아래 라인을 주석 처리하세요)
    options.add_argument("--headless") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # 쥬스박스 전용 파이어베이스 경로 (나중에 build_site.py에서 병합 대상이 됨)
    ref = db.reference('products/juicebox')

    try:
        # 1페이지만 먼저 테스트 (range(1, 3)으로 수정하면 2페이지까지 수행)
        for page in range(1, 3):
            url = f"https://juicebox.co.kr/product/list.html?cate_no=52&page={page}"
            print(f"📖 {page}페이지 접속 중: {url}")
            driver.get(url)
            time.sleep(3) # 로딩 대기

            # Cafe24 전형적인 상품 리스트 셀렉터
            items = driver.find_elements(By.CSS_SELECTOR, ".prdList > li")
            print(f"📦 {page}페이지에서 {len(items)}개의 상품 요소를 발견했습니다.")

            save_count = 0
            for i, item in enumerate(items):
                try:
                    # [DEBUG] First item HTML check
                    if i == 0:
                        html_snippet = item.get_attribute('innerHTML')[:1000]
                        print(f"🔍 First item innerHTML (Partial): {html_snippet}")

                    # 1. Product Name Extraction
                    # 1. Product Name Criteria
                    name = ""
                    try:
                        # Strategy A: Image Alt attribute (Primary)
                        img_el = item.find_element(By.CSS_SELECTOR, ".thumbnail img, .prdImg img")
                        name = img_el.get_attribute("alt").strip()
                    except: pass
                    
                    if not name: 
                        if i == 0: print("❌ Name not found (alt attribute empty or missing)")
                        continue

                    # 2. Price Extraction
                    price = 0
                    price_text = ""
                    
                    # Regex to find price anchored by '원' (e.g., 25,000원)
                    # This prevents capturing "22,000 220P" as 22000220
                    def extract_price_strict(txt):
                        match = re.search(r'([\d,]+)\s*원', txt)
                        if match:
                            clean = match.group(1).replace(',', '')
                            return int(clean)
                        return 0

                    try:
                        # Priority 1: Check specific columns first with strict regex
                        spans = item.find_elements(By.CSS_SELECTOR, "li[column_name='product_price'] span, li[column_name='price_unit'] span, .price span")
                        for s in spans:
                            p = extract_price_strict(s.get_attribute("innerText"))
                            if p > 0:
                                price = p
                                price_text = s.text
                                break
                        
                        # Priority 2: Scan full text if columns failed
                        if price == 0:
                            all_text = item.text
                            lines = all_text.split('\n')
                            for line in lines:
                                p = extract_price_strict(line)
                                if p > 0:
                                    price = p
                                    price_text = line
                                    break # Take the first valid 'Won' price (usually sale price or main price)
                    except: pass

                    if i == 0:
                        print(f"   [DEBUG] Name: '{name}', Price found: {price}")
                    
                    # 3. Save Data
                    if name and price > 1000:
                        safe_key = "".join(c for c in name if c.isalnum())
                        
                        ref.child(safe_key).update({
                            "name": name,
                            "price": price,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        save_count += 1
                        print(f"   OK: {str(name)[:30]}... | {price}원")
                    else:
                        if i == 0: print(f"❌ Skipped (Price invalid: {price})")

                except Exception as e:
                    if i == 0: print(f"❌ Exception: {e}")
                    continue
            
            print(f"✨ {page}페이지 수집 완료! ({save_count}개 저장)")

        print("📊 테스트 크롤링이 모두 완료되었습니다.")

    finally:
        driver.quit()

if __name__ == "__main__":
    if init_firebase():
        start_juicebox_test()
