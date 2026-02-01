import result
import difflib
from datetime import datetime

def analyze_duplicates(data):
    """
    데이터 내에서 유사한 상품명을 가진 항목들을 찾습니다.
    O(N^2) 복잡도이므로 데이터가 매우 많으면 최적화가 필요할 수 있습니다.
    """
    items = list(data.values())
    keys = list(data.keys())
    n = len(items)
    
    potential_duplicates = []
    
    print(f"🔍 총 {n}개 항목에 대해 중복 분석 시작 (Strict Mode)...")
    
    # 이름순 정렬
    items.sort(key=lambda x: x['display_name'])
    
    # Sliding Window 방식
    window_size = 50 
    
    for i in range(n):
        for j in range(1, window_size + 1):
            if i + j >= n: break
            
            item_a = items[i]
            item_b = items[i+j]
            
            name_a = item_a['display_name']
            name_b = item_b['display_name']
            
            # 1. 동일 사이트 충돌 방지
            sites_a = set(item_a['prices'].keys())
            sites_b = set(item_b['prices'].keys())
            if not sites_a.isdisjoint(sites_b):
                # 교집합이 있으면(같은 사이트에서 둘 다 팔면) 병합 금지
                continue

            # 2. 토큰 집합 포함 관계 확인 (엄격한 기준)
            # 괄호 제거 및 소문자 해체
            def tokenize(text):
                # 30ml 등 용량 단위는 구분 위해 보존하되, 특수문자는 제거
                text = text.lower().replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")
                tokens = set(text.split())
                return tokens

            tokens_a = tokenize(name_a)
            tokens_b = tokenize(name_b)
            
            # a가 b의 부분집합이거나, b가 a의 부분집합이어야 함
            # (즉, 다른 맛/단어가 섞여 있으면 안됨)
            if not (tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a)):
                continue

            # 유사도 측정 (보조 수단)
            ratio = difflib.SequenceMatcher(None, name_a, name_b).ratio()
            
            # 부분집합 관계라면 유사도는 꽤 높겠지만, 안전장치로 한번 더 확인 (0.6 이상)
            if ratio > 0.6:
                if name_a == name_b: continue
                
                # 3. 기준(Target) 자동 선정
                # 원칙: 이미지 있음 > 판매처 많음 > 이름 김
                score_a = (1 if item_a.get('image') else 0) * 100 + len(item_a['prices']) * 10 + len(name_a) * 0.1
                score_b = (1 if item_b.get('image') else 0) * 100 + len(item_b['prices']) * 10 + len(name_b) * 0.1
                
                if score_b >= score_a:
                    source, target = item_a, item_b
                else:
                    source, target = item_b, item_a

                # 중복 저장 방지 키
                pair_key = tuple(sorted([name_a, name_b]))
                
                potential_duplicates.append({
                    "item_a": source,   # 바뀔 놈
                    "item_b": target,   # 기준이 될 놈
                    "ratio": ratio,
                    "pair_key": pair_key
                })

    # 중복 제거
    unique_duplicates = []
    seen_pairs = set()
    for d in potential_duplicates:
        if d['pair_key'] not in seen_pairs:
            seen_pairs.add(d['pair_key'])
            unique_duplicates.append(d)
            
    # 유사도 순 정렬
    unique_duplicates.sort(key=lambda x: x['ratio'], reverse=True)
    return unique_duplicates

def analyze_suspicious_names(data):
    """
    이름이 너무 짧거나 이상한 패턴이 있는 상품을 찾습니다.
    """
    suspicious = []
    
    for key, item in data.items():
        name = item['display_name']
        
        # 1. 이름이 2글자 이하
        if len(name.strip()) < 2:
            suspicious.append({"item": item, "reason": "이름이 너무 짧음"})
            continue
            
        # 2. 숫자로만 구성됨
        if name.replace(" ", "").isdigit():
            suspicious.append({"item": item, "reason": "숫자로만 구성됨"})
            continue
            
        # 3. 영문+숫자 혼합인데 한글이 아예 없는 경우 (정책상 괜찮을 수도 있지만 검토 대상)
        # (이건 pass)

    return suspicious

