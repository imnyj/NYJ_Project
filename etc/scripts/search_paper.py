import urllib.request
import urllib.parse
import json

def search_arxiv(query):
    url = f'http://export.arxiv.org/api/query?search_query=all:"{urllib.parse.quote(query)}"&start=0&max_results=5'
    try:
        response = urllib.request.urlopen(url)
        print(f"--- Arxiv results for: {query} ---")
        print(response.read().decode('utf-8')[:500])
    except Exception as e:
        print(e)

def search_crossref(query):
    url = f'https://api.crossref.org/works?query={urllib.parse.quote(query)}&select=title,author,issued,container-title,DOI&rows=5'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mailto:imnyj@test.com'})
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        print(f"--- Crossref results for: {query} ---")
        for item in data['message']['items']:
            print(item)
    except Exception as e:
        print(e)

search_crossref("Spatio-Temporal Conditional Variational Autoencoder trajectory")
search_crossref("ST-CVAE trajectory")
search_crossref("Transformer trajectory prediction")
search_crossref("LSTM trajectory prediction")
search_crossref("GRU trajectory prediction")
