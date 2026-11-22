"""W1.1 (eksploracyjnie): dopasowanie nicków ziaren do autorów w bazie AZSecure.

Użycie:
    python -I -X utf8 scripts/w11_dopasuj_ziarna.py dane/ziarna/ziarna_v0.csv dane/azsecure/azsecure.sqlite dane/azsecure/w11_dopasowania.csv

Dopasowanie: dokładne (bez wielkości liter) i po normalizacji (tylko litery i cyfry, min. 3 znaki).
Kolumna `autorow_o_tej_nazwie` = ilu różnych par (forum, autor) w całym korpusie ma tę samą znormalizowaną nazwę —
prosta miara pospolitości nicka (im więcej, tym słabszy dowód tożsamości; por. Perito i in. 2011).
Wypisuje tylko nicki i liczby, nie treść postów.
"""
import csv, re, sqlite3, sys
from collections import defaultdict

norm = lambda s: re.sub(r"[^0-9a-zа-яё]", "", (s or "").lower())
ziarna_csv, db, wyj = sys.argv[1:4]
seeds = list(csv.DictReader(open(ziarna_csv, encoding="utf-8")))
con = sqlite3.connect(db)
autorzy = con.execute("SELECT forum, author, COUNT(*), MIN(post_date_raw), MAX(post_date_raw) FROM posty "
                      "WHERE author IS NOT NULL AND author<>'' GROUP BY forum, author").fetchall()
idx_e, idx_n = defaultdict(list), defaultdict(list)
for r in autorzy:
    idx_e[r[1].strip().lower()].append(r)
    idx_n[norm(r[1])].append(r)
rows = []
for s in seeds:
    e = idx_e.get(s["nick"].strip().lower(), [])
    nn = [x for x in idx_n.get(norm(s["nick"]), []) if x not in e] if len(norm(s["nick"])) >= 3 else []
    for typ, lst in (("dokladne", e), ("normalizacja", nn)):
        for forum, a, n, d0, d1 in lst:
            rows.append({"nick_ziarna": s["nick"], "grupa": s["grupa"], "typ_grupy": s["typ_grupy"], "dopasowanie": typ,
                         "forum": forum, "autor": a, "postow": n, "data_min_surowa": str(d0).strip(),
                         "data_max_surowa": str(d1).strip(), "autorow_o_tej_nazwie": len(idx_n.get(norm(s["nick"]), [])),
                         "dlugosc_nicka": len(norm(s["nick"]))})
with open(wyj, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["brak"])
    w.writeheader()
    w.writerows(rows)
trafione = len({r["nick_ziarna"] for r in rows})
print(f"par forum-autor w korpusie: {len(autorzy)}; ziaren: {len(seeds)}; ziaren z trafieniem: {trafione}; wierszy: {len(rows)}")
