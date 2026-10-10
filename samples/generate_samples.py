"""Regenerate the sample logs in this folder.

    uv run python samples/generate_samples.py

Output is deterministic (fixed random seed), so re-running it produces the
same files byte for byte. The main sample is one night of traffic for a small
web shop behind nginx in New York:

- 2025-11-01 22:00 to 2025-11-02 05:00 local time. Daylight saving ends at
  02:00, so the offset changes from -0400 to -0500 and 01:00-02:00 happens
  twice.
- The first 30 minutes were logged before $request_time was added to the
  log format.
- Browsers, bots, three health checkers, a vulnerability scanner, IPv6
  clients, conditional requests (304), redirects and a short burst of 502/503
  from the orders API around 02:45 EST.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
SEED = 20251102

START = datetime(2025, 11, 2, 2, 0, tzinfo=timezone.utc)
END = datetime(2025, 11, 2, 10, 0, tzinfo=timezone.utc)
DST_ENDS = datetime(2025, 11, 2, 6, 0, tzinfo=timezone.utc)
REQUEST_TIME_ADDED = datetime(2025, 11, 2, 2, 30, tzinfo=timezone.utc)
OUTAGE = (datetime(2025, 11, 2, 7, 38, tzinfo=timezone.utc), datetime(2025, 11, 2, 7, 53, tzinfo=timezone.utc))

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

BROWSERS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
]
# Some in-app browsers and SDKs put quotes in their user agent; they're
# written to the log as \".
QUOTED_AGENTS = [
    r'Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36 [FBAN/EMA;FBLC/en_GB;FBAV/\"425.0.0.12\"]',
    r'ShopApp/4.2.1 (iOS 18.0; \"iPhone15,2\") CFNetwork/1568 Darwin/24.0.0',
]
BOTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
]
TOOLS = ["curl/8.5.0", "python-requests/2.32.3"]
SCANNER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"

HEALTH_CHECKERS = ["10.0.4.11", "10.0.4.12", "10.0.4.13"]
SCANNER_IP = "185.220.101.47"


def client_ips(rng: random.Random) -> list[str]:
    ips = set()
    while len(ips) < 140:
        if rng.random() < 0.15:
            ips.add(f"2a02:c7c:{rng.randrange(0x10000):x}:{rng.randrange(0x10000):x}::{rng.randrange(1, 0xffff):x}")
        else:
            ips.add(f"{rng.choice([81, 86, 92, 98, 109, 151, 172, 203])}.{rng.randrange(256)}.{rng.randrange(256)}.{rng.randrange(1, 255)}")
    ips = sorted(ips)
    rng.shuffle(ips)
    return ips


def local_offset(when: datetime) -> timedelta:
    return timedelta(hours=-4) if when < DST_ENDS else timedelta(hours=-5)


def nginx_time(when: datetime) -> str:
    offset = local_offset(when)
    local = (when + offset).replace(tzinfo=None)
    minutes = int(offset.total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    hh, mm = divmod(abs(minutes), 60)
    return f"{local:%d}/{MONTHS[local.month - 1]}/{local:%Y:%H:%M:%S} {sign}{hh:02d}{mm:02d}"


def line(ip, when, request, status, size, referer, agent, request_time) -> str:
    text = f'{ip} - - [{nginx_time(when)}] "{request}" {status} {size} "{referer}" "{agent}"'
    if when >= REQUEST_TIME_ADDED:
        text += f" {request_time:.3f}"
    return text


def page_request(rng: random.Random, when: datetime) -> tuple[str, str, int, int, float]:
    """Returns (method, target, status, bytes, seconds) for a normal visitor."""
    r = rng.random()
    fast = rng.lognormvariate(-3.2, 0.6)  # median ~40 ms
    if r < 0.30:
        asset = rng.choice(["/static/app.js", "/static/css/site.css", "/static/img/logo.svg", "/favicon.ico"])
        if rng.random() < 0.55:
            return "GET", asset, 304, 0, fast / 4
        return "GET", asset, 200, rng.randrange(4_000, 180_000), fast / 2
    if r < 0.42:
        return "GET", "/", 200, rng.randrange(18_000, 24_000), fast
    if r < 0.58:
        pid = rng.randrange(100, 160)
        if rng.random() < 0.04:
            return "GET", f"/products/{pid + 900}", 404, 1_200, fast
        return "GET", f"/products/{pid}", 200, rng.randrange(25_000, 40_000), fast * 1.5
    if r < 0.66:
        term = rng.choice(["boots", "rain+jacket", "wool+socks", "gift+card", "scarf", "kids%27+wellies"])
        page = f"&page={rng.randrange(2, 5)}" if rng.random() < 0.3 else ""
        return "GET", f"/search?q={term}{page}", 200, rng.randrange(15_000, 30_000), fast * 3
    if r < 0.76:
        if rng.random() < 0.15:
            return "GET", "/api/v1/cart", 401, 90, fast / 3
        return rng.choice(["GET", "POST"]), "/api/v1/cart", 200, rng.randrange(300, 2_000), fast
    if r < 0.86:
        if OUTAGE[0] <= when < OUTAGE[1] and rng.random() < 0.6:
            return "POST", "/api/v1/orders", rng.choice([502, 502, 503]), 157, rng.uniform(5.0, 30.0)
        if rng.random() < 0.01:
            return "POST", "/api/v1/orders", 500, 210, fast * 4
        return "POST", "/api/v1/orders", 201, rng.randrange(600, 1_400), fast * 5
    if r < 0.88:
        return "GET", "/api/v1/orders/export?format=csv", 200, rng.randrange(80_000, 400_000), rng.uniform(1.2, 6.5)
    if r < 0.93:
        if rng.random() < 0.5:
            return "POST", "/login", 302, 0, fast * 2
        return "GET", "/login", 200, 7_400, fast
    if r < 0.96:
        return "GET", f"/blog/{rng.choice(['autumn-lookbook', 'care-guide-wool', 'store-opening'])}", 301, 162, fast / 2
    return "GET", rng.choice(["/robots.txt", "/sitemap.xml"]), 200, 640, fast / 2


def main_sample(rng: random.Random) -> list[str]:
    events: list[tuple[datetime, str]] = []
    ips = client_ips(rng)
    weights = [1 / (i + 1) ** 0.9 for i in range(len(ips))]

    # Health checkers: every 5 minutes, each on its own phase.
    for n, ip in enumerate(HEALTH_CHECKERS):
        when = START + timedelta(seconds=17 + 41 * n)
        while when < END:
            events.append((when, line(ip, when, "GET /health HTTP/1.1", 200, 15, "-", "kube-probe/1.31", 0.001)))
            when += timedelta(minutes=5)

    # Visitors: busier at the start of the night.
    when = START
    while when < END:
        hours_in = (when - START).total_seconds() / 3600
        when += timedelta(seconds=rng.expovariate(1 / (4 + 2 * hours_in)))
        if when >= END:
            break
        ip = rng.choices(ips, weights)[0]
        roll = rng.random()
        if roll < 0.08:
            agent = rng.choice(BOTS)
        elif roll < 0.11:
            agent = rng.choice(QUOTED_AGENTS)
        elif roll < 0.13:
            agent = rng.choice(TOOLS)
        else:
            agent = BROWSERS[ips.index(ip) % len(BROWSERS)]
        method, target, status, size, seconds = page_request(rng, when)
        referer = "https://shop.example.com/" if rng.random() < 0.6 and "bot" not in agent else "-"
        request = f"{method} {target} HTTP/{rng.choice(['1.1', '1.1', '2.0'])}"
        events.append((when, line(ip, when, request, status, size, referer, agent, seconds)))
        # Shoppers whose order failed press the button again.
        retry_at = when
        while status >= 500 and rng.random() < 0.8:
            retry_at += timedelta(seconds=seconds + rng.uniform(2, 10))
            status = rng.choice([502, 503]) if OUTAGE[0] <= retry_at < OUTAGE[1] else 201
            seconds = rng.uniform(5.0, 30.0) if status >= 500 else rng.lognormvariate(-1.6, 0.5)
            events.append((retry_at, line(ip, retry_at, request, status, 157 if status >= 500 else 980, referer, agent, seconds)))

    # A scanner, around 03:10 local (after the clocks went back).
    when = datetime(2025, 11, 2, 8, 10, 3, tzinfo=timezone.utc)
    probes = ["/wp-login.php", "/.env", "/.git/config", "/phpmyadmin/", "/admin.php", "/xmlrpc.php"]
    probes += ["/static/" + "../" * depth + "etc/passwd" for depth in range(4, 17, 2)]
    probes += ["/static/" + "..%2f" * 8 + "etc/passwd"]
    for target in probes * 3:
        when += timedelta(seconds=rng.uniform(0.2, 1.5))
        status = 400 if "../" in target else 404
        events.append((when, line(SCANNER_IP, when, f"GET {target} HTTP/1.1", status, 162, "-", SCANNER_AGENT, rng.uniform(0.0, 0.002))))
    events.append((when, line(SCANNER_IP, when, r"\x16\x03\x01\x00\xF1\x01\x00\x00\xED\x03\x03", 400, 166, "-", "-", 0.0)))

    events.sort(key=lambda e: e[0])
    return [text for _, text in events]


EDGE_CASES = r"""
192.0.2.10 - - [02/Nov/2025:01:59:58 -0400] "GET / HTTP/1.1" 200 20311 "-" "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0" 0.041
192.0.2.10 - - [02/Nov/2025:01:00:03 -0500] "GET /products/101 HTTP/1.1" 200 31877 "https://shop.example.com/" "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0" 0.088
2001:db8:85a3::8a2e:370:7334 - - [02/Nov/2025:01:05:12 -0500] "GET /search?q=boots HTTP/2.0" 200 18220 "-" "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1" 0.130
::1 - - [02/Nov/2025:01:05:30 -0500] "GET /health HTTP/1.1" 200 15 "-" "kube-probe/1.31" 0.001
198.51.100.7 - - [02/Nov/2025:01:06:00 -0500] "GET /api/v1/cart HTTP/1.1" 200 812 "-" "ShopApp/4.2.1 (iOS 18.0; \"iPhone15,2\") CFNetwork/1568 Darwin/24.0.0" 0.052
198.51.100.7 - alice [02/Nov/2025:01:06:02 -0500] "POST /api/v1/orders HTTP/1.1" 201 1040 "-" "ShopApp/4.2.1 (iOS 18.0; \"iPhone15,2\") CFNetwork/1568 Darwin/24.0.0" 0.310
203.0.113.50 - - [02/Nov/2025:11:36:10 +0530] "GET /static/app.js HTTP/1.1" 304 0 "https://shop.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" 0.002
203.0.113.50 - - [02/Nov/2025:11:36:11 +0530] "GET /static/css/site.css HTTP/1.1" 304 0 "https://shop.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" 0.001
203.0.113.51 - - [02/Nov/2025:06:07:40 +0000] "GET /blog/store-opening HTTP/1.1" 301 162 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" 0.003
203.0.113.52 - - [02/Nov/2025:01:08:00 -0500] "GET /api/v1/orders/export?format=csv HTTP/1.1" 200 254001 "-" "curl/8.5.0" 4.812
203.0.113.53 - - [02/Nov/2025:01:08:30 -0500] "POST /api/v1/orders HTTP/1.1" 502 157 "-" "python-requests/2.32.3" 30.001
203.0.113.54 - - [02/Nov/2025:01:09:00 -0500] "GET /products/999 HTTP/1.1" 404 1200 "-" "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
185.220.101.47 - - [02/Nov/2025:01:09:30 -0500] "\x16\x03\x01\x00\xF1\x01\x00\x00\xED\x03\x03" 400 166 "-" "-" 0.000
185.220.101.47 - - [02/Nov/2025:01:09:31 -0500] "GET /static/../../../../../../etc/passwd HTTP/1.1" 400 162 "-" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36" 0.000

this line is not an access log line
"""


def main() -> None:
    rng = random.Random(SEED)
    access = main_sample(rng)
    (HERE / "access.log").write_text("\n".join(access) + "\n", encoding="utf-8", newline="\n")
    (HERE / "edge-cases.log").write_text(EDGE_CASES.lstrip("\n"), encoding="utf-8", newline="\n")
    print(f"wrote {len(access)} lines to samples/access.log and samples/edge-cases.log")


if __name__ == "__main__":
    main()
