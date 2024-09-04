import trafilatura

link = input("Please enter a valid url: ")
result = trafilatura.extract(url=link, favor_precision=True, include_comments=False)
print(result)
