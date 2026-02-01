import result
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import urllib.parse
import re

# result.py에서 SEARCH_URLS 가져오기
SEARCH_URLS = result.SEARCH_URLS

def get_image_from_url(url, is_search=False):
    """URL에서 이미지 추출 (상세페이지 og:image 또는 검색결과 첫번째 이미지)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 상세 페이지일 경우 (og:image)
        if not is_search:
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return normalize_url(og_image["content"], url)
        
        # 2. 검색 결과 페이지일 경우 (첫번째 상품 이미지)
        else:
            # Cafe24 일반적인 구조 (prdList, thumbnail)
            # 다양한 셀렉터 시도
            selectors = [
                ".prdList .thumb img",      # 일반적인 목록
                ".thumbnail img",           # 썸네일 클래스
                ".prdImg img",              # 상품 이미지 클래스
                ".ec-base-product .thumb img" 
            ]
            
            for sel in selectors:
                img = soup.select_one(sel)
                if img and img.get('src'):
                    src = img['src']
                    # ec-img-hover 같은거 말고 메인 이미지
                    return normalize_url(src, url)
                    
        return None
        
    except Exception as e:
        # print(f"Error scraping {url}: {e}")
        return None

def normalize_url(img_url, base_url):
    """상대 경로를 절대 경로로 변환"""
    if img_url.startswith("//"):
        return "https:" + img_url
    if img_url.startswith("/"):
        # base_url의 도메인 추출
        parsed = urllib.parse.urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
    if not img_url.startswith("http"):
        # 경로가 좀 이상하면 일단 합치기 시도
        parsed = urllib.parse.urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}/{img_url}"
    return img_url

def fill_images():
    print("데이터 불러오는 중...")
    data, _ = result.process_data()
    
    # 2곳 이상 판매중인데 이미지가 없는 상품 필터링
    targets = []
    for key, item in data.items():
        if not item.get('image') and len(item['prices']) >= 2:
            targets.append((key, item))
            
    print(f"🎯 총 {len(targets)}개의 상품에 대해 이미지 검색을 시작합니다.")
    
    found_images = {}
    count = 0
    success = 0
    
    # 우선순위 사이트 (검색이 잘 되는 곳)
    PRIORITY_SITES = ['modu', 'juice24', 'tjf']

    for key, item in targets:
        count += 1
        print(f"[{count}/{len(targets)}] {item['display_name']} 검색 중...", end="\r")
        
        # 1. 기존 링크 확인
        links = [site_info['link'] for site_info in item['prices'].values() if site_info.get('link')]
        valid_links = [l for l in links if "search.html" not in l]
        
        img_url = None
        
        # 1-1. 상세 페이지 링크가 있으면 거기서 시도
        for link in valid_links:
            img_url = get_image_from_url(link, is_search=False)
            if img_url and check_valid_image(img_url): break
            time.sleep(random.uniform(0.5, 1.0))
            
        # 2. 링크가 없거나 실패했으면 '검색' 시도
        if not img_url:
            # 검색어 생성 (특수문자 제거 등)
            query = clean_query(item['display_name'])
            encoded_query = urllib.parse.quote(query)
            
            # 우선순위 사이트 순회
            for site in PRIORITY_SITES:
                if site not in SEARCH_URLS: continue
                
                search_prefix = SEARCH_URLS[site]
                search_url = f"{search_prefix}{encoded_query}"
                
                # print(f"  - 검색 시도: {site}")
                img_url = get_image_from_url(search_url, is_search=True)
                
                if img_url and check_valid_image(img_url):
                    # print(f"  -> 검색 성공: {img_url}")
                    break
                    
                time.sleep(random.uniform(1.0, 1.5))
        
        if img_url:
            found_images[key] = img_url
            success += 1
            
    print(f"\n✨ 완료! {success}개의 이미지를 찾았습니다.")
    
    # 결과 저장
    with open("additional_images.json", "w", encoding="utf-8") as f:
        json.dump(found_images, f, ensure_ascii=False, indent=2)

def check_valid_image(url):
    if not url: return False
    if "placeholder" in url: return False
    if "noimg" in url: return False
    if "btn_buy" in url: return False # 간혹 버튼 이미지가 잡힐 때
    return True

def clean_query(name):
    # 검색 정확도를 높이기 위해 [] 괄호 제거 등
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\(.*?\)', '', name)
    # 용량 제거 (30ml 등)
    name = re.sub(r'\d+ml', '', name, flags=re.IGNORECASE)
    return name.strip()

if __name__ == "__main__":
    fill_images()
