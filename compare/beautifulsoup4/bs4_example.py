from bs4 import BeautifulSoup
import time

html_content = """
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Header 1</h1>
    <p class="content">This is a paragraph.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
        <li>Item 3</li>
    </ul>
    <div id="main">Main content</div>
</body>
</html>
"""

while True:
    soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.find('title').text
    header = soup.find('h1').text
    paragraph = soup.find('p', class_='content').text
    items = [li.text for li in soup.find_all('li')]
    main_div = soup.find('div', id='main').text

    print(f"Title: {title}", flush=True)
    print(f"Header: {header}", flush=True)
    print(f"Paragraph: {paragraph}", flush=True)
    print(f"List items: {items}", flush=True)
    print(f"Main div: {main_div}", flush=True)

    time.sleep(5)
