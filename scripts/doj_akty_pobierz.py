"""Pobieranie aktów oskarżenia / skarg DOJ (PDF) z Wayback Machine według manifestu (URL, znacznik czasu, sha256).

Użycie:
    python -I -X utf8 scripts/doj_akty_pobierz.py scripts/expected/doj_akty.csv dane/doj_akty

Manifest: kolumny sprawa, plik, url_zrodlowy, wayback_timestamp, sha256 (tworzy go scripts/repo_eksport.py
z dane/doj_akty/MANIFEST.csv). Pliki trafiają do <katalog>/<sprawa>/<plik>, tylko do odczytu; sha256 musi się zgadzać
z manifestem (kod wyjścia 1 przy niezgodności). PDF-y są nieufne — skrypt niczego z nich nie uruchamia ani nie parsuje.
"""
import csv, hashlib, os, stat, sys, time, urllib.request

UA = {"User-Agent": "research-client"}


def http(url, timeout=300):
    for proba in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print(f"   błąd ({proba + 1}/4): {e}", flush=True)
            time.sleep(10 * (proba + 1))
    raise RuntimeError(f"nie udało się pobrać {url}")


def main():
    manifest, cel = sys.argv[1:3]
    zle = 0
    for r in csv.DictReader(open(manifest, encoding="utf-8")):
        kat = os.path.join(cel, r["sprawa"])
        os.makedirs(kat, exist_ok=True)
        lok = os.path.join(kat, r["plik"])
        if os.path.exists(lok):
            dane = open(lok, "rb").read()
        else:
            url = f"https://web.archive.org/web/{r['wayback_timestamp']}id_/{r['url_zrodlowy']}"
            print(f"== {r['sprawa']}/{r['plik']} <- {url}", flush=True)
            dane = http(url)
            with open(lok, "wb") as f:
                f.write(dane)
            os.chmod(lok, stat.S_IREAD)
        h = hashlib.sha256(dane).hexdigest()
        ok = h == r["sha256"]
        zle += not ok
        print(f"   {r['plik']}: {len(dane)} B, sha256 {'zgodny' if ok else 'NIEZGODNY ' + h[:16]}", flush=True)
    sys.exit(1 if zle else 0)


if __name__ == "__main__":
    main()
