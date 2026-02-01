import time
import os
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def init_firebase():
    if not os.path.exists("key.json"):
        print("❌ key.json 파일이 없습니다!")
        return False
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })
    return True

def start_juice24():
    print("🚀 쥬스24(juice24) 수집 시작 (1~13페이지)...")
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/juice24')

    seen_names = set()

    try:
        # 1. 1페이지부터 13페이지까지 순회
        for pg in range(1, 14):
            target_url = f"https://juice24.kr/product/list.html?cate_no=48&page={pg}"
            driver.get(target_url)
            print(f"📡 {pg}페이지 접속 중...")
            time.sleep(5) 

            # 2. 상품 리스트 확보
            items = driver.find_elements(By.CSS_SELECTOR, ".prdList > li")
            if not items:
                print(f"⚠️ {pg}페이지에 상품이 없습니다.")
                break

            print(f"📦 {pg}페이지 {len(items)}개 감지. 상세 데이터 추출 중...")

            save_count = 0
            for item in items:
                try:
                    # 이름 추출
                    name_el = item.find_elements(By.CSS_SELECTOR, ".description .name a span:last-child, .name a")
                    if not name_el: continue
                    name = name_el[0].text.strip()
                    
                    # [중복 방지]
                    if name in seen_names:
                        continue

                    # [최저가 추출] '할인판매가' 등을 포함한 모든 가격 중 최소값 선택
                    price_elements = item.find_elements(By.CSS_SELECTOR, "ul.xans-product-listitem li span")
                    prices = []
                    for p_el in price_elements:
                        txt = p_el.text
                        num = int(''.join(filter(str.isdigit, txt)) or 0)
                        if num > 3000: # 유효 가격대만 필터링
                            prices.append(num)
                    
                    final_price = min(prices) if prices else 0

                    if name and final_price > 3000:
                        safe_key = "".join(c for c in name if c.isalnum())
                        ref.child(safe_key).update({
                            "name": name,
                            "price": final_price,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print(f"   ✅ [저장] {name[:12]} | {final_price}원")
                        seen_names.add(name)
                        save_count += 1
                except:
                    continue
            
            print(f"📊 {pg}페이지 결과: {save_count}개 신규 저장됨.")

    finally:
        driver.quit()
        print("🏁 쥬스24 수집 완료.")

if __name__ == "__main__":
    if init_firebase():
        start_juice24()