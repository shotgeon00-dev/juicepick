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

def start_modu():
    print("🚀 모두의액상(MODU) 수집 시작 (속도 최적화 모드)")
    options = Options()
    # 속도 향상을 위해 GPU 가속 끄기 및 불필요한 로그 제한
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/modu')

    try:
        url = "https://xn--hu1b83j3sfk9e3xc.kr/category/%EC%9E%85%ED%98%B8%ED%9D%A1-%EC%95%A1%EC%83%81/127/"
        driver.get(url)
        time.sleep(5)

        # 1. '더보기' 버튼 무한 클릭 (기존 로직 유지)
        print("⏬ 상품 펼치는 중... 잠시만 기다려주세요.")
        while True:
            try:
                more_btn = driver.find_element(By.XPATH, "//a[contains(text(), '더보기')] | //a[contains(@class, 'more')] | //span[contains(text(), 'MORE')]/..")
                if more_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", more_btn)
                    time.sleep(1.5) # 펼치는 속도 약간 상향
                else: break
            except: break

        print("✅ 펼치기 완료. 데이터 고속 추출 시작...")

        # 2. 모든 상품 리스트를 한 번에 확보
        items = driver.find_elements(By.CSS_SELECTOR, ".prdList > li")
        total_count = len(items)
        print(f"📦 총 {total_count}개의 상품을 찾았습니다.")

        save_count = 0
        for idx, item in enumerate(items):
            try:
                # [속도 개선] 상품명 추출
                name_el = item.find_element(By.CSS_SELECTOR, ".description .name a span:last-child, .name")
                name = name_el.text.strip()
                
                # [속도 개선] 가격 추출 로직 정밀화
                # find_elements 대신 textContent를 한 번에 가져와서 숫자 분리
                price_text = item.find_element(By.CSS_SELECTOR, "ul.xans-product-listitem").get_attribute("textContent")
                
                import re
                # 숫자만 다 찾아내기 (예: ['7900', '12000'])
                nums = [int(n) for n in re.findall(r'\d+', price_text.replace(',', '')) if int(n) > 3000]
                
                # 그 중 가장 작은 값을 할인가로 선택
                final_price = min(nums) if nums else 0

                if name and final_price > 3000:
                    safe_key = "".join(c for c in name if c.isalnum())
                    ref.child(safe_key).update({
                        "name": name,
                        "price": final_price,
                        "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    # 10개마다 진행 상황 출력 (터미널 멈춤 착시 방지)
                    save_count += 1
                    if save_count % 10 == 0 or idx == total_count - 1:
                        print(f"   ⏳ 진행 중... ({idx+1}/{total_count}) | 최근저장: {name[:10]}")

            except Exception:
                continue

        print(f"📊 수집 완료! 총 {save_count}개 상품 저장됨.")

    finally:
        driver.quit()

if __name__ == "__main__":
    if init_firebase():
        start_tjf() if 'start_tjf' in locals() else None # TJF가 같이 있다면 실행
        start_modu()