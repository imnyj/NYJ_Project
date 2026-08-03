import urllib.request
import urllib.parse
import json

def search_crossref(query):
    url = f'https://api.crossref.org/works?query={urllib.parse.quote(query)}&select=title,author,issued,container-title,DOI&rows=2'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mailto:imnyj@test.com'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        print(f"--- Crossref results for: {query} ---")
        for item in data['message']['items']:
            print(item)
    except Exception as e:
        print(e)

search_crossref("Transformer trajectory prediction vehicle")
search_crossref("CVAE vehicle trajectory prediction")
