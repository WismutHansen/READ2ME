import requests
import logging
import json
from urllib.parse import quote

def encode_search_query(query):
    base_url = "https://s.jina.ai/"
    encoded_query = quote(query)
    return f"{base_url}{encoded_query}"

# Function to search the web using Jina
def search_with_jina(search_term: str) -> str:
    search_url = encode_search_query(search_term)
    try:
        headers = {
             "Accept":"application/json",
             "X-With-Links-Summary": "true"
        }
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            logging.error(
                f"Jina search failed with status code: {response.status_code}"
            )
            return None
    except Exception as e:
        logging.error(f"Error searching with Jina: {e}")
        return None

def save_to_json(data: str, filename: str) -> None:
    try:
        parsed_data = json.loads(data)
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(parsed_data, json_file, indent=4)
        logging.info(f"Data successfully saved to {filename}")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON: {e}")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")

if __name__ == "__main__":
    query = input("Enter the search term to search: ")
    result = search_with_jina(query)
    if result:
        print(result)
        save_to_json(result, "search_results.json")
