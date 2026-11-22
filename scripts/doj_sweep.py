"""Przegląd komunikatów DOJ (oficjalne API) pod kątem nicków forumowych.
Użycie: python -I -X utf8 doj_sweep.py <katalog_wyjsciowy>
Zapisuje: doj_raw.json (wszystkie komunikaty), doj_kandydaci.json i doj_kandydaci.md (z forum + pseudonimem)."""
import json, os, re, sys, time, urllib.parse, urllib.request
from html import unescape

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)  # 2026-11-22: brak tego kroku wykrył test odtworzenia na czystym katalogu
KEYWORDS = ["hack", "ransomware", "malware", "cybercriminal", "botnet", "dark web", "darknet", "carding",
            "forum", "cyber", "computer intrusion", "stolen data", "credentials", "marketplace", "access broker"]
API = "https://www.justice.gov/api/v1/press_releases.json?"
PAGESIZE = 50

FORUMS = ["Exploit", "XSS", "RAMP", "BreachForums", "Breach Forums", "RaidForums", "Raid Forums", "Hack Forums",
          "HackForums", "Verified", "Mazafaka", "Maza", "Club2Card", "Altenen", "fuckav", "Omerta", "Sniff3r", "L33t",
          "Infraud", "CardingMafia", "Cracked", "Nulled", "Dread", "Genesis Market", "Carder.su", "CarderPlanet",
          "DirectConnection", "Darkode", "Lolzteam", "WWH-Club", "Antichat", "Damagelab", "BHF", "Joker's Stash",
          "Hydra", "Empire Market", "AlphaBay", "Hansa", "Wall Street Market"]
FORUM_RE = re.compile(r"\b(" + "|".join(re.escape(f) for f in FORUMS) + r")\b", re.I)
FORUM_WORD = re.compile(r"\b(online|criminal|cybercrim\w*|hack\w*|underground|dark ?web|russian[- ]language)\s+forums?\b", re.I)
ALIAS_RE = re.compile(
    r"(?:a/k/a|aka|also known as|known online as|online (?:moniker|alias|persona|handle|nickname)s?|moniker|"
    r"under the (?:alias|name|moniker|handle)|username|user name|handle|nickname)\s*,?\s*(?:of\s+)?[“\"']([^”\"']{2,40})[”\"']",
    re.I)
STATE_RE = re.compile(r"\b(GRU|FSB|SVR|Ministry of State Security|MSS|People's Liberation Army|PLA Unit|Unit \d{5}|"
                      r"North Korea\w*|DPRK|Reconnaissance General Bureau|IRGC|Islamic Revolutionary Guard|"
                      r"state[- ]sponsored|on behalf of the (?:government|Russian|Chinese|Iranian)|intelligence service|espionage)\b", re.I)


def fetch(kw, page):
    url = API + urllib.parse.urlencode({"parameters[title]": kw, "pagesize": PAGESIZE, "page": page})
    req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            print(f"  błąd {kw} s.{page}: {e}; ponawiam", flush=True)
            time.sleep(10)
    return {"results": [], "metadata": {"resultset": {"count": "0"}}}


releases = {}
for kw in KEYWORDS:
    page, total = 0, None
    while True:
        d = fetch(kw, page)
        total = int(d.get("metadata", {}).get("resultset", {}).get("count", 0))
        for p in d.get("results", []):
            releases[p.get("uuid") or p.get("url")] = p
        page += 1
        if page * PAGESIZE >= total or not d.get("results"):
            break
        time.sleep(1.5)
    print(f"{kw!r}: {total} (razem unikalnych: {len(releases)})", flush=True)
    time.sleep(1.5)

with open(f"{OUT}/doj_raw.json", "w", encoding="utf-8") as f:
    json.dump(list(releases.values()), f, ensure_ascii=False)

cands = []
for p in releases.values():
    body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(p.get("body") or "")))
    forums = sorted({m.group(1) for m in FORUM_RE.finditer(body)} | {m.group(0) for m in FORUM_WORD.finditer(body)}, key=str.lower)
    aliases = sorted({m.group(1).strip() for m in ALIAS_RE.finditer(body)})
    if not forums or not aliases:
        continue
    state = sorted({m.group(1) for m in STATE_RE.finditer(body)}, key=str.lower)
    date = time.strftime("%Y-%m-%d", time.gmtime(int(p.get("date") or 0)))
    snippets = []
    for m in FORUM_RE.finditer(body):
        s, e = max(0, m.start() - 200), min(len(body), m.end() + 200)
        snippets.append(body[s:e])
        if len(snippets) >= 3:
            break
    cands.append({"date": date, "title": p.get("title"), "url": p.get("url"), "forums": forums,
                  "aliases": aliases, "state_markers": state, "snippets": snippets})

cands.sort(key=lambda c: c["date"])
with open(f"{OUT}/doj_kandydaci.json", "w", encoding="utf-8") as f:
    json.dump(cands, f, ensure_ascii=False, indent=1)
with open(f"{OUT}/doj_kandydaci.md", "w", encoding="utf-8") as f:
    for c in cands:
        f.write(f"## {c['date']} | {c['title']}\n{c['url']}\n- fora: {', '.join(c['forums'])}\n"
                f"- pseudonimy: {', '.join(c['aliases'])}\n- znaczniki państwowe: {', '.join(c['state_markers']) or '—'}\n\n")
print(f"\nKomunikatów: {len(releases)}; kandydatów (forum + pseudonim): {len(cands)}")
print(f"z markerami państwowymi: {sum(1 for c in cands if c['state_markers'])}")
