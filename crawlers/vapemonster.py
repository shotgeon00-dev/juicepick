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
    key_path = "key.json"
    if not os.path.exists(key_path): return False
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app' 
        })
    return True

def start_vape():
    print("🚀 베이프몬스터 최신 카테고리(016002) 수집 시작...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 이제 구조를 잡았으니 다시 꺼도 됩니다.
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    ref = db.reference('products/vapemonster')

    # 주신 새로운 주소
    base_url = "https://vapemonster.co.kr/goods/goods_list.php?cateCd=016002"

    try:
        for pg in range(1, 11):
            target_url = f"{base_url}&page={pg}"
            driver.get(target_url)
            time.sleep(3) # 목록 로딩 대기

            # 고도몰 특유의 상품 리스트 선택자 (item_gallery_type 또는 item_list)
            # 베몬은 현재 item_basket_type 스타일을 사용 중입니다.
            items = driver.find_elements(By.CSS_SELECTOR, ".item_gallery_type > ul > li, .item_basket_type > ul > li")
            
            if not items:
                print(f"🏁 {pg}페이지에 상품이 더 이상 없습니다.")
                break

            found_on_page = 0
            for item in items:
                try:
                    # 1. 이름 (strong.item_name 또는 .item_info_cont .item_tit)
                    name = item.find_element(By.CSS_SELECTOR, ".item_tit_box .item_name, .item_name").text.strip()
                    
                    # 2. 가격 (strong.item_price)
                    price_text = item.find_element(By.CSS_SELECTOR, ".item_price_box .item_price, .item_price").text
                    price = int(''.join(filter(str.isdigit, price_text)) or 0)
                    
                    # 3. 이미지 및 ID
                    img = item.find_element(By.CSS_SELECTOR, ".item_photo_box img").get_attribute("src")
                    link = item.find_element(By.CSS_SELECTOR, ".item_photo_box a").get_attribute("href")
                    
                    # 주소에서 goodsNo 추출 (예: goodsNo=1000000123)
                    p_id = link.split("goodsNo=")[-1].split("&")[0]

                    if name and price > 0:
                        ref.child(f"item_{p_id}").update({
                            "name": name,
                            "price": price,
                            "img": img,
                            "link": link,
                            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        found_on_page += 1
                        print(f"   ✅ [DB저장] {name[:12]} | {price}원")
                except:
                    continue
            
            print(f"📊 {pg}페이지 완료 ({found_on_page}개 수집)")

    finally:
        print("\n👋 베몬 수집 종료!")
        driver.quit()

if __name__ == "__main__":
    if init_firebase():
        start_vape()