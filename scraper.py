import datetime as dt
from dataclasses import dataclass
from typing import List, Dict
from urllib.parse import urljoin

try:
    import feedparser
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("필요한 패키지가 설치되지 않았습니다. 먼저 pip install -r requirements.txt를 실행하세요.")
    raise

SOURCES = [
    {
        "name": "ESG Today",
        "url": "https://www.esgtoday.com/",
        "rss_urls": ["https://www.esgtoday.com/feed/"],
    },
    {
        "name": "Carbon Herald",
        "url": "https://carbonherald.com/",
        "rss_urls": ["https://carbonherald.com/feed/"],
    },
    {
        "name": "The EV Report",
        "url": "https://theevreport.com/",
        "rss_urls": ["https://theevreport.com/feed/"],
    },
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

INDUSTRY_RULES: Dict[str, List[str]] = {
    "자동차": ["ev", "electric vehicle", "automotive", "car", "tesla", "hyundai", "kia", "ford", "gm", "toyota"],
    "철강": ["steel", "posco", "arcelormittal"],
    "조선": ["ship", "shipping", "shipbuilding", "vessel"],
    "IT": ["software", "cloud", "ai", "microsoft", "google", "amazon", "apple"],
    "반도체": ["semiconductor", "chip", "tsmc", "nvidia", "intel", "memory"],
    "식음료": ["food", "beverage", "coca-cola", "nestle", "drink"],
    "기후테크·순환경제": ["recycling", "circular", "climate tech", "capture", "ccus", "waste"],
    "재생에너지": ["renewable", "solar", "wind", "hydrogen", "clean energy"],
    "배터리": ["battery", "lithium", "cathode", "anode"],
    "석유화학": ["oil", "gas", "petrochemical", "refinery", "lng"],
}

ISSUE_RULES: Dict[str, List[str]] = {
    "정책": ["policy", "plan", "roadmap", "initiative"],
    "규제": ["regulation", "rule", "compliance", "ban", "standard"],
    "공시": ["disclosure", "reporting", "filing", "scope 3"],
    "소송": ["lawsuit", "sue", "court", "litigation", "settlement"],
    "투자": ["invest", "investment", "funding", "financing", "raises"],
    "M&A": ["acquire", "acquisition", "merger", "buyout", "deal"],
    "테크": ["technology", "tech", "platform", "ai", "software"],
    "공급망": ["supply chain", "supplier", "procurement", "sourcing"],
    "평가·등급": ["rating", "score", "rank", "assessment", "benchmark"],
    "탄소시장": ["carbon market", "carbon credit", "offset", "ets"],
    "금융": ["bank", "loan", "bond", "asset manager", "finance"],
    "그린워싱": ["greenwashing", "misleading", "false claim"],
    "노동·인권": ["labor", "human rights", "worker", "wage"],
    "생물다양성": ["biodiversity", "nature", "forest", "deforestation"],
    "리스크": ["risk", "exposure", "uncertainty"],
    "실적·전략": ["earnings", "guidance", "strategy", "target", "outlook"],
    "ESG DEAL": ["esg deal", "sustainability-linked", "slb", "ppa"],
}


@dataclass
class Article:
    source: str
    title: str
    link: str


def get_html(url: str) -> str:
    r = requests.get(url, timeout=15, headers=BROWSER_HEADERS)
    r.raise_for_status()
    return r.text


def find_rss_links(site_url: str) -> List[str]:
    links = []
    try:
        html = get_html(site_url)
    except Exception:
        return links

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("link", type="application/rss+xml"):
        href = tag.get("href")
        if href:
            links.append(urljoin(site_url, href))
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "rss" in href.lower() or "feed" in href.lower():
            links.append(urljoin(site_url, href))
    return list(dict.fromkeys(links))


def collect_from_rss(source_name: str, site_url: str, preset_rss_urls: List[str], limit: int = 30) -> List[Article]:
    candidate_feeds = list(dict.fromkeys(preset_rss_urls + find_rss_links(site_url)))

    for feed_url in candidate_feeds:
        try:
            feed = feedparser.parse(feed_url, request_headers=BROWSER_HEADERS)
            entries = getattr(feed, "entries", [])
            if not entries:
                continue

            items = []
            for entry in entries[:limit]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                if title and link:
                    items.append(Article(source_name, title, link))
            if items:
                print(f"[RSS 성공] {source_name}: {feed_url} ({len(items)}건)")
                return items
        except Exception as e:
            print(f"[RSS 실패] {source_name}: {feed_url} ({e})")
    return []


def collect_from_html(source_name: str, site_url: str, limit: int = 30) -> List[Article]:
    html = get_html(site_url)
    soup = BeautifulSoup(html, "html.parser")

    articles: List[Article] = []
    for a in soup.select("article a[href], h2 a[href], h3 a[href], .post a[href]"):
        title = a.get_text(" ", strip=True)
        link = urljoin(site_url, a.get("href", ""))

        if not title or len(title) < 8:
            continue
        if not link.startswith("http"):
            continue
        articles.append(Article(source_name, title, link))

    unique = {}
    for item in articles:
        unique[item.link] = item
    return list(unique.values())[:limit]


def classify(title: str, rules: Dict[str, List[str]], default_tag: str = "기타") -> str:
    t = title.lower()
    for tag, keywords in rules.items():
        if any(k in t for k in keywords):
            return tag
    return default_tag


def collect_all() -> List[Dict[str, str]]:
    today = dt.date.today().isoformat()
    rows = []
    seen_urls = set()
    failed_sources = []

    for src in SOURCES:
        source_name = src["name"]
        site_url = src["url"]
        rss_urls = src.get("rss_urls", [])

        items = collect_from_rss(source_name, site_url, rss_urls)
        method = "RSS"

        if not items:
            print(f"[RSS 실패 -> HTML 시도] {source_name}")
            method = "HTML"
            try:
                items = collect_from_html(source_name, site_url)
            except Exception as e:
                print(f"[수집 실패] {source_name}: {e}")
                items = []

        if not items:
            failed_sources.append(source_name)
            print(f"[완전 실패] {source_name}: 0건")
            continue

        added_count = 0
        for item in items:
            if item.link in seen_urls:
                continue
            seen_urls.add(item.link)
            added_count += 1
            rows.append(
                {
                    "날짜": today,
                    "매체명": item.source,
                    "기사명": item.title,
                    "링크": item.link,
                    "산업태그": classify(item.title, INDUSTRY_RULES),
                    "이슈태그": classify(item.title, ISSUE_RULES),
                    "담당자": "",
                    "비고": "",
                }
            )

        print(f"[수집 완료] {source_name}: {added_count}건 (방법: {method})")

    print("\n===== 수집 요약 =====")
    print(f"성공 기사 총 {len(rows)}건")
    if failed_sources:
        print("실패 매체: " + ", ".join(failed_sources))
    else:
        print("실패 매체: 없음")

    return rows


def save_excel(rows: List[Dict[str, str]]) -> str:
    date_str = dt.date.today().strftime("%Y%m%d")
    filename = f"mawari_{date_str}.xlsx"
    columns = ["날짜", "매체명", "기사명", "링크", "산업태그", "이슈태그", "담당자", "비고"]
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(filename, index=False)
    return filename


if __name__ == "__main__":
    results = collect_all()
    out_file = save_excel(results)
    print(f"완료: {out_file} (총 {len(results)}건)")
