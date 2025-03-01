from bs4 import BeautifulSoup


def remove_think_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(True):
        if tag.name == "think":
            tag.unwrap()
    return str(soup)
