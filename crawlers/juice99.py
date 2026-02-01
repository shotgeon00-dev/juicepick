import time
import os
import re
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

def start_99juice():
    print("🚀 99쥬스(99juice) 강제 수집 모드 가동...")
    options = Options()
    # 자동화 탐지 회피용 설정 추가
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/juice99')
    seen_names = set()

    try:
        for pg in range(1, 14):
            target_url = f"https://99juice.co.kr/category/%EC%9E%85%ED%98%B8%ED%9D%A1-%EC%95%A1%EC%83%81/42/?page={pg}"
            driver.get(target_url)
            print(f"📡 {pg}페이지 접속... (10초 대기하며 데이터 강제 로딩)")
            time.sleep(10) # 사이트가 무거우므로 충분히 대기

            # [수정] 모든 상품 박스 후보군을 싹 다 긁어모음
            # id에 anchorBox가 있거나, 클래스에 sp-product-box가 있는 모든 요소를 타겟팅
            items = driver.find_elements(By.XPATH, "//*[contains(@id, 'anchorBoxId_')] | //li[contains(@class, 'item')] | //div[contains(@class, 'sp-product-box')]")
            
            if not items:
                print(f"⚠️ {pg}페이지에서 상품 요소를 찾지 못했습니다. 브라우저 창을 확인해주세요.")
                continue

            print(f"📦 {pg}페이지 {len(items)}개 요소 감지. 정밀 필터링 시작...")

            save_count = 0
            for item in items:
                try:
                    # 1. 이름 추출 (가장 텍스트가 많은 span이나 a 태그 추출)
                    name = ""
                    name_candidates = item.find_elements(By.CSS_SELECTOR, ".name a, .sp-product-name a, strong, span")
                    for cand in name_candidates:
                        txt = cand.text.strip()
                        if len(txt) > 5: # 상품명은 보통 5자 이상인 점 이용
                            name = txt
                            break
                    
                    if not name or name in seen_names: continue

                    # 2. 가격 추출 (숫자 패턴 검색)
                    full_text = item.text.replace(',', '')
                    match = re.search(r'(\d+)원', full_text) # '원' 앞에 붙은 숫자만 추출
                    if not match:
                        match = re.search(r'\d+', full_text) # 원이 없으면 그냥 첫 숫자
                    
                    price = int(match.group(1)) if match and match.lastindex >= 1 else (int(match.group()) if match else 0)

                    # 3. 데이터 저장 (가격이 너무 낮거나 높은 건 무시)
                    if name and 3000 < price < 150000:
                        safe_key = "".join(c for c in name if c.isalnum())
                        ref.child(safe_key).update({
                            "name": name,
                            "price": price,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print(f"   ✅ [저장] {name[:12]} | {price}원")
                        seen_names.add(name)
                        save_count += 1
                except:
                    continue
            
            print(f"📊 {pg}페이지 수집 결과: {save_count}개 성공")

    finally:
        driver.quit()
        print("🏁 수집 프로세스 종료.")

if __name__ == "__main__":
    if init_firebase():
        start_99juice()