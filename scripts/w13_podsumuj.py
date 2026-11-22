"""Podsumowanie wyników W1.3/W1.4 (z scripts/w13_wstrzykiwanie.py) + kontrola wewnętrzna rankingu losowego.

Użycie:
    python -I -X utf8 scripts/w13_podsumuj.py dane/azsecure/w13_damagelab.csv [dane/azsecure/w13_rutor.csv ...]

Dla każdego (s, g/s, k, metoda): średnia precyzji w top-10 i AUC z 95% przedziałem (średnia ± 1,96·sd/√n) oraz moc =
odsetek powtórzeń z p < 0,05 (test hipergeometryczny dla top-10). Kontrola: metoda „losowy” musi mieć AUC ≈ 0,5
(przedział zawiera 0,5) i moc ≤ ~0,05 + szum; inaczej wypisuje OSTRZEŻENIE.
"""
import csv, math, sys
from collections import defaultdict

for plik in sys.argv[1:]:
    grupy = defaultdict(list)
    for r in csv.DictReader(open(plik, encoding="utf-8")):
        grupy[(int(r["s"]), int(r["g_na_czlonka"]), int(r["k"]), r["metoda"])].append(r)
    print(f"\n######## {plik}")
    print("s  g/s  k  metoda            P@10 (95% CI)        AUC (95% CI)         moc P@10  n")
    ostrz = []
    for (s, g, k, met), rows in sorted(grupy.items()):
        n = len(rows)
        def sr(kol):
            xs = [float(x[kol]) for x in rows]
            m = sum(xs) / n
            sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0
            return m, 1.96 * sd / math.sqrt(n)
        p10, e10 = sr("p10")
        auc, ea = sr("auc")
        moc = sum(float(x["pval10"]) < 0.05 for x in rows) / n
        print(f"{s:<3}{g:<5}{k:<3}{met:<17} {p10:.3f} ±{e10:.3f}      {auc:.3f} ±{ea:.3f}      {moc:.2f}     {n}")
        if met == "losowy" and (abs(auc - 0.5) > max(ea, 0.02) or moc > 0.12):
            ostrz.append(f"s={s} g/s={g} k={k}: AUC {auc:.3f}, moc {moc:.2f}")
    print("KONTROLA rankingu losowego:", "OK" if not ostrz else "OSTRZEŻENIE " + "; ".join(ostrz))
