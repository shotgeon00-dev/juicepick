import requests
from bs4 import BeautifulSoup

urls = [
    'https://vapemonster.co.kr/goods/goods_view.php?goodsNo=1000001078',
    'https://vapemonster.co.kr/goods/goods_view.php?goodsNo=1000000091'
]
headers = {'User-Agent': 'Mozilla/5.0'}

for u in urls:
    try:
        res = requests.get(u, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_img = soup.find('meta', property='og:image')
        if og_img:
            print(f"{u} -> {og_img['content']}")
        else:
            print(f"{u} -> No og:image")
    except Exception as e:
        print(f"{u} -> Error: {e}")
