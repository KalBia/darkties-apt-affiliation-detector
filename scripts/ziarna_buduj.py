"""Budowa listy ziaren v0 (pseudonimy z atrybucji urzędowej DOJ) — W0.2.

Użycie:
    python -I -X utf8 scripts/ziarna_buduj.py dane/doj_2026-11-17/doj_kandydaci.json dane/ziarna/ziarna_reczne.csv dane/ziarna/ziarna_v0.csv

Wejścia:
- doj_kandydaci.json — wynik scripts/doj_sweep.py (komunikaty DOJ z pseudonimami);
- ziarna_reczne.csv — PRYWATNY plik (poza repozytorium) z pozycjami zweryfikowanymi ręcznie w komunikatach i aktach
  oskarżenia; kolumny: nick, grupa, typ_grupy, poziom, tier, zrodlo, data_publiczna. Prawdziwe pseudonimy nie trafiają
  do publicznego repozytorium — format i źródła opisuje docs/reproduction.md.
Infraud i GozNym: pseudonimy z komunikatów (tylko jednowyrazowe — bez imion i nazwisk).
"""
import csv, json, re, sys

src_json, reczne_csv, out_csv = sys.argv[1:4]
POLA = ["nick", "grupa", "typ_grupy", "poziom", "tier", "zrodlo", "data_publiczna"]
R = [{k: r[k] for k in POLA} for r in csv.DictReader(open(reczne_csv, encoding="utf-8"))]


def add(nicks, grupa, typ, poziom, tier, zrodlo, data):
    for n in nicks:
        R.append({"nick": n, "grupa": grupa, "typ_grupy": typ, "poziom": poziom, "tier": tier, "zrodlo": zrodlo,
                  "data_publiczna": data})


for c in json.load(open(src_json, encoding="utf-8")):
    if "Thirty-six Defendants" in c["title"] or "Thirty-Six Defendants" in c["title"]:
        grupa, data, src = "Infraud", "2018-02-07", "komunikat DOJ 2018-02-07"
    elif "GozNym" in c["title"] or "GOZNYM" in c["title"]:
        grupa, data, src = "GozNym", "2019-05-16", "komunikat DOJ 2019-05-16"
    else:
        continue
    nicks = {re.sub(r"[,;.]+$", "", a).strip() for a in c["aliases"]}
    add(sorted(n for n in nicks if n and " " not in n), grupa, "finansowa", "L3", "gold", src, data)

seen, out = set(), []
for r in R:
    k = (r["nick"].lower(), r["grupa"])
    if k not in seen:
        seen.add(k)
        out.append(r)
with open(out_csv, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=POLA)
    w.writeheader()
    w.writerows(out)
print(f"ziaren: {len(out)}")
