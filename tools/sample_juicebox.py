"""
Firebase DB에서 쥬스박스 상품명 샘플 확인
"""
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate('key.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

products = db.reference('products').get() or {}

print("=== 쥬스박스 상품명 샘플 (최대 20개) ===\n")
count = 0
for key, product in products.items():
    if not product:
        continue
    
    sites = product.get('sites', {})
    for site_name in sites.keys():
        if '쥬스박스' in site_name or 'juicebox' in site_name.lower():
            name = product.get('name', '')
            print(f"[{key[:8]}] {name}")
            count += 1
            if count >= 20:
                break
    if count >= 20:
        break

print(f"\n총 {count}개 샘플 출력")
