"""Pobieranie archiwalnych zbiorów AZSecure (fora hakerskie) z Wayback Machine (uzasadnienie: docs/feasibility_tests_2026-11.md).

Użycie:
    python -I -X utf8 scripts/azsecure_pobierz.py <katalog_docelowy> [nazwa_zbioru ...]
    np. python -I -X utf8 scripts/azsecure_pobierz.py dane/azsecure damagelab

Struktura: <katalog>/surowe/<zbior>/<plik> (tylko do odczytu) + <katalog>/MANIFEST.csv.
Bezpieczeństwo: pliki traktowane jako nieufne — skrypt niczego z nich nie uruchamia; ZIP jest tylko testowany
(zipfile.testzip) i listowany (nazwy, rozmiary), bez rozpakowywania.
"""
import csv, datetime, hashlib, json, os, stat, sys, time, urllib.parse, urllib.request, zipfile

BASE = "https://dibbs.ai.arizona.edu/dibbs/"
ZBIORY = {  # katalog na serwerze AZSecure -> opis
    "antichat": "AntiChat (RU)", "webkillforum": "Webkill (RU)", "xakepokforum": "Xakepok (RU)",
    "damagelab": "DamageLab (RU)", "exetoolsforum": "ExeTools (EN)", "crackingarenaforum": "CrackingArena (EN)",
    "hackhoundforum": "HackHound (EN)", "crackingfireforum": "CrackingFire (EN)", "garage4hackers": "Garage4Hackers (EN)",
    "darknetforums": "Dark Net Forums 2019 (EN/RU)",
}
UA = {"User-Agent": "research-client"}
POLA = ["zbior", "plik", "url_zrodlowy", "wayback_timestamp", "pobrano_utc", "rozmiar_B", "sha256", "zip_ok", "zawartosc"]


def http(url, timeout=600):
    for proba in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print(f"   błąd ({proba + 1}/4): {e}", flush=True)
            time.sleep(15 * (proba + 1))
    raise RuntimeError(f"nie udało się pobrać {url}")


def kopie(zbior):
    """Najnowsza kopia ze statusem 200 dla każdego pliku w katalogu zbioru (CDX API)."""
    q = urllib.parse.urlencode({"url": f"dibbs.ai.arizona.edu/dibbs/{zbior}/*", "output": "json",
                                "fl": "original,timestamp,statuscode", "filter": "statuscode:200"})
    rows = json.loads(http("https://web.archive.org/cdx/search/cdx?" + q))[1:]
    najnowsze = {}
    for orig, ts, _ in rows:
        nazwa = orig.rsplit("/", 1)[-1]
        if nazwa and (nazwa not in najnowsze or ts > najnowsze[nazwa][1]):
            najnowsze[nazwa] = (orig, ts)
    return najnowsze


def main():
    cel = sys.argv[1]
    wybrane = sys.argv[2:] or list(ZBIORY)
    manifest = os.path.join(cel, "MANIFEST.csv")
    stare = {}
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8", newline="") as f:
            stare = {(r["zbior"], r["plik"]): r for r in csv.DictReader(f)}
    for zbior in wybrane:
        assert zbior in ZBIORY, f"nieznany zbiór {zbior}"
        print(f"== {zbior}: {ZBIORY[zbior]}", flush=True)
        katalog = os.path.join(cel, "surowe", zbior)
        os.makedirs(katalog, exist_ok=True)
        for nazwa, (orig, ts) in sorted(kopie(zbior).items()):
            sciezka = os.path.join(katalog, nazwa)
            if os.path.exists(sciezka) and (zbior, nazwa) in stare:
                print(f"   {nazwa}: już jest — pomijam")
                continue
            dane = http(f"https://web.archive.org/web/{ts}id_/{orig}")
            sha = hashlib.sha256(dane).hexdigest()
            tmp = sciezka + ".part"
            with open(tmp, "wb") as f:
                f.write(dane)
            zip_ok, zawartosc = "", ""
            if nazwa.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(tmp) as z:
                        zly = z.testzip()
                        zip_ok = "tak" if zly is None else f"NIE ({zly})"
                        zawartosc = "; ".join(f"{i.filename} ({i.file_size} B)" for i in z.infolist())
                except zipfile.BadZipFile as e:
                    zip_ok = f"NIE ({e})"
            os.replace(tmp, sciezka)
            os.chmod(sciezka, stat.S_IREAD)  # tylko do odczytu
            stare[(zbior, nazwa)] = {"zbior": zbior, "plik": nazwa, "url_zrodlowy": orig, "wayback_timestamp": ts,
                                     "pobrano_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                     "rozmiar_B": len(dane), "sha256": sha, "zip_ok": zip_ok, "zawartosc": zawartosc}
            print(f"   {nazwa}: {len(dane)} B, sha256 {sha[:12]}, zip_ok={zip_ok or '-'} {zawartosc[:150]}", flush=True)
            with open(manifest, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=POLA)
                w.writeheader()
                w.writerows(sorted(stare.values(), key=lambda r: (r["zbior"], r["plik"])))
            time.sleep(5)
        time.sleep(5)


if __name__ == "__main__":
    main()
