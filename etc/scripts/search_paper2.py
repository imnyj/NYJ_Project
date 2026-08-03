import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET

def search_arxiv(query):
    url = f'http://export.arxiv.org/api/query?search_query=all:"{urllib.parse.quote(query)}"&start=0&max_results=3'
    try:
        response = urllib.request.urlopen(url)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        print(f"--- Arxiv results for: {query} ---")
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text
            authors = [a.find('{http://www.w3.org/2005/Atom}name').text for a in entry.findall('{http://www.w3.org/2005/Atom}author')]
            published = entry.find('{http://www.w3.org/2005/Atom}published').text
            doi_elem = entry.find('{http://arxiv.org/schemas/atom}doi')
            doi = doi_elem.text if doi_elem is not None else entry.find('{http://www.w3.org/2005/Atom}id').text
            print(f"Title: {title.strip()}, Authors: {authors}, Year: {published[:4]}, DOI/Link: {doi}")
    except Exception as e:
        print(e)

search_arxiv("ST-CVAE trajectory")
search_arxiv("Spatio-Temporal Conditional Variational Autoencoder trajectory")
search_arxiv("Spatio-Temporal Conditional Variational Autoencoder vehicle")
