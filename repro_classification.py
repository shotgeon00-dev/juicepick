
# Mocking the classification logic from build_site.py
import re

CATEGORIES = {
    "연초": ["시가", "타바코", "말보로", "던힐", "카멜", "마일드", "세븐", "버지니아", "클래식", "토바코", "구수한", "누룽지", "트리베카"],
    "디저트": ["치즈", "케이크", "케익", "크림", "커피", "바닐라", "초코", "초콜릿", "우유", "밀크", "카라멜", "팝콘", 
              "쿠키", "버터", "빵", "도넛", "푸딩", "아이스크림", "빙수", "요거트", "타르트", "마카롱", "커스터드"]
}

def classify_category(name):
    name_lower = name.lower()
    for k in CATEGORIES["연초"]:
        if k in name_lower: return "연초"
    for k in CATEGORIES["디저트"]:
        if k in name_lower: return "디저트"
    return "과일/멘솔"

def test_case(name, expected, description):
    result = classify_category(name)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {description}: '{name}' -> Got '{result}', Expected '{expected}'")

print("--- Current Logic Test ---")
test_case("세븐코리아 포카리", "과일/멘솔", "Brand 'Seven Korea' should be ignored for 연초 trigger")
test_case("레드 세븐데이즈 애플", "과일/멘솔", "Brand 'Seven Days' should be ignored for 연초 trigger")
test_case("마일드 세븐", "연초", "Real Tobacco product 'Mild Seven' should stay 연초")
test_case("세븐 믹스", "연초", "Generic 'Seven' should trigger 연초 if not exception")
