"""Podsumowanie E6 (z scripts/e6_conti_wstrzykniecie.py) + kontrola wewnętrzna rankingu losowego.

Użycie:
    python -I -X utf8 scripts/e6_podsumuj.py dane/conti/e6_rutor.csv [dane/conti/e6_antichat.csv ...]

Dla każdego (scenariusz, widoczność, ziarna, metoda): średnie P@10, P@50, P@200 i AUC; 95% przedział dla P@50
(średnia ± 1,96·sd/√n); moc = odsetek powtórzeń z p < 0,05 (test hipergeometryczny) dla P@10 i P@50; średnia liczba
widocznych krawędzi wewnątrz grupy. Kontrola: metoda „losowy” — AUC w przedziale 0,5 ± max(CI, 0,02) i moc ≤ 0,12.
"""
import csv, math, sys
from collections import defaultdict

for plik in sys.argv[1:]:
    grupy = defaultdict(list)
    for r in csv.DictReader(open(plik, encoding="utf-8")):
        grupy[(r["scenariusz"], r["widocznosc"], r["ziarna"], r["metoda"])].append(r)
    print(f"\n######## {plik}")
    print(f"{'scen':<6}{'wid':<6}{'ziarna':<10}{'metoda':<24}{'P@10':>6}{'P@50 (95% CI)':>17}{'P@200':>7}{'AUC':>7}"
          f"{'moc10':>7}{'moc50':>7}{'kraw':>7}{'n':>5}")
    ostrz = []
    for (sc, wid, zi, met), rows in grupy.items():
        n = len(rows)
        def sr(kol):
            xs = [float(x[kol]) for x in rows]
            m = sum(xs) / n
            sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0
            return m, 1.96 * sd / math.sqrt(n)
        p10, _ = sr("p10")
        p50, e50 = sr("p50")
        p200, _ = sr("p200")
        auc, ea = sr("auc")
        kr, _ = sr("kraw_wew")
        moc10 = sum(float(x["pval10"]) < 0.05 for x in rows) / n
        moc50 = sum(float(x["pval50"]) < 0.05 for x in rows) / n
        print(f"{sc:<6}{wid:<6}{zi:<10}{met:<24}{p10:>6.3f}{p50:>9.3f} ±{e50:.3f}{p200:>7.3f}{auc:>7.3f}"
              f"{moc10:>7.2f}{moc50:>7.2f}{kr:>7.0f}{n:>5}")
        if met == "losowy" and (abs(auc - 0.5) > max(ea, 0.02) or moc10 > 0.12 or moc50 > 0.12):
            ostrz.append(f"{sc} {wid} {zi}: AUC {auc:.3f}, moc10 {moc10:.2f}, moc50 {moc50:.2f}")
    print("KONTROLA rankingu losowego:", "OK" if not ostrz else "OSTRZEŻENIE " + "; ".join(ostrz))