def generate_analysis_report(duplicates, suspicious):
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>JuiceHunter 데이터 분석 리포트</title>
        <style>
            body { font-family: 'Pretendard', sans-serif; padding: 20px; background: #f9f9f9; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1, h2 { color: #333; }
            .section { margin-bottom: 40px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
            th { background: #f0f0f0; }
            .high-score { color: #e74c3c; font-weight: bold; }
            .row-dup { background-color: #fff8f8; }
            img { width: 40px; height: 40px; object-fit: cover; border-radius: 4px; vertical-align: middle; margin-right: 10px; }
            
            /* Action Bar */
            .action-bar { position: sticky; top: 0; background: white; padding: 15px; border-bottom: 2px solid #eee; z-index: 100; display: flex; justify-content: space-between; align-items: center; }
            .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
            .btn-save { background: #2ecc71; color: white; }
            .btn-save:hover { background: #27ae60; }
            .checkbox-wrapper { transform: scale(1.5); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕵️ JuiceHunter 데이터 분석 리포트</h1>
            <p>생성 시간: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            
            <div class="section">
                <h2>⚠️ 의심스러운 상품명 ({len_suspicious}개)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>상품명</th>
                            <th>이미지</th>
                            <th>이유</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    html = html.replace("{len_suspicious}", str(len(suspicious)))
    for s in suspicious:
        item = s['item']
        img = item.get('image', '')
        html += f"""
        <tr>
            <td>{item['display_name']}</td>
            <td><img src="{img}"></td>
            <td>{s['reason']}</td>
        </tr>
        """
    html += """
                    </tbody>
                </table>
            </div>

            <div class="section">
                <div class="action-bar">
                    <h2>👯 중복 예상 상품 ({len_duplicates}쌍)</h2>
                    <button class="btn btn-save" onclick="exportData()">💾 병합 설정 저장 (custom_aliases.json)</button>
                </div>
                <p>중복으로 판단되는 항목을 체크하세요. 체크된 항목은 '상품 A'가 '상품 B'로 병합(이름 변경)됩니다.</p>
                <table>
                    <thead>
                        <tr>
                            <th width="50">병합</th>
                            <th>유사도</th>
                            <th>상품 A (변경 대상)</th>
                            <th>→</th>
                            <th>상품 B (기준)</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    html = html.replace("{len_duplicates}", str(len(duplicates)))
    
    for i, d in enumerate(duplicates):
        score = int(d['ratio'] * 100)
        item_a = d['item_a']
        item_b = d['item_b']
        
        # A와 B 중 더 짧은 이름을 기준으로 삼기 위해 정렬 (보통 짧은게 깔끔함, 아니면 긴게 상세할 수도 있음)
        # 여기서는 단순히 문자열 길이로 B를 '기준'으로 삼거나, Display logic에 따라 사용자에게 맡김
        # 기본적으로 A -> B 병합으로 가정. 
        # (만약 반대를 원하면 JS에서 구현해야 하지만 복잡하므로 단순화: 체크하면 A를 B로 바꿈)
        
        html += f"""
        <tr class="row-dup">
            <td style="text-align:center;">
                <input type="checkbox" class="merge-check checkbox-wrapper" 
                       data-source="{item_a['display_name']}" 
                       data-target="{item_b['display_name']}">
            </td>
            <td class="high-score">{score}%</td>
            <td>
                <img src="{item_a.get('image', '')}">
                <strong>{item_a['display_name']}</strong><br>
                <span style="font-size:0.8em; color:#666;">{item_a['category']}</span>
            </td>
            <td style="color:#aaa; font-size:20px;">➔</td>
            <td>
                <img src="{item_b.get('image', '')}">
                <strong>{item_b['display_name']}</strong><br>
                <span style="font-size:0.8em; color:#666;">{item_b['category']}</span>
            </td>
        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            function exportData() {
                const checks = document.querySelectorAll('.merge-check:checked');
                const aliases = {};
                
                if (checks.length === 0) {
                    alert("병합할 항목을 하나 이상 선택해주세요.");
                    return;
                }
                
                checks.forEach(chk => {
                    const source = chk.getAttribute('data-source');
                    const target = chk.getAttribute('data-target');
                    // source 이름을 target 이름으로 매핑
                    aliases[source] = target;
                });
                
                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(aliases, null, 2));
                const downloadAnchorNode = document.createElement('a');
                downloadAnchorNode.setAttribute("href", dataStr);
                downloadAnchorNode.setAttribute("download", "custom_aliases.json");
                document.body.appendChild(downloadAnchorNode); // required for firefox
                downloadAnchorNode.click();
                downloadAnchorNode.remove();
                
                alert(checks.length + "개의 병합 규칙이 저장되었습니다.\\n다운로드 폴더의 'custom_aliases.json' 파일을 JuiceHunter 폴더로 옮겨주세요.");
            }
        </script>
    </body>
    </html>
    """
    
    with open("analysis_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ 분석 완료! analysis_report.html 파일이 생성되었습니다.")

if __name__ == "__main__":
    # result.py의 로직을 사용하여 데이터 가져오기 (정규화된 상태)
    data, sites = result.process_data()
    
    if data:
        duplicates = analyze_duplicates(data)
        suspicious = analyze_suspicious_names(data)
        generate_analysis_report(duplicates, suspicious)
    else:
        print("데이터를 가져오지 못했습니다.")
