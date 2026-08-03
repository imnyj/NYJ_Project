import urllib.request
import json
dois = ["10.1109/aero66936.2026.11519972", "10.23919/ccc52363.2021.9549995", "10.5220/0010321710901096", "10.1109/tmm.2026.3673507"]
for doi in dois:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mailto:imnyj@test.com'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        item = data['message']
        print(f"--- {doi} ---")
        print(item.get('abstract', 'No abstract'))
    except Exception as e:
        print(f"Error for {doi}: {e}")
