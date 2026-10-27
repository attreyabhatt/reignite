"""Read-only audit of Search Console exclusion CSV/ZIP exports.

python scripts/seo_audit.py --crawled export.zip --discovered export2.zip --output .seo-audit/indexing.csv
Only TryAgainText public URLs are fetched. No indexing requests are submitted.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from zipfile import ZipFile

import requests


ORIGIN = "https://www.tryagaintext.com"


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonical = ""
        self.robots = []
        self.links = set()
        self.h1 = 0
        self.ignore = 0
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.ignore += 1
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href", "")
        if tag == "meta" and attrs.get("name", "").lower() in {"robots", "googlebot"}:
            self.robots.append(attrs.get("content", ""))
        if tag == "a" and attrs.get("href"):
            self.links.add(urlsplit(attrs["href"]).path)
        if tag == "h1":
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore - 1)

    def handle_data(self, data):
        if not self.ignore:
            self.text.append(data)


def read_export(path):
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            text = archive.read("Table.csv").decode("utf-8-sig")
    else:
        text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text)))


def fetch(url):
    parsed = urlsplit(url)
    if parsed.hostname not in {"tryagaintext.com", "www.tryagaintext.com"} or parsed.scheme not in {"https", "http"}:
        raise ValueError("Export contains an unrelated URL")
    try:
        response = requests.get(url, timeout=(5, 20), headers={"User-Agent": "TryAgainText-SEO-Review/1.0"})
        return response, Page(response.text)
    except requests.RequestException:
        return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crawled", type=Path, required=True)
    parser.add_argument("--discovered", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [{"reason": reason, **row} for reason, source in (
        ("crawled_not_indexed", args.crawled), ("discovered_not_indexed", args.discovered)) for row in read_export(source)]
    urls = [row["URL"] for row in rows]
    category_urls = {ORIGIN + "/".join(urlsplit(url).path.split("/")[:3]) + "/"
                     for url in urls if urlsplit(url).path.startswith("/pickup-lines/")}
    navigation = sorted(category_urls | {ORIGIN + "/", ORIGIN + "/pickup-lines/", ORIGIN + "/situations/"})
    with ThreadPoolExecutor(max_workers=4) as pool:
        nav_pages = list(pool.map(fetch, navigation))
        fetched = list(pool.map(fetch, urls))
    robots = RobotFileParser()
    robots.parse(requests.get(ORIGIN + "/robots.txt", timeout=20).text.splitlines())
    result = []
    for row, (response, page) in zip(rows, fetched):
        path = urlsplit(row["URL"]).path
        incoming = sum(bool(parsed and path in parsed.links) for _, parsed in nav_pages)
        item = {"reason": row["reason"], "original_url": row["URL"], "path": path,
                "last_crawled": row.get("Last crawled", ""), "navigation_incoming_links": incoming}
        if response is None:
            item.update(status="fetch_error", recommendation="Retry fetch before deciding")
        else:
            blocked = not robots.can_fetch("Googlebot", row["URL"])
            noindex = "noindex" in ",".join(page.robots + [response.headers.get("X-Robots-Tag", "")]).lower()
            item.update(status=response.history[0].status_code if response.history else response.status_code,
                        final_status=response.status_code, final_url=response.url, canonical=page.canonical,
                        robots_blocked=blocked, noindex=noindex, h1_count=page.h1,
                        visible_word_count=len(re.findall(r"\b\w+\b", " ".join(page.text))))
            if path in {"/robots.txt", "/sitemap.xml"} and response.status_code == 200:
                recommendation = "Discovery endpoint; indexing as a page is not required"
            elif response.status_code != 200 or blocked or noindex or page.canonical != ORIGIN + path:
                recommendation = "Review response, canonical or indexing directive"
            elif response.history and urlsplit(row["URL"]).hostname != "www.tryagaintext.com":
                recommendation = "Historical hostname; canonical destination is fetchable"
            else:
                recommendation = "No fetch/indexability blocker found; review usefulness and search selection"
            item["recommendation"] = recommendation
        result.append(item)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(key for row in result for key in row))
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(result)
    from collections import Counter
    print({"exported_urls": len(result), "canonical_paths": len({r['path'] for r in result}),
           "recommendations": dict(Counter(r['recommendation'] for r in result)), "output": str(args.output)})


if __name__ == "__main__":
    main()
