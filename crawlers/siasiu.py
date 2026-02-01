import time
import os
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# 🔐 설정 정보
USER_ID = "qwerqwer12"
USER_PW = "qwerqwer12"

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

def start_siasiu():
    print("🚀 샤슈컴퍼니 전수 조사 시작 (1~23페이지)...")
    options = Options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    ref = db.reference('products/siasiu')

    try:
        # 1. 로그인 단계 (대기 5초)
        driver.get("https://siasiu.com/pages/sign-in/sign-in.html")
        time.sleep(5) 

        driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(USER_ID)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(USER_PW)
        driver.find_element(By.XPATH, "//button[contains(text(), '로그인')] | //button[@type='submit']").click()
        
        time.sleep(5) # 로그인 승인 대기 5초
        print("✅ 로그인 완료! 수집을 시작합니다.")

        # 2. 1페이지부터 23페이지까지 순회 (마지막 페이지 지정)
        for pg in range(1, 24):
            url = f"https://siasiu.com/pages/product/product-list.html?categoryNo=937592&pageNumber={pg}&pageSize=20"
            driver.get(url)
            time.sleep(6) # 목록 로딩 대기

            # 중복 제거 (productNo 추출)
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='productNo=']")
            if not links:
                print(f"🏁 {pg}페이지에 상품이 없습니다. 루프를 종료합니다.")
                break

            final_map = {}
            for l in links:
                href = l.get_attribute("href")
                if href and "productNo=" in href:
                    p_id = href.split("productNo=")[-1].split("&")[0]
                    final_map[p_id] = href
            
            print(f"📄 [{pg}/23] 페이지 분석 중... (실제 상품 {len(final_map)}개)")

            for p_id, detail_url in final_map.items():
                try:
                    driver.get(detail_url)
                    time.sleep(4) # 상세페이지 대기

                    name = driver.find_element(By.CSS_SELECTOR, "h2, .product-summary__title").text.strip()
                    price_txt = driver.find_element(By.CSS_SELECTOR, ".product-summary__price").text
                    price = int(''.join(filter(str.isdigit, price_txt)) or 0)

                    # 3,000원 이하 제품 제외
                    if price > 3000:
                        img = driver.find_element(By.CSS_SELECTOR, "img[src*='/product/']").get_attribute("src")
                        ref.child(f"item_{p_id}").update({
                            "name": name, "price": price, "img": img, "link": detail_url,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print(f"   ✅ [저장] {name[:12]} | {price}원")
                    else:
                        print(f"   ⏩ [제외] 3,000원 이하: {name[:12]} ({price}원)")
                except:
                    continue

    finally:
        driver.quit()
        print("🏁 23페이지까지 모든 수집이 완료되어 프로그램을 종료합니다.")

if __name__ == "__main__":
    if init_firebase():
        start_siasiu()