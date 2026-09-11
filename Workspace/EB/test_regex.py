import requests
import re

res = requests.get('http://place.map.kakao.com/1610896349', headers={'User-Agent': 'Mozilla/5.0'})
html = res.text

# Usually the JSON state is embedded in a script tag like data-react-helmet or window.__INITIAL_STATE__
match = re.search(r'window\.location\.replace\(".+?"\);', html)
if match:
    print("Redirect page")
else:
    # let's look for rating or review
    import json
    # find lines with review
    for line in html.splitlines():
        if 'blogrvwcnt' in line or 'review' in line or 'rating' in line:
            print(line.strip()[:200])
