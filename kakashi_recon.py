#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║        KAKASHI RECON - Web Reconnaissance Tool               ║
║               Recon Like A Bug Hunter                        ║
║                Built with Python 3                           ║
╚══════════════════════════════════════════════════════════════╝

Modules:
  1.  Wayback Machine Recon        (old URLs, robots.txt)
  2.  Subdomain Discovery          (crt.sh, HackerTarget, AlienVault)
  3.  IP Range Lookup              (ARIN WHOIS)
  4.  JS Endpoint Extraction       (spider + regex)
  5.  S3 Bucket Finder             (AWS bucket enumeration)
  6.  GitHub Recon                 (search dorks)
  7.  Technology Detection         (headers, HTML fingerprinting)
  8.  Content Discovery            (Google dorks)
  9.  Quick Wins                   (.git, .env, phpinfo, backups...)
  10. DNS Records Mapper           (A/AAAA/MX/TXT/NS/CNAME/SOA)
  11. Zone Transfer Check          (AXFR test against nameservers)
  12. Subdomain Takeover Scanner   (dangling CNAME fingerprints)
  13. URL Parameter Extractor      (param harvesting + risk flagging)
  14. JS Secrets Scanner           (API keys, tokens, credentials)
  15. API & Swagger Finder         (REST/GraphQL/OpenAPI discovery)
  16. CORS Tester                  (wildcard, reflected-origin, credentials)
  17. TLS/SSL Inspector            (cert expiry, cipher, HSTS)
  18. Cookie Security Checker      (Secure/HttpOnly/SameSite flags)
  19. HTTP Method Analyzer         (PUT/DELETE/TRACE/OPTIONS)
  20. Open Redirect & SSRF Hints   (parameter-based vulnerability hints)
