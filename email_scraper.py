import requests
import os
from bs4 import BeautifulSoup
import re
import csv
from urllib.parse import urljoin, urlparse
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Regular expression to match email addresses.
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

def crawl(url, visited, results, max_depth, current_depth=0):
    """
    Recursively crawl the given URL up to max_depth.
    
    Parameters:
      - url: The URL to crawl.
      - visited: A set of URLs already visited (to avoid repeats).
      - results: A dictionary mapping URLs to a list of emails found on that page.
      - max_depth: How deep to crawl.
      - current_depth: The current recursion depth.
    """
    if current_depth > max_depth:
        return
    if url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url, timeout=10)
        # Check that the response is HTML.
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return
        html = response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return

    # # Find email addresses using the regex.
    # emails1 = set(EMAIL_REGEX.findall(html))
    # results[url] = list(emails1)
    # print(emails1)

    # Parse the HTML and look for emails using gemini-flash from google deepmind    .
    client = genai.Client(api_key="AIzaSyAPmMlj1ENmRahSSX-zFyKXA64PvC05mZQ")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            "Find and return all email addresses from the following HTML. Do not return a script that does this, just return the email addresses. If no email addresses are found, return an empty list:\n\n",
            html
        ]
    )

    emails = response.text
    print(emails)
    results[url] = list(emails)

    # Parse the HTML and look for hyperlinks.
    soup = BeautifulSoup(html, 'html.parser')
    for link in soup.find_all('a', href=True):
        next_url = urljoin(url, link['href'])
        # Filter only http(s) URLs.
        parsed = urlparse(next_url)
        if parsed.scheme not in ['http', 'https']:
            continue
        # Remove URL fragments (anything after a #)
        next_url = next_url.split('#')[0]
        if next_url not in visited:
            crawl(next_url, visited, results, max_depth, current_depth + 1)

def main():
    # Get a comma-separated list of seed URLs from the user.
    seed_input = input("Enter seed URLs (separated by commas): ")
    seed_urls = [url.strip() for url in seed_input.split(',') if url.strip()]

    # Ask for a maximum crawl depth (default to 2 if invalid input).
    depth_input = input("Enter maximum crawl depth (default is 2): ")
    try:
        max_depth = int(depth_input)
    except ValueError:
        max_depth = 2

    visited = set()
    results = {}

    # Start crawling from each seed URL.
    for seed in seed_urls:
        print(f"Crawling {seed} ...")
        crawl(seed, visited, results, max_depth)

    # Write results to a CSV file.
    csv_filename = 'emails_scraped.csv'
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Emails']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for url, emails in results.items():
                # Flatten the list of emails so that all entries are strings.
                flattened_emails = []
                for email in emails:
                    if isinstance(email, str):
                        flattened_emails.append(email)
                    elif isinstance(email, tuple):
                        # Extend the list with any strings found in the tuple.
                        flattened_emails.extend([item for item in email if isinstance(item, str)])
                writer.writerow({'URL': url, 'Emails': ", ".join(flattened_emails)})
        print(f"Scraping complete. Results saved in {csv_filename}")
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    main()
