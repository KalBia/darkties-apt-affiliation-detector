"""Pobieranie danych z wycieku Conti (2022) z repozytorium pracy Manatova, McGrath, Camp (J. Cybersecurity 2026,
doi:10.1093/cybsec/tyag014) — uzasadnienie: docs/feasibility_tests_2026-11.md. Repozytorium przypięte do commita (odtwarzalność).

Użycie:
    python -I -X utf8 scripts/conti_pobierz.py <katalog_docelowy>
    np. python -I -X utf8 scripts/conti_pobierz.py dane/conti

Pobiera tylko: graf końcowy z pracy (graphml), mapę aliasów, listę użytkowników i dwa logi czatów (Jabber + „chat”),
z których praca zbudowała graf. NIE pobiera: plików .pkl (pickle uruchamia kod przy wczytaniu), logów Rocket.Chat
(praca nie używa ich do grafu), dokumentów wewnętrznych grupy ani kodu.
Struktura: <katalog>/surowe/<plik> (tylko do odczytu) + <katalog>/MANIFEST.csv (sha256).
Bezpieczeństwo: pliki nieufne — skrypt niczego z nich nie uruchamia ani nie parsuje.
"""
import csv, datetime, hashlib, os, stat, sys, time, urllib.parse, urllib.request

REPO = "dalyapraz/conti-org-analysis"
COMMIT = "73222516ebf963fcca6fb0dc7e452fc8ebf0967f"  # main z 2026-07-06 (sprawdzone przez API GitHuba 2026-11-20)
PLIKI = [  # ścieżka w repozytorium -> nazwa lokalna
    ("analysis/structure/graph_clusters.graphml", "graph_clusters.graphml"),
    ("data/logs/user match list.json", "user_match_list.json"),
    ("data/user_lists/users.txt", "users.txt"),
    ("data/user_lists/users_clean.txt", "users_clean.txt"),
    ("data/logs/jabber_logs.json", "jabber_logs.json"),
    ("data/logs/chat_logs.json", "chat_logs.json"),
]
UA = {"User-Agent": "research-client"}
POLA = ["plik", "url_zrodlowy", "commit", "pobrano_utc", "rozmiar_B", "sha256"]


def http(url, timeout=600):
    for proba in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print(f"   błąd ({proba + 1}/4): {e}", flush=True)
            time.sleep(10 * (proba + 1))
    raise RuntimeError(f"nie udało się pobrać {url}")


def main():
    cel = sys.argv[1]
    katalog = os.path.join(cel, "surowe")
    os.makedirs(katalog, exist_ok=True)
    wiersze = []
    for sciezka, nazwa in PLIKI:
        url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{urllib.parse.quote(sciezka)}"
        lok = os.path.join(katalog, nazwa)
        if os.path.exists(lok):
            print(f"== {nazwa}: już jest, pomijam pobieranie", flush=True)
            dane = open(lok, "rb").read()
        else:
            print(f"== {nazwa} <- {url}", flush=True)
            dane = http(url)
            if dane[:15].lower().startswith(b"<!doctype html"):
                raise RuntimeError(f"{nazwa}: serwer zwrócił stronę HTML zamiast pliku")
            with open(lok, "wb") as f:
                f.write(dane)
            os.chmod(lok, stat.S_IREAD)
        wiersze.append({"plik": nazwa, "url_zrodlowy": url, "commit": COMMIT,
                        "pobrano_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "rozmiar_B": len(dane), "sha256": hashlib.sha256(dane).hexdigest()})
        print(f"   {len(dane)} B, sha256 {wiersze[-1]['sha256'][:16]}…", flush=True)
    with open(os.path.join(cel, "MANIFEST.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=POLA)
        w.writeheader()
        w.writerows(wiersze)
    print(f"MANIFEST: {len(wiersze)} plików", flush=True)


if __name__ == "__main__":
    main()
