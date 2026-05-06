import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Tuple
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
    {"name": "ESG Today", "url": "https://www.esgtoday.com/"},
    {"name": "Carbon Herald", "url": "https://carbonherald.com/"},
    {"name": "The EV Report", "url": "https://theevreport.com/"},
]

INDUSTRY_TAGS = [
    "자동차", "철강", "조선", "IT", "반도체", "식음료", "기후테크·순환경제", "재생에너지", "배터리", "석유화학", "기타",
]

ISSUE_TAGS = [
    "정책", "규제", "공시", "소송", "투자", "M&A", "테크", "공급망", "평가·등급", "탄소시장", "금융", "그린워싱", "노동·인권", "생물다양성", "리스크", "실적·전략", "ESG DEAL", "기타",
]

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
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, timeout=15, headers=headers)
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

    # 중복 제거
    return list(dict.fromkeys(links))


def collect_from_rss(source_name: str, site_url: str, limit: int = 30) -> List[Article]:
    for feed_url in find_rss_links(site_url):
        feed = feedparser.parse(feed_url)
        if feed.entries:
            items = []
            for entry in feed.entries[:limit]:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                if title and link:
                    items.append(Article(source_name, title, link))
            if items:
                print(f"[RSS 성공] {source_name}: {feed_url}")
                return items
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

    # 링크 기준으로 중복 제거 + 개수 제한
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

    for src in SOURCES:
        source_name = src["name"]
        site_url = src["url"]

        items = collect_from_rss(source_name, site_url)
        if not items:
            print(f"[RSS 실패 -> HTML] {source_name}")
            try:
                items = collect_from_html(source_name, site_url)
            except Exception as e:
                print(f"[수집 실패] {source_name}: {e}")
                items = []

        for item in items:
            if item.link in seen_urls:
                continue
            seen_urls.add(item.link)

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