"""

import argparse
import sys
import os
import re
import json
import socket
import time
import concurrent.futures
from datetime import datetime
from urllib.parse import urlparse, urljoin, quote

# ── Dependency check ─────────────────────────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
    from colorama import Fore, Back, Style, init
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    init(autoreset=True)
except ImportError as e:
    print(f"\n[!] Missing dependency: {e}")
    print("[*] Install with:  pip install -r requirements.txt\n")
    sys.exit(1)

# ── Banner ────────────────────────────────────────────────────────────────────
BANNER = """
\033[92m ██╗  ██╗ █████╗ ██╗  ██╗ █████╗ ███████╗██╗  ██╗██╗
 ██║ ██╔╝██╔══██╗██║ ██╔╝██╔══██╗██╔════╝██║  ██║██║
 █████╔╝ ███████║█████╔╝ ███████║███████╗███████║██║
 ██╔═██╗ ██╔══██║██╔═██╗ ██╔══██║╚════██║██╔══██║██║
 ██║  ██╗██║  ██║██║  ██╗██║  ██║███████║██║  ██║██║
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝
      ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
      ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║
      ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║
      ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║
      ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
      ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝╚═╝  ╚═══╝
\033[33m                  Recon Like A Bug Hunter  |  Tool built with Python 3\033[0m
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 12


def info(msg):   print(f"\033[94m[*]\033[0m {msg}")
def good(msg):   print(f"\033[92m[+]\033[0m {msg}")
def warn(msg):   print(f"\033[93m[!]\033[0m {msg}")
def bad(msg):    print(f"\033[91m[-]\033[0m {msg}")
def juicy(msg):  print(f"\033[91m[⚠]\033[0m \033[1m{msg}\033[0m")
def link(msg):   print(f"    \033[90m→\033[0m {msg}")


def section(title):
    width = 64
    border = "═" * width
    pad = (width - len(title) - 2) // 2
    print(f"\n\033[1;36m╔{border}╗")
    print(f"║{' ' * pad} {title} {' ' * (width - pad - len(title) - 1)}║")
    print(f"╚{border}╝\033[0m\n")


# ── Report Manager ────────────────────────────────────────────────────────────
class ReconReport:
    def __init__(self, domain, output_dir):
        self.domain = domain
        self.output_dir = output_dir
        self.data = {
            "target":           domain,
            "scan_time":        datetime.now().isoformat(),
            "wayback_urls":     [],
            "subdomains":       [],
            "ip_info":          {},
            "js_endpoints":     [],
            "s3_buckets":       [],
            "google_dorks":     [],
            "github_dorks":     [],
            "technologies":        {},
            "content_discovery":  [],
            "quick_wins":         [],
            # ── New modules ────────────────────────────────────────
            "dns_records":        {},
            "zone_transfer":      {},
            "subdomain_takeover": [],
            "parameters":         {},
            "js_secrets":         [],
            "api_endpoints":      [],
            "cors":               [],
            "tls":                {},
            "cookies":            [],
            "http_methods":       [],
            "redirect_ssrf":      [],
        }
        os.makedirs(output_dir, exist_ok=True)

    def save(self):
        path = os.path.join(self.output_dir, f"{self.domain}_report.json")
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)
        good(f"Full JSON report → {path}")

    def save_list(self, name, items):
        if not items:
            return
        path = os.path.join(self.output_dir, f"{self.domain}_{name}.txt")
        with open(path, "w") as f:
            f.write("\n".join(str(i) for i in items))
        info(f"  Saved {len(items)} items → {path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 1 — Wayback Machine Recon
# ═══════════════════════════════════════════════════════════════════════════════
def wayback_recon(domain, report):
    section("MODULE 1 │ WAYBACK MACHINE RECON")

    # ── Fetch archived URLs ──────────────────────────────────────────────────
    info(f"Querying Wayback CDX API for *.{domain} ...")
    cdx_url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url=*.{domain}/*&output=text&fl=original&collapse=urlkey&limit=1000"
    )
    urls = []
    try:
        r = requests.get(cdx_url, headers=HEADERS, timeout=25)
        urls = sorted(set(r.text.strip().splitlines()))
        good(f"Found {len(urls)} archived URLs")
        for u in urls[:15]:
            print(f"  {u}")
        if len(urls) > 15:
            info(f"  ... and {len(urls) - 15} more (see output file)")
        report.data["wayback_urls"] = urls
        report.save_list("wayback_urls", urls)
    except Exception as e:
        bad(f"Wayback CDX error: {e}")

    # ── Highlight juicy file extensions ─────────────────────────────────────
    juicy_ext = re.compile(
        r'\.(php|asp|aspx|txt|log|bak|sql|env|conf|config|key|pem|'
        r'json|xml|yaml|yml|backup|rar|zip|tar|gz|7z|old|orig|save)(\?|$)',
        re.I
    )
    found_juicy = [u for u in urls if juicy_ext.search(u)]
    if found_juicy:
        warn(f"Potentially interesting archived files ({len(found_juicy)}):")
        for j in found_juicy[:20]:
            print(f"  \033[93m{j}\033[0m")
        report.save_list("wayback_juicy", found_juicy)

    # ── Fetch archived robots.txt snapshots ─────────────────────────────────
    info("Fetching archived robots.txt entries ...")
    robots_api = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url={domain}/robots.txt&output=json&fl=timestamp,original&limit=5"
    )
    try:
        r = requests.get(robots_api, headers=HEADERS, timeout=10)
        rows = r.json()
        for row in rows[1:]:
            ts, orig = row
            link(f"https://web.archive.org/web/{ts}/{orig}")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 2 — Subdomain Discovery
# ═══════════════════════════════════════════════════════════════════════════════
def _crtsh(domain):
    subs = set()
    try:
        r = requests.get(
            f"https://crt.sh/?q=%25.{domain}&output=json",
            headers=HEADERS, timeout=18
        )
        for entry in r.json():
            for name in entry.get("name_value", "").splitlines():
                name = name.strip().lstrip("*.")
                if name.endswith(domain):
                    subs.add(name)
    except Exception as e:
        warn(f"crt.sh: {e}")
    return subs


def _hackertarget(domain):
    subs = set()
    try:
        r = requests.get(
            f"https://api.hackertarget.com/hostsearch/?q={domain}",
            headers=HEADERS, timeout=15
        )
        for line in r.text.splitlines():
            parts = line.split(",")
            if parts and parts[0].endswith(domain):
                subs.add(parts[0].strip())
    except Exception as e:
        warn(f"HackerTarget: {e}")
    return subs


def _alienvault(domain):
    subs = set()
    try:
        r = requests.get(
            f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns",
            headers=HEADERS, timeout=15
        )
        for entry in r.json().get("passive_dns", []):
            h = entry.get("hostname", "")
            if h.endswith(domain):
                subs.add(h)
    except Exception as e:
        warn(f"AlienVault: {e}")
    return subs


def _resolve(sub):
    try:
        ip = socket.gethostbyname(sub)
        return (sub, ip)
    except Exception:
        return None


def subdomain_discovery(domain, report):
    section("MODULE 2 │ SUBDOMAIN DISCOVERY")
    all_subs = set()

    info("Source 1/3 — crt.sh (Certificate Transparency) ...")
    s = _crtsh(domain);      good(f"crt.sh      → {len(s)} entries"); all_subs |= s

    info("Source 2/3 — HackerTarget ...")
    s = _hackertarget(domain); good(f"HackerTarget → {len(s)} entries"); all_subs |= s

    info("Source 3/3 — AlienVault OTX ...")
    s = _alienvault(domain);   good(f"AlienVault   → {len(s)} entries"); all_subs |= s

    info(f"Total unique subdomains (before DNS): {len(all_subs)}")

    # ── DNS resolution ───────────────────────────────────────────────────────
    info("Resolving subdomains via DNS ...")
    live = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        futs = {ex.submit(_resolve, s): s for s in all_subs}
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            if res:
                live[res[0]] = res[1]

    good(f"Live / resolvable subdomains: {len(live)}")
    for sub, ip in sorted(live.items()):
        print(f"  \033[92m{sub:<45}\033[0m {ip}")

    report.data["subdomains"] = [{"host": k, "ip": v} for k, v in live.items()]
    report.save_list("subdomains", sorted(live.keys()))

    # ── Online resources for deeper recon ────────────────────────────────────
    info("Online resources for deeper subdomain recon:")
    link(f"https://crt.sh/?q=%25.{domain}")
    link(f"https://dnsdumpster.com/  (search: {domain})")
    link(f"https://www.virustotal.com/gui/domain/{domain}/relations")
    link(f"https://searchdns.netcraft.com/?restriction=site+ends+with&host={domain}")
    link(f"https://www.yougetsignal.com/tools/web-sites-on-web-server/  (reverse IP)")

    info("Google Dork for subdomains:")
    print(f"  site:{domain} -site:www.{domain}")

    info("Tool suggestions (run on Linux/Kali):")
    print(f"  python3 sublist3r.py -d {domain}")
    print(f"  ./knockpy {domain}")
    print(f"  ./subbrute.py {domain}")
    print(f"  ./altdns.py -i subdomains.txt -o altdns_output -w words.txt -r -s resolved.txt")

    return live


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 3 — IP Range & WHOIS
# ═══════════════════════════════════════════════════════════════════════════════
def ip_range_lookup(domain, report):
    section("MODULE 3 │ IP RANGE & WHOIS (ARIN)")
    try:
        ip = socket.gethostbyname(domain)
        good(f"Resolved IP: {ip}")

        r = requests.get(
            f"https://rdap.arin.net/registry/ip/{ip}",
            headers=HEADERS, timeout=12
        )
        data = r.json()
        net_name = data.get("name", "N/A")
        start    = data.get("startAddress", "N/A")
        end      = data.get("endAddress",   "N/A")
        handle   = data.get("handle",       "N/A")

        good(f"Network Name : {net_name}")
        good(f"Handle       : {handle}")
        good(f"IP Range     : {start}  →  {end}")

        report.data["ip_info"] = {
            "ip": ip, "net_name": net_name,
            "handle": handle, "range_start": start, "range_end": end
        }

        info("Manual links:")
        link(f"https://whois.arin.net/rest/ip/{ip}")
        link(f"https://www.yougetsignal.com/tools/web-sites-on-web-server/  (IP: {ip})")

        warn("Tip: Scan the IP range for phpinfo.php, backup.rar, etc. (authorized targets only)")
        print(f"  Bash: for ip in {{start..end}}; do wget -q http://$ip/phpinfo.php; done")

    except Exception as e:
        bad(f"IP lookup failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 4 — JS Endpoint Extraction
# ═══════════════════════════════════════════════════════════════════════════════
_JS_PATTERNS = [
    r'["\'](/api/[^\s"\'<>{}]+)["\']',
    r'["\'](/v\d+/[^\s"\'<>{}]+)["\']',
    r'url\s*[:=]\s*["\']([^"\']+)["\']',
    r'endpoint\s*[:=]\s*["\']([^"\']+)["\']',
    r'path\s*[:=]\s*["\']([/][^"\']+)["\']',
    r'(https?://[a-zA-Z0-9._/\-?=&#%+:@]+)',
    r'["\']((?:/[a-zA-Z0-9_\-]+){2,}(?:\.\w+)?)["\']',
]


def _extract_endpoints_from_js(js_url):
    found = set()
    try:
        r = requests.get(js_url, headers=HEADERS, timeout=10, verify=False)
        for pat in _JS_PATTERNS:
            for m in re.findall(pat, r.text):
                if len(m) > 2 and "//cdn" not in m and "//fonts" not in m:
                    found.add(m)
    except Exception:
        pass
    return found


def js_endpoint_discovery(domain, report):
    section("MODULE 4 │ JS ENDPOINT EXTRACTION")
    base_url = f"https://{domain}"
    js_files = set()

    # ── Crawl homepage ───────────────────────────────────────────────────────
    info(f"Crawling {base_url} for <script src=...> tags ...")
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=12, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup.find_all("script", src=True):
            src = tag["src"]
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            if ".js" in src:
                js_files.add(src)
        good(f"JS files found on homepage: {len(js_files)}")
    except Exception as e:
        bad(f"Crawl error: {e}")

    # ── Get more JS from Wayback ─────────────────────────────────────────────
    info("Fetching JS URLs from Wayback Machine ...")
    try:
        r = requests.get(
            f"http://web.archive.org/cdx/search/cdx"
            f"?url=*.{domain}/*.js&output=text&fl=original&collapse=urlkey&limit=60",
            timeout=18
        )
        for u in r.text.strip().splitlines():
            js_files.add(u)
    except Exception:
        pass

    good(f"Total JS files to analyse: {len(js_files)}")

    # ── Extract endpoints ────────────────────────────────────────────────────
    all_endpoints = set()
    info(f"Extracting endpoints from {min(len(js_files), 40)} JS files ...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(_extract_endpoints_from_js, js): js for js in list(js_files)[:40]}
        for f in concurrent.futures.as_completed(futs):
            js_url = futs[f]
            endpoints = f.result()
            if endpoints:
                print(f"\n  \033[94m{js_url}\033[0m")
                for ep in sorted(endpoints)[:10]:
                    print(f"    \033[92m{ep}\033[0m")
                all_endpoints |= endpoints

    good(f"Unique endpoints extracted: {len(all_endpoints)}")
    report.data["js_endpoints"] = sorted(all_endpoints)
    report.save_list("js_endpoints", sorted(all_endpoints))

    warn("These endpoints are often missed by automated scanners — check them manually!")
    info("Tools for deeper JS analysis:")
    print("  Zscanner (zseano):  scrape URLs + extract JS links")
    print("  JS-Scan:            extract all URLs defined in JS files")
    print("  linkfinder:         python3 linkfinder.py -i https://domain/file.js -o cli")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 5 — S3 Bucket Finder
# ═══════════════════════════════════════════════════════════════════════════════
def _check_s3(bucket):
    for url in [
        f"https://{bucket}.s3.amazonaws.com",
        f"https://s3.amazonaws.com/{bucket}",
    ]:
        try:
            r = requests.get(url, timeout=6)
            if r.status_code == 200:
                return (bucket, url, "🔓 PUBLIC READ", r.text[:120])
            elif r.status_code == 403:
                return (bucket, url, "🔒 EXISTS (403 Forbidden)", "")
        except Exception:
            pass
    return None


def s3_bucket_finder(domain, report):
    section("MODULE 5 │ AWS S3 BUCKET FINDER")
    name = domain.split(".")[0]

    variations = [
        name,
        f"{name}-dev", f"{name}-development",
        f"{name}-staging", f"{name}-stage",
        f"{name}-prod", f"{name}-production",
        f"{name}-backup", f"{name}-backups",
        f"{name}-static", f"{name}-assets",
        f"{name}-media", f"{name}-uploads",
        f"{name}-images", f"{name}-img",
        f"{name}-data", f"{name}-logs",
        f"{name}-files", f"{name}-public",
        f"{name}-private", f"{name}-internal",
        f"{name}-attachments", f"{name}-cdn",
        f"{name}-test", f"{name}-qa",
        f"dev-{name}", f"staging-{name}",
        f"prod-{name}", f"backup-{name}",
        f"assets-{name}", f"static-{name}",
        domain, f"www.{domain}",
    ]

    info(f"Checking {len(variations)} S3 bucket name variations ...")
    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
        futs = {ex.submit(_check_s3, v): v for v in variations}
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            if res:
                bucket, url, status, preview = res
                if "PUBLIC" in status:
                    juicy(f"BUCKET FOUND: {url}  [{status}]")
                    if preview:
                        print(f"  Preview: {preview[:80]}")
                else:
                    warn(f"Bucket exists: {url}  [{status}]")
                found.append({"bucket": bucket, "url": url, "status": status})

    if not found:
        info("No open S3 buckets found with common naming patterns")

    report.data["s3_buckets"] = found
    info("Manual Google Dork:")
    print(f"  site:amazonaws.com inurl:{name}")
    info("Tool suggestion:")
    print(f"  aws s3 ls s3://{name} --no-sign-request")
    print(f"  python3 s3scanner.py --buckets buckets.txt")
    link("https://github.com/sa7mon/S3Scanner")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 6 — GitHub Recon
# ═══════════════════════════════════════════════════════════════════════════════
def github_recon(domain, report):
    section("MODULE 6 │ GITHUB RECON")
    company = domain.split(".")[0]

    dorks = [
        f'"{domain}" password',
        f'"{domain}" secret',
        f'"{domain}" API_key',
        f'"{domain}" apikey',
        f'"{domain}" api_secret',
        f'"{domain}" "dev"',
        f'"{domain}" credentials',
        f'"{domain}" ftp',
        f'"{domain}" smtp',
        f'"{domain}" aws_access_key',
        f'"{domain}" S3_BUCKET',
        f'"dev.{domain}"',
        f'"staging.{domain}"',
        f'"api.{domain}"',
        f'"{company}" password',
        f'"{company}" secret_key',
        f'"{company}" aws_secret',
        f'"{company}" private_key',
    ]

    info("GitHub Code Search dorks (copy & paste into browser):")
    for dork in dorks:
        encoded = dork.replace('"', '%22').replace(" ", "+")
        url = f"https://github.com/search?q={encoded}&type=code"
        print(f"  \033[93m{dork}\033[0m")
        link(url)

    print()
    info("Google-to-GitHub dorks:")
    g_dorks = [
        f'site:github.com "{company}" password',
        f'site:github.com "{domain}" apikey',
        f'site:pastebin.com "{domain}"',
        f'site:trello.com "{domain}"',
        f'site:jsfiddle.net "{domain}"',
    ]
    for d in g_dorks:
        enc = quote(d)
        print(f"  \033[93m{d}\033[0m")
        link(f"https://www.google.com/search?q={enc}")

    print()
    info("Automated tools:")
    print(f"  truffleHog  --regex --entropy=False https://github.com/{company}/")
    print(f"  gitrob      --github-access-token <TOKEN> {company}")
    print(f"  git-all-secrets   -org {company}")
    print(f"  repo-supervisor   scan {company}")

    report.data["github_dorks"] = dorks


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 7 — Technology Detection
# ═══════════════════════════════════════════════════════════════════════════════
_CMS = {
    "WordPress":  [r"wp-content", r"wp-includes", r"wordpress"],
    "Drupal":     [r"drupal", r"sites/default"],
    "Joomla":     [r"joomla", r"/components/com_"],
    "Magento":    [r"magento", r"Mage\."],
    "Shopify":    [r"shopify", r"cdn\.shopify"],
    "Ghost":      [r"ghost-theme"],
    "Wix":        [r"wix\.com"],
}
_JS_FRAMEWORKS = {
    "React":       [r"react\.production\.min\.js", r"__react", r"React\.createElement"],
    "Angular":     [r"ng-app", r"angular\.min\.js", r"ng-version"],
    "Vue.js":      [r"vue\.min\.js", r"__vue__", r"v-app"],
    "jQuery":      [r"jquery\.min\.js", r"jQuery\."],
    "Next.js":     [r"_next/static"],
    "Nuxt.js":     [r"_nuxt/"],
    "Backbone.js": [r"backbone\.js"],
}


def tech_detect(domain, report):
    section("MODULE 7 │ TECHNOLOGY DETECTION")
    base_url = f"https://{domain}"
    tech = {}

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=12, verify=False)
        h = r.headers
        html = r.text.lower()

        # ── HTTP Headers ─────────────────────────────────────────────────────
        header_checks = {
            "Server":       "Web Server",
            "X-Powered-By": "Backend",
            "X-Generator":  "Generator",
            "X-Runtime":    "Runtime",
        }
        for hdr, label in header_checks.items():
            if hdr in h:
                tech[label] = h[hdr]
                good(f"{label:<15}: {h[hdr]}")

        # ── CDN / Cloud ───────────────────────────────────────────────────────
        if "cf-ray"  in h: tech["CDN"]  = "Cloudflare"; good("CDN            : Cloudflare")
        if "x-cache" in h: tech["Cache"]= h["x-cache"]; good(f"Cache          : {h['x-cache']}")
        if any("amz" in k.lower() for k in h):
            tech["Cloud"] = "AWS"; good("Cloud          : AWS")
        if "x-azure" in str(h).lower():
            tech["Cloud"] = "Azure"; good("Cloud          : Azure")

        # ── CMS Detection ────────────────────────────────────────────────────
        for cms, patterns in _CMS.items():
            if any(re.search(p, html, re.I) for p in patterns):
                tech["CMS"] = cms
                good(f"CMS            : {cms}")
                break

        # ── JS Framework Detection ────────────────────────────────────────────
        for fw, patterns in _JS_FRAMEWORKS.items():
            if any(re.search(p, html, re.I) for p in patterns):
                tech["JS Framework"] = fw
                good(f"JS Framework   : {fw}")
                break

        # ── Security Headers ──────────────────────────────────────────────────
        print()
        info("Security Headers:")
        sec_hdrs = [
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ]
        for sh in sec_hdrs:
            if sh in h:
                good(f"  ✔ {sh}: {h[sh][:70]}")
            else:
                warn(f"  ✗ {sh}: MISSING")

        report.data["technologies"] = tech

    except Exception as e:
        bad(f"Tech detection error: {e}")

    info("Use Wappalyzer browser extension for detailed fingerprinting:")
    link(f"https://www.wappalyzer.com/lookup/{domain}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 8 — Content Discovery (Google Dorks)
# ═══════════════════════════════════════════════════════════════════════════════
def content_discovery(domain, report):
    section("MODULE 8 │ CONTENT DISCOVERY — GOOGLE DORKS")

    dork_groups = {
        "File Extensions": [
            f"site:{domain} filetype:php",
            f"site:{domain} filetype:aspx",
            f"site:{domain} filetype:swf",
            f"site:{domain} filetype:wsdl",
            f"site:{domain} filetype:txt",
            f"site:{domain} filetype:log",
            f"site:{domain} filetype:bak",
            f"site:{domain} filetype:sql",
            f"site:{domain} filetype:env",
            f"site:{domain} filetype:yaml",
            f"site:{domain} filetype:xml",
        ],
        "Parameters (for SQLi/XSS hunting)": [
            f"site:{domain} inurl:.php?id=",
            f"site:{domain} inurl:.php?user=",
            f"site:{domain} inurl:.php?page=",
            f"site:{domain} inurl:.php?book=",
            f"site:{domain} inurl:.php?cat=",
            f"site:{domain} inurl:.aspx?id=",
        ],
        "Login & Admin Panels": [
            f"site:{domain} inurl:login.php",
            f"site:{domain} inurl:login.aspx",
            f"site:{domain} inurl:admin",
            f"site:{domain} inurl:portal",
            f"site:{domain} inurl:dashboard",
            f"site:{domain} inurl:register.php",
            f'site:{domain} intext:"login"',
        ],
        "Directory Listings": [
            f'site:{domain} intext:"index of /"',
            f'site:{domain} intitle:"index of"',
        ],
        "Sensitive Content": [
            f'site:{domain} intext:password',
            f'site:{domain} intext:username',
            f"site:{domain} inurl:config",
            f"site:{domain} inurl:backup",
            f"site:{domain} inurl:test",
            f"site:{domain} inurl:dev",
            f"site:{domain} inurl:staging",
        ],
        "Subdomains via Google": [
            f"site:{domain} -site:www.{domain}",
        ],
    }

    all_dorks = []
    for group, dorks in dork_groups.items():
        print(f"\n  \033[1;33m── {group} ──\033[0m")
        for dork in dorks:
            encoded = quote(dork)
            url = f"https://www.google.com/search?q={encoded}"
            print(f"  \033[93m{dork}\033[0m")
            link(url)
            all_dorks.append(dork)

    report.data["google_dorks"] = all_dorks
    report.save_list("google_dorks", all_dorks)

    print()
    info("Directory Brute-Force (run on Kali / Linux):")
    print(f"  gobuster dir -u https://{domain} -w /usr/share/wordlists/dirb/common.txt -t 50")
    print(f"  ffuf -u https://{domain}/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt")
    print(f"  dirsearch -u https://{domain} -e php,asp,aspx,txt,bak,sql,json")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 9 — Quick Wins (common exposed files/paths)
# ═══════════════════════════════════════════════════════════════════════════════
_QUICK_PATHS = [
    ("/robots.txt",              "Robots.txt",                  False),
    ("/sitemap.xml",             "Sitemap",                     False),
    ("/.git/HEAD",               "GIT REPOSITORY EXPOSED!",     True),
    ("/.git/config",             "GIT CONFIG EXPOSED!",         True),
    ("/.env",                    ".ENV FILE EXPOSED!",          True),
    ("/.env.backup",             ".ENV BACKUP EXPOSED!",        True),
    ("/phpinfo.php",             "PHPINFO.PHP EXPOSED!",        True),
    ("/info.php",                "INFO.PHP EXPOSED!",           True),
    ("/test.php",                "TEST.PHP EXPOSED!",           True),
    ("/wp-admin/",               "WordPress Admin Panel",       False),
    ("/wp-config.php",           "WP-CONFIG.PHP EXPOSED!",     True),
    ("/wp-login.php",            "WordPress Login",             False),
    ("/admin/",                  "Admin Panel",                 False),
    ("/administrator/",          "Administrator Panel",         False),
    ("/dashboard/",              "Dashboard",                   False),
    ("/backup.zip",              "BACKUP.ZIP EXPOSED!",         True),
    ("/backup.rar",              "BACKUP.RAR EXPOSED!",         True),
    ("/backup.tar.gz",           "BACKUP TAR.GZ EXPOSED!",     True),
    ("/db.sql",                  "DB.SQL EXPOSED!",             True),
    ("/database.sql",            "DATABASE.SQL EXPOSED!",      True),
    ("/config.php",              "CONFIG.PHP EXPOSED!",         True),
    ("/config.yml",              "CONFIG.YML EXPOSED!",         True),
    ("/web.config",              "WEB.CONFIG EXPOSED!",         True),
    ("/.htaccess",               ".HTACCESS EXPOSED!",          True),
    ("/crossdomain.xml",         "Cross-Domain Policy",         False),
    ("/.well-known/security.txt","Security.txt",                False),
    ("/server-status",           "Apache Server Status!",       True),
    ("/server-info",             "Apache Server Info!",         True),
    ("/.DS_Store",               ".DS_STORE EXPOSED!",          True),
    ("/Thumbs.db",               "THUMBS.DB EXPOSED!",          True),
    ("/id_rsa",                  "PRIVATE KEY EXPOSED!",        True),
    ("/id_rsa.pub",              "PUBLIC KEY EXPOSED!",         True),
    ("/docker-compose.yml",      "DOCKER-COMPOSE EXPOSED!",    True),
    ("/Dockerfile",              "DOCKERFILE EXPOSED!",         True),
    ("/package.json",            "Package.json",                False),
    ("/composer.json",           "Composer.json",               False),
]


def _check_path(args):
    base, path, label, is_critical = args
    url = base + path
    try:
        r = requests.get(
            url, headers=HEADERS, timeout=6,
            verify=False, allow_redirects=False
        )
        if r.status_code == 200:
            return (url, label, r.status_code, len(r.content), is_critical)
        elif r.status_code in (301, 302):
            return (url, label + " (redirect)", r.status_code, 0, False)
    except Exception:
        pass
    return None


def quick_wins(domain, report):
    section("MODULE 9 │ QUICK WINS — COMMON EXPOSED PATHS")
    base = f"https://{domain}"
    info(f"Checking {len(_QUICK_PATHS)} common paths on {base} ...")

    args_list = [(base, p, l, c) for p, l, c in _QUICK_PATHS]
    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        futs = [ex.submit(_check_path, a) for a in args_list]
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            if res:
                url, label, code, size, is_crit = res
                if is_crit:
                    juicy(f"{label:<35} → {url}  [{code}]  {size}b")
                else:
                    good(f"{label:<35} → {url}  [{code}]  {size}b")
                found.append({
                    "url": url, "label": label,
                    "status": code, "size": size, "critical": is_crit
                })

    if not found:
        info("No interesting paths found at common locations")
    else:
        warn(f"Found {len(found)} accessible path(s) — review each one!")

    report.data["quick_wins"] = found


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 10 — DNS Records Mapper
# ═══════════════════════════════════════════════════════════════════════════════
def dns_records(domain, report):
    section("MODULE 10 │ DNS RECORDS MAPPER")
    record_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"]
    results = {}
    for rtype in record_types:
        try:
            r = requests.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": domain, "type": rtype},
                headers={**HEADERS, "Accept": "application/dns-json"},
                timeout=8,
            )
            answers = r.json().get("Answer", [])
            if answers:
                records = [a.get("data", "") for a in answers]
                results[rtype] = records
                good(f"{rtype:<6} → {len(records)} record(s)")
                for rec in records[:5]:
                    print(f"  {rec}")
        except Exception as e:
            warn(f"  {rtype}: {e}")
    for txt in results.get("TXT", []):
        if "v=spf1"   in txt: good(f"SPF    : {txt}")
        if "v=DMARC1" in txt: good(f"DMARC  : {txt}")
        if any(x in txt.lower() for x in ["verify", "token", "key", "secret"]):
            warn(f"Juicy TXT record: {txt}")
    report.data["dns_records"] = results
    report.save_list("dns_records", [f"{k}: {v}" for k, vs in results.items() for v in vs])


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 11 — Zone Transfer Check (AXFR)
# ═══════════════════════════════════════════════════════════════════════════════
def zone_transfer(domain, report):
    section("MODULE 11 │ ZONE TRANSFER CHECK (AXFR)")
    ns_list = []
    try:
        r = requests.get(
            "https://cloudflare-dns.com/dns-query",
            params={"name": domain, "type": "NS"},
            headers={**HEADERS, "Accept": "application/dns-json"},
            timeout=8,
        )
        for ans in r.json().get("Answer", []):
            ns = ans.get("data", "").rstrip(".")
            if ns:
                ns_list.append(ns)
    except Exception:
        pass
    if not ns_list:
        warn("Could not determine nameservers"); return
    info(f"Testing AXFR against: {', '.join(ns_list)}")
    vulnerable = []
    for ns in ns_list:
        try:
            ns_ip = socket.gethostbyname(ns)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ns_ip, 53))
            qname = b"".join(bytes([len(p)]) + p.encode() for p in domain.split(".")) + b"\x00"
            payload = b"\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00" + qname + b"\x00\xfc\x00\x01"
            s.send(len(payload).to_bytes(2, "big") + payload)
            resp = s.recv(512)
            s.close()
            if len(resp) > 6:
                rcode = resp[5] & 0x0F
                if rcode == 0:
                    juicy(f"ZONE TRANSFER MAY BE POSSIBLE → {ns} ({ns_ip})")
                    vulnerable.append(ns)
                elif rcode == 5:
                    good(f"{ns}: REFUSED (properly restricted)")
                else:
                    good(f"{ns}: rcode={rcode} (restricted)")
            else:
                good(f"{ns}: no response (restricted)")
        except Exception as e:
            good(f"{ns}: {e}")
    if not vulnerable:
        good("Zone transfer properly restricted on all nameservers")
    report.data["zone_transfer"] = {"vulnerable": vulnerable, "tested": ns_list}


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 12 — Subdomain Takeover Scanner
# ═══════════════════════════════════════════════════════════════════════════════
_TAKEOVER_FINGERPRINTS = {
    "github.io":         "There isn't a GitHub Pages site here",
    "heroku.com":        "No such app",
    "herokuapp.com":     "No such app",
    "shopify.com":       "Sorry, this shop is currently unavailable",
    "netlify.app":       "Not Found",
    "amazonaws.com":     "NoSuchBucket",
    "cloudfront.net":    "ERROR: The request could not be satisfied",
    "azurewebsites.net": "404 Web Site not found",
    "zendesk.com":       "Help Center Closed",
    "wordpress.com":     "Do you want to register",
    "tumblr.com":        "Whatever you were looking for doesn't currently exist",
    "ghost.io":          "The thing you were looking for is no longer here",
    "surge.sh":          "project not found",
    "fly.dev":           "404 Not Found",
    "vercel.app":        "The deployment could not be found",
    "bitbucket.io":      "Repository not found",
    "readme.io":         "Project doesnt exist",
    "intercom.com":      "Uh oh. That page doesn't exist",
}


def subdomain_takeover(domain, report):
    section("MODULE 12 │ SUBDOMAIN TAKEOVER SCANNER")
    subs_data = report.data.get("subdomains", [])
    if not subs_data:
        warn("Run subdomain discovery first (-m subdomains)"); return
    info(f"Checking {len(subs_data)} subdomains for dangling CNAMEs ...")
    results = []

    def _check(sub_info):
        host = sub_info["host"]
        try:
            r = requests.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": host, "type": "CNAME"},
                headers={**HEADERS, "Accept": "application/dns-json"},
                timeout=6,
            )
            for ans in r.json().get("Answer", []):
                cname = ans.get("data", "").rstrip(".")
                for svc, fingerprint in _TAKEOVER_FINGERPRINTS.items():
                    if svc in cname:
                        try:
                            page = requests.get(f"https://{host}", headers=HEADERS,
                                                timeout=6, verify=False)
                            status = "VULNERABLE" if fingerprint.lower() in page.text.lower() else "CHECK-MANUALLY"
                        except Exception:
                            status = "CNAME-FOUND"
                        return {"host": host, "cname": cname, "service": svc, "status": status}
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for fut in concurrent.futures.as_completed([ex.submit(_check, s) for s in subs_data]):
            res = fut.result()
            if res:
                results.append(res)
                if res["status"] == "VULNERABLE":
                    juicy(f"TAKEOVER: {res['host']} → {res['cname']} [{res['service']}]")
                else:
                    warn(f"Check manually: {res['host']} → {res['cname']} ({res['status']})")
    if not results:
        good("No subdomain takeover candidates found")
    report.data["subdomain_takeover"] = results


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 13 — URL Parameter Extractor
# ═══════════════════════════════════════════════════════════════════════════════
_PARAM_CATEGORIES = {
    "open_redirect": ["url","redirect","return","returnUrl","next","goto","dest",
                      "destination","redir","continue","target","to","link","out","view","go","forward"],
    "ssrf":          ["url","uri","src","source","dest","host","hostname","proxy",
                      "webhook","callback","fetch","load","service","endpoint","feed","ping","import"],
    "sqli_idor":     ["id","user_id","item","product","order","cat","category",
                      "page","num","offset","limit","from","record","row","no"],
    "lfi":           ["file","page","template","view","doc","document","path",
                      "folder","dir","include","load","read","display","show","open"],
    "xss":           ["q","query","search","s","term","keyword","name","input",
                      "msg","comment","text","data","content","value","html","message"],
}


def param_extractor(domain, report):
    section("MODULE 13 │ URL PARAMETER EXTRACTOR")
    all_urls = list(report.data.get("wayback_urls", []))
    info("Fetching extra URLs from URLScan.io ...")
    try:
        r = requests.get(
            f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=100",
            headers=HEADERS, timeout=12,
        )
        for result in r.json().get("results", []):
            u = result.get("page", {}).get("url", "")
            if u:
                all_urls.append(u)
    except Exception as e:
        warn(f"URLScan: {e}")
    info(f"Analyzing {len(all_urls)} URLs for parameters ...")
    param_freq = {}
    flagged = {k: set() for k in _PARAM_CATEGORIES}
    for url in all_urls:
        try:
            q = urlparse(url).query
            if not q:
                continue
            for pair in q.split("&"):
                key = pair.split("=")[0].lower()
                if key:
                    param_freq[key] = param_freq.get(key, 0) + 1
                    for cat, plist in _PARAM_CATEGORIES.items():
                        if key in plist:
                            flagged[cat].add(key)
        except Exception:
            pass
    good(f"Unique parameters found: {len(param_freq)}")
    top = sorted(param_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    if top:
        info("Top 20 parameters by frequency:")
        for p, c in top:
            print(f"  \033[93m?{p}=\033[0m  ({c}x)")
    for cat, pset in flagged.items():
        if pset:
            warn(f"Potential {cat} params: {', '.join(sorted(pset))}")
    report.data["parameters"] = {
        "frequency": param_freq,
        "flagged": {k: list(v) for k, v in flagged.items() if v},
    }
    report.save_list("parameters", [f"?{p}=" for p in param_freq])


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 14 — JS Secrets Scanner
# ═══════════════════════════════════════════════════════════════════════════════
_SECRET_PATTERNS = {
    "AWS Access Key":   r"AKIA[0-9A-Z]{16}",
    "GitHub Token":     r"gh[pousr]_[A-Za-z0-9_]{36,255}",
    "JWT Token":        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "Google API Key":   r"AIza[0-9A-Za-z\-_]{35}",
    "Slack Webhook":    r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
    "Stripe Live Key":  r"sk_live_[0-9a-zA-Z]{24}",
    "Twilio SID":       r"AC[0-9a-fA-F]{32}",
    "Private Key":      r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "Firebase URL":     r"https://[a-z0-9-]+\.firebaseio\.com",
    "Password in code": r"password\s*[=:]\s*[\"'][^\"']{4,}[\"']",
    "API Key in var":   r"api_?key\s*[=:]\s*[\"'][A-Za-z0-9_\-]{8,}[\"']",
    "Secret in var":    r"secret\s*[=:]\s*[\"'][A-Za-z0-9_\-]{8,}[\"']",
    "Bearer Token":     r"[Bb]earer\s+[A-Za-z0-9\-._~+/]+=*",
    "Internal IP":      r"(192\.168\.|10\.\d+\.|172\.(1[6-9]|2[0-9]|3[01])\.)[\d.]+",
}


def js_secrets_scan(domain, report):
    section("MODULE 14 │ JS SECRETS SCANNER")
    base_url = f"https://{domain}"
    js_urls = set()
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup.find_all("script", src=True):
            src = tag["src"]
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            js_urls.add(src)
    except Exception:
        pass
    try:
        r = requests.get(
            f"http://web.archive.org/cdx/search/cdx"
            f"?url=*.{domain}/*.js&output=text&fl=original&collapse=urlkey&limit=40",
            timeout=15,
        )
        for u in r.text.strip().splitlines():
            js_urls.add(u)
    except Exception:
        pass
    good(f"Scanning {len(js_urls)} JS files for secrets ...")
    findings = []

    def _scan(js_url):
        local = []
        try:
            r = requests.get(js_url, headers=HEADERS, timeout=8, verify=False)
            for name, pattern in _SECRET_PATTERNS.items():
                for m in re.findall(pattern, r.text)[:3]:
                    if len(str(m)) >= 8:
                        local.append({"file": js_url, "type": name, "match": str(m)[:80]})
        except Exception:
            pass
        return local

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for fut in concurrent.futures.as_completed([ex.submit(_scan, js) for js in list(js_urls)[:50]]):
            for f in fut.result():
                juicy(f"[{f['type']}] → {f['file']}")
                print(f"  Match: \033[93m{f['match']}\033[0m")
                findings.append(f)
    if not findings:
        good("No obvious secrets detected in JS files")
    else:
        warn(f"{len(findings)} potential secret(s) found — verify manually!")
    report.data["js_secrets"] = findings


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 15 — API / Swagger / GraphQL Finder
# ═══════════════════════════════════════════════════════════════════════════════
_API_PATHS = [
    "/api", "/api/v1", "/api/v2", "/api/v3", "/v1", "/v2", "/v3",
    "/rest", "/rest/v1", "/graphql", "/graphiql", "/playground",
    "/swagger.json", "/swagger.yaml", "/swagger/v1/swagger.json",
    "/api-docs", "/api-docs.json", "/openapi.json", "/openapi.yaml",
    "/api/swagger.json", "/api/openapi.json", "/.well-known/openapi",
    "/api/schema", "/schema.json", "/api/explorer", "/api/graphql",
    "/graphql/console", "/graph", "/api/rest",
]


def api_finder(domain, report):
    section("MODULE 15 │ API / SWAGGER / GRAPHQL FINDER")
    base  = f"https://{domain}"
    found = []
    info(f"Checking {len(_API_PATHS)} API-related paths ...")

    def _check(path):
        url = base + path
        try:
            r = requests.get(url, headers=HEADERS, timeout=6, verify=False, allow_redirects=True)
            if r.status_code != 200:
                return None
            ct   = r.headers.get("Content-Type", "")
            text = r.text[:500].lower()
            if "swagger" in text or "openapi" in text or "swagger" in path:
                kind = "swagger/openapi"
            elif "graphql" in path or "playground" in path or "graphiql" in path:
                kind = "graphql-ui"
            elif "json" in ct or text.lstrip().startswith("{") or text.lstrip().startswith("["):
                kind = "api-json"
            else:
                kind = "api-page"
            return {"url": url, "type": kind, "status": 200, "size": len(r.content)}
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        for fut in concurrent.futures.as_completed([ex.submit(_check, p) for p in _API_PATHS]):
            res = fut.result()
            if res:
                found.append(res)
                if res["type"] in ("swagger/openapi", "graphql-ui"):
                    juicy(f"{res['type'].upper()}: {res['url']}")
                else:
                    good(f"{res['type']}: {res['url']}  {res['size']}b")

    # GraphQL introspection test
    gql_url = f"{base}/graphql"
    info("Testing GraphQL introspection ...")
    try:
        r = requests.post(
            gql_url,
            data='{"query":"{__schema{types{name}}}"}',
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=8, verify=False,
        )
        if r.status_code == 200 and "__schema" in r.text:
            juicy(f"GraphQL INTROSPECTION ENABLED: {gql_url}")
            found.append({"url": gql_url, "type": "graphql-introspection", "status": 200, "size": len(r.content)})
        elif r.status_code == 200:
            good(f"GraphQL endpoint alive (introspection disabled): {gql_url}")
    except Exception:
        pass

    if not found:
        info("No API/Swagger/GraphQL endpoints found at common paths")
    report.data["api_endpoints"] = found
    report.save_list("api_endpoints", [e["url"] for e in found])


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 16 — CORS Misconfiguration Tester
# ═══════════════════════════════════════════════════════════════════════════════
def cors_tester(domain, report):
    section("MODULE 16 │ CORS MISCONFIGURATION TESTER")
    base         = f"https://{domain}"
    test_origins = [
        "https://evil.com",
        f"https://{domain}.evil.com",
        f"https://evil{domain}",
        "null",
        "https://attacker.com",
    ]
    info(f"Testing {len(test_origins)} origin variations ...")
    findings = []
    for origin in test_origins:
        try:
            r    = requests.get(base, headers={**HEADERS, "Origin": origin}, timeout=8, verify=False)
            acao = r.headers.get("Access-Control-Allow-Origin", "")
            acac = r.headers.get("Access-Control-Allow-Credentials", "")
            if not acao:
                continue
            if acao == "*":
                warn(f"Wildcard CORS (*) — origin: {origin}")
                findings.append({"origin": origin, "acao": acao, "credentials": acac, "severity": "medium"})
            elif acao == origin:
                if acac.lower() == "true":
                    juicy(f"CORS + Credentials! '{origin}' reflected + credentials=true")
                    findings.append({"origin": origin, "acao": acao, "credentials": acac, "severity": "high"})
                else:
                    warn(f"Origin reflected: '{origin}' → ACAO: {acao}")
                    findings.append({"origin": origin, "acao": acao, "credentials": acac, "severity": "low"})
        except Exception:
            pass
    if not findings:
        good("No CORS misconfigurations detected")
    else:
        warn(f"{len(findings)} CORS issue(s) found — verify manually!")
    report.data["cors"] = findings


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 17 — TLS / SSL Certificate Inspector
# ═══════════════════════════════════════════════════════════════════════════════
def tls_checker(domain, report):
    section("MODULE 17 │ TLS/SSL CERTIFICATE INSPECTOR")
    import ssl
    findings = {}
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=domain) as ssock:
            ssock.settimeout(8)
            ssock.connect((domain, 443))
            cert   = ssock.getpeercert()
            cipher = ssock.cipher()
            ver    = ssock.version()
        not_after  = datetime.strptime(cert.get("notAfter", ""), "%b %d %H:%M:%S %Y %Z")
        days_left  = (not_after - datetime.utcnow()).days
        subject    = dict(x[0] for x in cert.get("subject", []))
        issuer     = dict(x[0] for x in cert.get("issuer",  []))
        cn         = subject.get("commonName", "?")
        org        = issuer.get("organizationName", "?")
        sans       = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
        good(f"CN           : {cn}")
        good(f"Issuer       : {org}")
        good(f"TLS Version  : {ver}")
        good(f"Cipher       : {cipher[0] if cipher else '?'}")
        if   days_left < 0:   juicy(f"Certificate EXPIRED {abs(days_left)} days ago!")
        elif days_left < 15:  juicy(f"Expires in {days_left} days — CRITICAL!")
        elif days_left < 30:  warn(f"Expires in {days_left} days — renew soon")
        else:                 good(f"Expires      : {not_after.strftime('%Y-%m-%d')} ({days_left} days)")
        if sans:
            good(f"SANs ({len(sans)})    : {', '.join(sans[:6])}")
            if len(sans) > 6: info(f"  ... and {len(sans)-6} more SANs")
        if ver in ("TLSv1", "TLSv1.0", "TLSv1.1"):
            warn(f"Deprecated TLS version: {ver} — upgrade to TLS 1.2+")
        try:
            rr   = requests.get(f"https://{domain}", headers=HEADERS, timeout=8, verify=False)
            hsts = rr.headers.get("Strict-Transport-Security", "")
            if hsts: good(f"HSTS         : {hsts}")
            else:    warn("HSTS header missing!")
        except Exception:
            pass
        findings = {
            "cn": cn, "issuer": org, "tls_version": ver,
            "cipher": cipher[0] if cipher else "?",
            "expires": not_after.isoformat(), "days_left": days_left, "sans": sans,
        }
    except Exception as e:
        bad(f"TLS check error: {e}")
        findings["error"] = str(e)
    report.data["tls"] = findings


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 18 — Cookie Security Checker
# ═══════════════════════════════════════════════════════════════════════════════
def cookie_checker(domain, report):
    section("MODULE 18 │ COOKIE SECURITY CHECKER")
    base = f"https://{domain}"
    try:
        r           = requests.get(base, headers=HEADERS, timeout=10, verify=False)
        raw_cookies = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
        if not raw_cookies:
            info("No cookies set on initial response")
            report.data["cookies"] = []
            return
        findings = []
        for cookie_str in raw_cookies:
            parts        = [p.strip() for p in cookie_str.split(";")]
            name         = parts[0].split("=", 1)[0] if parts else "unknown"
            attrs        = [p.lower() for p in parts[1:]]
            has_secure   = any(a == "secure"   for a in attrs)
            has_httponly = any(a == "httponly"  for a in attrs)
            samesite     = next((a.split("=")[1] for a in attrs if a.startswith("samesite=")), None)
            issues = []
            if not has_secure:   issues.append("Missing Secure")
            if not has_httponly: issues.append("Missing HttpOnly")
            if not samesite:     issues.append("Missing SameSite")
            entry = {
                "name": name, "secure": has_secure, "httponly": has_httponly,
                "samesite": samesite or "not set", "issues": issues,
            }
            findings.append(entry)
            if issues: warn(f"Cookie '{name}': {', '.join(issues)}")
            else:      good(f"Cookie '{name}': ✔ Secure  ✔ HttpOnly  ✔ SameSite={samesite}")
        report.data["cookies"] = findings
    except Exception as e:
        bad(f"Cookie check error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 19 — HTTP Method Analyzer
# ═══════════════════════════════════════════════════════════════════════════════
def http_methods(domain, report):
    section("MODULE 19 │ HTTP METHOD ANALYZER")
    base    = f"https://{domain}"
    methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "HEAD", "DEBUG"]
    results = []
    info(f"Testing {len(methods)} HTTP methods on {base} ...")
    for method in methods:
        try:
            r     = requests.request(method, base, headers=HEADERS, timeout=6, verify=False, allow_redirects=False)
            entry = {"method": method, "status": r.status_code}
            if method == "TRACE" and r.status_code == 200:
                juicy(f"TRACE ENABLED → Cross-Site Tracing (XST) possible: {base}")
                entry["critical"] = True
            elif method == "OPTIONS":
                allow = r.headers.get("Allow", r.headers.get("Public", ""))
                if allow:
                    good(f"OPTIONS → Allow: {allow}")
                    entry["allow"] = allow
                    if any(m in allow for m in ["PUT", "DELETE", "TRACE"]):
                        warn(f"Dangerous method(s) in Allow header: {allow}")
                else:
                    info(f"OPTIONS → {r.status_code}")
            elif method in ("PUT", "DELETE") and r.status_code not in (400, 403, 404, 405, 501):
                warn(f"{method:<8} → {r.status_code} (unexpected — may be enabled!)")
                entry["suspicious"] = True
            else:
                fn = good if r.status_code in (200, 204) else info
                fn(f"{method:<8} → {r.status_code}")
            results.append(entry)
        except Exception:
            pass
    report.data["http_methods"] = results


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 20 — Open Redirect & SSRF Parameter Hints
# ═══════════════════════════════════════════════════════════════════════════════
_REDIR_PARAMS = {
    "url","redirect","return","returnUrl","next","goto","dest","destination",
    "redir","continue","target","to","link","out","view","site","go","forward","back","ref",
}
_SSRF_PARAMS = {
    "url","uri","src","source","dest","host","hostname","proxy","webhook",
    "callback","fetch","load","service","endpoint","feed","ping","import","request",
}


def open_redirect_ssrf(domain, report):
    section("MODULE 20 │ OPEN REDIRECT & SSRF HINTS")
    all_urls    = list(report.data.get("wayback_urls", []))[:500]
    redir_found = set()
    ssrf_found  = set()
    for url in all_urls:
        try:
            for pair in urlparse(url).query.split("&"):
                key = pair.split("=")[0].lower()
                if key in _REDIR_PARAMS: redir_found.add(key)
                if key in _SSRF_PARAMS:  ssrf_found.add(key)
        except Exception:
            pass
    findings = []
    base     = f"https://{domain}"
    if redir_found:
        warn(f"Open Redirect candidate params: {', '.join(sorted(redir_found))}")
        for p in sorted(redir_found):
            url = f"{base}?{p}=https://evil.com"
            print(f"  Test: \033[93m{url}\033[0m")
            findings.append({"type": "open_redirect", "param": p, "test_url": url})
    if ssrf_found:
        warn(f"SSRF candidate params: {', '.join(sorted(ssrf_found))}")
        for p in sorted(ssrf_found):
            url = f"{base}?{p}=http://169.254.169.254/"
            print(f"  Test: \033[93m{url}\033[0m")
            findings.append({"type": "ssrf", "param": p, "test_url": url})
    if not findings:
        info("No redirect/SSRF candidates found — run 'wayback' module for better results")
    report.data["redirect_ssrf"] = findings


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        description='The KAKASHI Recon V 1.1 - Recon Like A Bug Hunter',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "domain",
        help="Target domain — e.g.  example.com"
    )
    parser.add_argument(
        "-o", "--output",
        default="recon_output",
        help="Output directory (default: recon_output)"
    )
    parser.add_argument(
        "-m", "--modules",
        default="all",
        help=(
            "Comma-separated modules to run (default: all)\n"
            "Core : wayback, subdomains, ip, js, s3, github, tech, content, quick\n"
            "New  : dns, zone, takeover, params, secrets, api, cors, tls, cookies, methods, redirect\n"
            "Example: -m subdomains,dns,tls,cors,secrets,api"
        )
    )
    args = parser.parse_args()

    # Normalise domain
    domain = (
        args.domain.strip().lower()
        .replace("https://", "").replace("http://", "")
        .rstrip("/")
    )

    report = ReconReport(domain, args.output)

    print(f"\033[1;35m  Target  :\033[0m {domain}")
    print(f"\033[1;35m  Output  :\033[0m {args.output}/")
    print(f"\033[1;35m  Started :\033[0m {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Module selection
    if args.modules.lower() == "all":
        mods = [
            "wayback", "subdomains", "ip", "js", "s3", "github",
            "tech", "content", "quick",
            "dns", "zone", "takeover", "params", "secrets",
            "api", "cors", "tls", "cookies", "methods", "redirect",
        ]
    else:
        mods = [m.strip().lower() for m in args.modules.split(",")]

    module_map = {
        # ── Original 9 ────────────────────────────────────────────
        "wayback":    lambda: wayback_recon(domain, report),
        "subdomains": lambda: subdomain_discovery(domain, report),
        "ip":         lambda: ip_range_lookup(domain, report),
        "js":         lambda: js_endpoint_discovery(domain, report),
        "s3":         lambda: s3_bucket_finder(domain, report),
        "github":     lambda: github_recon(domain, report),
        "tech":       lambda: tech_detect(domain, report),
        "content":    lambda: content_discovery(domain, report),
        "quick":      lambda: quick_wins(domain, report),
        # ── New 11 ────────────────────────────────────────────────
        "dns":        lambda: dns_records(domain, report),
        "zone":       lambda: zone_transfer(domain, report),
        "takeover":   lambda: subdomain_takeover(domain, report),
        "params":     lambda: param_extractor(domain, report),
        "secrets":    lambda: js_secrets_scan(domain, report),
        "api":        lambda: api_finder(domain, report),
        "cors":       lambda: cors_tester(domain, report),
        "tls":        lambda: tls_checker(domain, report),
        "cookies":    lambda: cookie_checker(domain, report),
        "methods":    lambda: http_methods(domain, report),
        "redirect":   lambda: open_redirect_ssrf(domain, report),
    }

    try:
        for mod in mods:
            if mod in module_map:
                module_map[mod]()
            else:
                warn(f"Unknown module: {mod}")
    except KeyboardInterrupt:
        print()
        warn("Scan interrupted by user (Ctrl+C)")

    # ── Summary ──────────────────────────────────────────────────────────────
    section("SCAN COMPLETE — SUMMARY")
    good(f"Target            : {domain}")
    good(f"Wayback URLs      : {len(report.data['wayback_urls'])}")
    good(f"Subdomains        : {len(report.data['subdomains'])}")
    good(f"JS Endpoints      : {len(report.data['js_endpoints'])}")
    good(f"S3 Buckets        : {len(report.data['s3_buckets'])}")
    good(f"Technologies      : {', '.join(report.data['technologies'].keys()) or 'None detected'}")
    good(f"Quick Wins        : {len(report.data.get('quick_wins', []))}")
    good(f"DNS Record Types  : {len(report.data.get('dns_records', {}))}")
    good(f"Zone Transfer     : {len(report.data.get('zone_transfer', {}).get('vulnerable', []))} vulnerable")
    good(f"Takeover Candidates: {len(report.data.get('subdomain_takeover', []))}")
    good(f"Parameters Found  : {len(report.data.get('parameters', {}).get('frequency', {}))}")
    good(f"JS Secrets        : {len(report.data.get('js_secrets', []))}")
    good(f"API Endpoints     : {len(report.data.get('api_endpoints', []))}")
    good(f"CORS Issues       : {len(report.data.get('cors', []))}")
    good(f"Cookie Issues     : {len([c for c in report.data.get('cookies', []) if c.get('issues')])}")
    good(f"HTTP Methods      : {len(report.data.get('http_methods', []))}")
    good(f"Redirect/SSRF     : {len(report.data.get('redirect_ssrf', []))}")

    report.save()
    good(f"All output files in: {os.path.abspath(args.output)}/")


if __name__ == "__main__":
    main()
