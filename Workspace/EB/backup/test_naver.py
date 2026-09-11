import requests

url = "https://map.naver.com/p/api/search/allSearch?query=%EC%B2%AD%EC%A3%BC%20%ED%9D%A5%EB%8D%95%EA%B5%AC%20%EB%B4%89%EB%AA%85%EB%8F%99%20%EB%A7%9B%EC%A7%91"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://map.naver.com/p/"
}
res = requests.get(url, headers=headers)
try:
    print(res.json().keys())
    print(res.json().get('result', {}).get('place', {}).get('list', [])[0]['name'])
except Exception as e:
    print(e)
