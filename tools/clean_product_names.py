"""
Firebase DB에서 '이미지' 포함된 상품명 검색 및 정리
- ml 뒤에 붙어있는 모든 문자 삭제
"""
import firebase_admin
from firebase_admin import credentials, db
import re

cred = credentials.Certificate('key.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juicehunter-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

products = db.reference('products').get() or {}

print("=== '이미지' 포함 상품명 검색 ===\n")
found = []
for key, product in products.items():
    if not product:
        continue
    name = product.get('name', '')
    if '이미지' in name:
        found.append((key, name))
        if len(found) <= 20:
            print(f"[{key[:8]}] {name}")

print(f"\n총 {len(found)}개 상품에 '이미지' 포함됨")

# 정리 실행
if found:
    print("\n=== 상품명 정리 시작 ===\n")
    for key, name in found:
        # ml 뒤에 붙어있는 모든 문자 삭제
        new_name = re.sub(r'(\d+\s*[mM][lL]).*$', r'\1', name)
        if new_name != name:
            db.reference(f'products/{key}/name').set(new_name)
            print(f"✅ '{name}' -> '{new_name}'")
    print(f"\n🎉 {len(found)}개 상품명 정리 완료")
