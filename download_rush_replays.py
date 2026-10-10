"""Download CS2 match replays (GOTV demos) for the Rush game mode.

Scrapes your Steam "Personal Game Data" (GCPD) match history page, which is
the same place Steam's "Download GOTV Replay" links live, and saves each demo
as a decompressed .dem file.

Auth: copy the `steamLoginSecure` cookie from steamcommunity.com in your
browser (DevTools > Application > Cookies) and pass it via --cookie or the
STEAM_LOGIN_SECURE environment variable.

Usage:
    python download_rush_replays.py --list-tabs
    python download_rush_replays.py                       # auto-detects the Rush tab
    python download_rush_replays.py --tab matchhistoryrush --out demos
"""

import argparse
import bz2
import html
import os
import re
import sys
import time
from pathlib import Path

import requests

GCPD_URL = "https://steamcommunity.com/my/gcpd/730"
DEMO_LINK_RE = re.compile(r'href="(https?://replay\d+\.valve\.net/730/[^"]+\.dem\.bz2)"')
TAB_RE = re.compile(r'[?&]tab=(matchhistory[a-z0-9_]+)')
CONTINUE_TOKEN_RE = re.compile(r"g_sGcContinueToken\s*=\s*'([^']*)'")


def make_session(cookie: str) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (cs2-rush-replay-downloader)"
    s.cookies.set("steamLoginSecure", cookie, domain="steamcommunity.com")
    # Prime the session so Steam sets a sessionid cookie (needed for ajax paging).
    s.get("https://steamcommunity.com/", timeout=30)
    return s


def fetch_tab_page(s: requests.Session, tab: str) -> str:
    r = s.get(GCPD_URL, params={"tab": tab}, timeout=30)
    r.raise_for_status()
    if "g_steamID = false" in r.text or "/login/" in r.url:
        sys.exit("Not logged in: the steamLoginSecure cookie is missing or expired.")
    return r.text


def list_tabs(s: requests.Session) -> list[str]:
    page = fetch_tab_page(s, "matchhistorycompetitive")
    return sorted(set(TAB_RE.findall(page)))


def find_rush_tab(s: requests.Session) -> str:
    tabs = list_tabs(s)
    rush = [t for t in tabs if "rush" in t]
    if not rush:
        sys.exit(
            "No Rush match-history tab found on your GCPD page.\n"
            f"Tabs available: {', '.join(tabs) or '(none)'}\n"
            "Pass one explicitly with --tab if Rush is listed under a different name."
        )
    return rush[0]


def collect_demo_urls(s: requests.Session, tab: str, max_pages: int) -> list[str]:
    page = fetch_tab_page(s, tab)
    urls = DEMO_LINK_RE.findall(page)
    token_match = CONTINUE_TOKEN_RE.search(page)
    token = token_match.group(1) if token_match else None
    session_id = s.cookies.get("sessionid", domain="steamcommunity.com") or s.cookies.get("sessionid")

    pages = 1
    while token and pages < max_pages:
        r = s.get(
            GCPD_URL,
            params={"ajax": 1, "tab": tab, "continue_token": token, "sessionid": session_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            break
        urls += DEMO_LINK_RE.findall(data.get("html", ""))
        token = data.get("continue_token")
        pages += 1
        time.sleep(1)  # be polite to Steam

    # Preserve order, drop duplicates.
    return list(dict.fromkeys(html.unescape(u) for u in urls))


def download_demo(url: str, out_dir: Path) -> None:
    name = url.rsplit("/", 1)[-1].removesuffix(".bz2")
    dest = out_dir / name
    if dest.exists():
        print(f"  skip  {name} (already downloaded)")
        return

    tmp = dest.with_suffix(".dem.part")
    print(f"  get   {name}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            if r.status_code == 404:
                print("        expired on Valve's servers (demos are kept ~30 days)")
                return
            r.raise_for_status()
            decompressor = bz2.BZ2Decompressor()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(decompressor.decompress(chunk))
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cookie", default=os.environ.get("STEAM_LOGIN_SECURE"),
                   help="steamLoginSecure cookie value (or set STEAM_LOGIN_SECURE)")
    p.add_argument("--tab", help="GCPD tab to scrape (default: auto-detect the Rush tab)")
    p.add_argument("--out", default="rush_demos", help="output directory (default: rush_demos)")
    p.add_argument("--max-pages", type=int, default=20, help="max history pages to walk (default: 20)")
    p.add_argument("--list-tabs", action="store_true", help="print available match-history tabs and exit")
    args = p.parse_args()

    if not args.cookie:
        p.error("provide --cookie or set STEAM_LOGIN_SECURE")

    s = make_session(args.cookie)

    if args.list_tabs:
        for t in list_tabs(s):
            print(t)
        return

    tab = args.tab or find_rush_tab(s)
    print(f"Scanning tab: {tab}")
    urls = collect_demo_urls(s, tab, args.max_pages)
    if not urls:
        print("No downloadable replays found (none recorded, or all expired).")
        return

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(urls)} replay(s) -> {out_dir.resolve()}")
    for url in urls:
        download_demo(url, out_dir)


if __name__ == "__main__":
    main()
