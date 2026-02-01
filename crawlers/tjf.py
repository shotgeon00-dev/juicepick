import time
import os
import re  # 정규표현식 추가
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

def start_tjf():
    print("🚀 더쥬스팩토리(TJF) 수집 시작 (첫 번째 숫자만 추출)")
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/tjf')

    seen_names = set()

    try:
        for pg in range(1, 4):
            target_url = f"https://www.tjf.kr/?productListFilter=241674&productListPage={pg}&productSortFilter=PRODUCT_ORDER_NO"
            driver.get(target_url)
            print(f"📡 {pg}페이지 접속 중 (8초 대기)...")
            time.sleep(8) 

            items = driver.find_elements(By.CSS_SELECTOR, "div[class*='shopProduct'], .shopProduct, .product_item")
            
            if not items:
                print(f"⚠️ {pg}페이지에서 상품 컨테이너를 찾지 못했습니다.")
                continue

            save_count = 0
            for item in items:
                try:
                    name_el = item.find_elements(By.CSS_SELECTOR, ".productName, .name, h4, .tit")
                    if not name_el: continue
                    name = name_el[0].text.strip()
                    
                    if name in seen_names:
                        continue

                    # [핵심 수정 부분]
                    price_el = item.find_elements(By.CSS_SELECTOR, ".productPriceSpan, .price, .pay")
                    if not price_el: continue
                    
                    # 1. 태그 안의 전체 텍스트를 가져옴 (예: "13,000원 14,000원")
                    full_price_text = price_el[0].text.replace(',', '') 
                    
                    # 2. 정규식을 사용해 "첫 번째로 등장하는 숫자 뭉치"만 추출
                    # \d+ 는 연속된 숫자를 의미합니다.
                    match = re.search(r'\d+', full_price_text)
                    if match:
                        price = int(match.group()) # 첫 번째 매칭된 숫자(13000)만 가져옴
                    else:
                        price = 0

                    if name and price > 3000:
                        safe_key = "".join(c for c in name if c.isalnum())
                        ref.child(safe_key).update({
                            "name": name,
                            "price": price,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print(f"    ✅ [저장 완료] {name[:15]} | {price}원")
                        
                        seen_names.add(name)
                        save_count += 1
                except Exception as e:
                    continue
            
            print(f"📊 {pg}페이지에서 총 {save_count}개 신규 저장 성공.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()
        print("🏁 수집 완료.")

if __name__ == "__main__":
    if init_firebase():
        start_tjf()