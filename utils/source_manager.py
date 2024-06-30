import json
import os
import argparse
from typing import List, Optional, Dict

SOURCES_FILE = "sources.json"

def read_sources() -> Dict:
    if not os.path.exists(SOURCES_FILE):
        return {"global_keywords": [], "sources": []}
    with open(SOURCES_FILE, 'r') as file:
        return json.load(file)

def write_sources(data: Dict):
    with open(SOURCES_FILE, 'w') as file:
        json.dump(data, file, indent=2)

def print_sources():
    data = read_sources()
    print("Global Keywords:", ", ".join(data['global_keywords']))
    print("\nSources:")
    for source in data['sources']:
        print(f"  URL: {source['url']}")
        print(f"  Keywords: {', '.join(source['keywords'])}")
        print()

def update_sources(global_keywords: Optional[List[str]] = None, sources: Optional[List[Dict[str, List[str]]]] = None) -> Dict:
    data = read_sources()
    
    if global_keywords is not None:
        data['global_keywords'] = list(set(data['global_keywords'] + global_keywords))
    
    if sources is not None:
        for new_source in sources:
            existing_source = next((s for s in data['sources'] if s['url'] == new_source['url']), None)
            if existing_source:
                existing_source['keywords'] = list(set(existing_source['keywords'] + new_source['keywords']))
            else:
                data['sources'].append(new_source)
    
    write_sources(data)
    return data

def cli():
    parser = argparse.ArgumentParser(description="Manage sources and keywords for article fetching")
    parser.add_argument("--add-global", nargs="+", help="Add global keywords")
    parser.add_argument("--add-source", nargs=2, metavar=("URL", "KEYWORDS"), action="append", help="Add a source with keywords")
    parser.add_argument("--print", action="store_true", help="Print current sources and keywords")
    
    args = parser.parse_args()
    
    if args.print:
        print_sources()
    elif args.add_global or args.add_source:
        sources = [{"url": url, "keywords": keywords.split(",")} for url, keywords in args.add_source] if args.add_source else None
        update_sources(args.add_global, sources)
        print_sources()
    else:
        parser.print_help()

if __name__ == "__main__":
    cli()