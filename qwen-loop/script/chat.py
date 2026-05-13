import asyncio
import json
import re
from nltk.tokenize import sent_tokenize
import logging

# 캐싱 딕셔너리 초기화
cache = {}

def optimize_tokens(input_text):
    # 불필요한 메타데이터 제거
    input_text = re.sub(r'\[.*?\]', '', input_text)
    # 문장 단위로 분리
    sentences = sent_tokenize(input_text)
    return ' '.join(sentences)

async def fetch_data(url, max_bytes=None):
    if url in cache:
        return cache[url]
    
    response = await web_fetch({"tool": "web_fetch", "args": {"url": url, "max_bytes": max_bytes}})
    cache[url] = response
    return response

async def process_data(urls):
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

def load_user_profile(user_id):
    try:
        with open(f'profiles/{{user_id}}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_profile(user_id, profile):
    with open(f'profiles/{{user_id}}.json', 'w') as f:
        json.dump(profile, f)

logging.basicConfig(filename='error.log', level=logging.ERROR)

def log_error(error_message):
    logging.error(error_message)

async def chat_loop():
    while True:
        user_input = input("사용자: ")
        
        # 토큰 최적화
        optimized_input = optimize_tokens(user_input)
        
        # 사용자 프로필 로드
        user_id = "12345"  # 예시 사용자 ID, 실제 사용 시 동적으로 설정
        profile = load_user_profile(user_id)
        
        try:
            if "web_search" in optimized_input:
                query = optimized_input.replace("web_search", "").strip()
                results = await web_search({"tool": "web_search", "args": {"query": query}})
                print(f"검색 결과: {{results}}")
            else:
                # 일반적인 응답 처리
                response = f"응답: {{optimized_input}}"  # 실제 응답 로직으로 대체
                print(response)
                
                # 사용자 프로필 업데이트 (예시)
                profile['preferences'] = {'tone': 'formal', 'language': 'ko'}
                save_user_profile(user_id, profile)
        
        except Exception as e:
            log_error(f"Error: {{e}}")
            print("오류가 발생했습니다. 다시 시도해 주세요.")

if __name__ == "__main__":
    asyncio.run(chat_loop())