import urllib.request
import urllib.parse
import json
import time

titles = [
    "Traffic optimized content precaching scheme based on tolerable delay time in content-centric vehicular networks",
    "Content Storage Management and Precaching Scheme in Content-Centric Networks-Based Internet of Vehicle",
    "Data delivery protocol using the trajectory information on a road map in VANETs",
    "Particle swarm optimization video streaming service in vehicular ad-hoc networks",
    "The partial cloud member replacement for reconstructing vehicular clouds in VANETs: Reactive and proactive schemes",
    "Particle Swarm Optimization-based Content Delivery Protocol for UAV VANETs",
    "Multi-hop vehicular cloud construction with connection time based resource allocation in VANETs",
    "Efficient multipath routing protocol against path failures in wireless sensor networks",
    "Mobility-aware distributed proactive caching in content-centric vehicular networks",
    "RSU-driven cloud construction and management mechanism in VANETs",
    "Cooperative content downloading protocol based on the mobility information of vehicles in intermittently connected vehicular networks",
    "Delay Tolerable Precaching Scheme in Content-Centric Vehicular Networks",
    "Set Ranking-Based Precaching Protocol in Vehicular Ad hoc Networks",
    "Enhanced Hybrid Energy-Efficient Distributed Clustering Protocol for IoT-Based WSNs with Multiple Sinks"
]

results = []

for title in titles:
    # Use CrossRef API to find the metadata
    query = urllib.parse.quote(title + " Youngju Nam")
    url = f"https://api.crossref.org/works?query.bibliographic={query}&rows=1&mailto=test@example.com"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data['message']['items']:
                item = data['message']['items'][0]
                
                # Check if it matches high quality publisher criteria
                pub = item.get('publisher', '').lower()
                valid_publishers = ['institute of electrical and electronics engineers', 'ieee', 'elsevier', 'acm', 'nature', 'springer', 'sciencedirect']
                
                if any(x in pub for x in valid_publishers):
                    # Format as a clean dictionary for bibitem use
                    authors = []
                    for author in item.get('author', []):
                        authors.append(f"{author.get('given', '')} {author.get('family', '')}".strip())
                        
                    paper_data = {
                        "title": item.get('title', [''])[0],
                        "authors": authors,
                        "publisher": item.get('publisher', ''),
                        "container-title": item.get('container-title', [''])[0] if item.get('container-title') else '',
                        "year": item.get('issued', {}).get('date-parts', [[None]])[0][0],
                        "doi": item.get('DOI', ''),
                        "volume": item.get('volume', ''),
                        "issue": item.get('issue', ''),
                        "page": item.get('page', '')
                    }
                    results.append(paper_data)
        time.sleep(0.5) # Be nice to the API
    except Exception as e:
        print(f"Error fetching {title}: {e}")

with open('/home/imnyj/publications.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4, ensure_ascii=False)
    
print(f"Saved {len(results)} papers to publications.json")
