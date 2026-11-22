"""Analiza wyników E6 (z scripts/e6_conti_wstrzykniecie.py): porównanie sparowane metod, oś „widoczny stopień
wewnętrzny”, jakość ziaren, powtarzalność.

Użycie:
    python -I -X utf8 scripts/e6_analiza.py dane/conti/e6_analiza.txt dane/conti/e6_rutor_v2.csv dane/conti/e6_antichat.csv --conti dane/conti/conti_krawedzie.csv --powt dane/conti/e6_rutor.csv dane/conti/e6_rutor_v2.csv

A. Porównanie sparowane (te same powtórzenia = ten sam graf, odwzorowanie i ziarna): różnica P@50 metody PPR i najkrótszej
   ścieżki (baseline DP 4.4.1). Test: permutacyjny ze zmianą znaków różnic (Fisher randomization test; DP 4.2.2 — test
   permutacyjny; ranx `compare()` — Bassani, ECIR 2022), 20 000 permutacji, dwustronny. Rodzina = wszystkie porównania
   „PPR vs najkrótsza ścieżka” w E6 (2 warianty PPR × wszystkie konfiguracje × fora), ustalona przed analizą; korekta
   Holma (FWER; Holm 1979).
B. Oś wspólna: P@10 dla 5 losowych ziaren w funkcji średniego widocznego stopnia wewnętrznego (2·krawędzie/s) —
   do zestawienia z grupą syntetyczną W1.3 (s = 30, k = 5).
C. Jakość ziaren (gdy jest kolumna st_ziaren_sr): korelacja Spearmana stopnia ziarna w grafie Conti z P@50 (1 losowe
   ziarno), osobno dla każdej widoczności.
D. Powtarzalność (--powt A B): czy wspólne kolumny obu plików są identyczne.
E. Mechanizm (--conti krawędzie): odsetek członków bez żadnej widocznej więzi przy danej widoczności.
"""
import csv, sys
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr

NPERM, SEED = 20000, 2026
METODY_PPR = ["ppr_0.5", "ppr_0.85_przez_stopien"]
BASE = "najkr_sciezka"


def wczytaj(plik):
    return list(csv.DictReader(open(plik, encoding="utf-8")))


def perm_test(d, rng):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    znaki = rng.choice([-1.0, 1.0], size=(NPERM, len(d)))
    return (1 + int((np.abs((znaki * d).mean(axis=1)) >= obs - 1e-15).sum())) / (NPERM + 1)


def holm(p):
    p = np.asarray(p)
    kol = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for i, j in enumerate(kol):
        run = max(run, (m - i) * p[j])
        adj[j] = min(run, 1.0)
    return adj


def main():
    wyj, pliki = sys.argv[1], []
    powt = None
    a = sys.argv[2:]
    conti = None
    if "--conti" in a:
        i = a.index("--conti")
        conti = a[i + 1]
        a = a[:i] + a[i + 2:]
    if "--powt" in a:
        i = a.index("--powt")
        powt = a[i + 1:i + 3]
        a = a[:i]
    pliki = a
    rng = np.random.default_rng(SEED)
    out = open(wyj, "w", encoding="utf-8")
    def log(*x):
        s = " ".join(str(y) for y in x)
        print(s, flush=True)
        out.write(s + "\n")

    # A
    testy = []
    for plik in pliki:
        idx = defaultdict(dict)
        for r in wczytaj(plik):
            idx[(r["scenariusz"], r["widocznosc"], r["ziarna"])].setdefault(r["metoda"], {})[int(r["powt"])] = float(r["p50"])
        for kfg, m in idx.items():
            for met in METODY_PPR:
                rep = sorted(set(m[met]) & set(m[BASE]))
                d = [m[met][x] - m[BASE][x] for x in rep]
                testy.append((plik.rsplit("/", 1)[-1], *kfg, met, float(np.mean(d)), float(np.mean(np.array(d) > 0)),
                              perm_test(d, rng)))
    adj = holm([t[-1] for t in testy])
    log("## A. PPR vs najkrótsza ścieżka — różnica P@50 (sparowana), test permutacyjny, Holm na", len(testy), "testów")
    for met in METODY_PPR:
        sel = [(t, q) for t, q in zip(testy, adj) if t[4] == met]
        lep = sum(1 for t, q in sel if q < 0.05 and t[5] > 0)
        gor = sum(1 for t, q in sel if q < 0.05 and t[5] < 0)
        log(f"{met}: istotnie lepszy w {lep}/{len(sel)}, istotnie gorszy w {gor}/{len(sel)}, "
            f"mediana różnicy {np.median([t[5] for t, _ in sel]):+.3f}")
        for t, q in sel:
            if not (q < 0.05 and t[5] > 0):
                log(f"   bez przewagi: {t[0]} {t[1]} {t[2]} {t[3]}: różnica {t[5]:+.3f}, wygrane {t[6]:.2f}, p_Holm {q:.3g}")

    # B
    log("\n## B. P@10 (5 losowych ziaren) vs średni widoczny stopień wewnętrzny 2·kraw/s")
    log(f"{'plik':<20}{'scen':<7}{'wid':<6}{'st.wew':>8}{'PPR/st P@10':>13}{'PPR0.5 P@10':>13}{'najkr P@10':>12}")
    for plik in pliki:
        g = defaultdict(list)
        for r in wczytaj(plik):
            if r["ziarna"] == "los5":
                g[(r["scenariusz"], r["widocznosc"], r["metoda"])].append(r)
        for (sc, wid, met) in sorted(k for k in g if k[2] == "ppr_0.85_przez_stopien"):
            rr = g[(sc, wid, met)]
            st = np.mean([2 * float(x["kraw_wew"]) / float(x["s"]) for x in rr])
            p = lambda mm: np.mean([float(x["p10"]) for x in g[(sc, wid, mm)]])
            log(f"{plik.rsplit('/', 1)[-1]:<20}{sc:<7}{wid:<6}{st:>8.2f}{p('ppr_0.85_przez_stopien'):>13.3f}"
                f"{p('ppr_0.5'):>13.3f}{p(BASE):>12.3f}")

    # C
    log("\n## C. Jakość ziaren: Spearman(stopień ziarna w Conti, P@50), 1 losowe ziarno, scenariusz „cała”")
    for plik in pliki:
        rows = [r for r in wczytaj(plik) if r["scenariusz"] == "cala" and r["ziarna"] == "los1"]
        if not rows or "st_ziaren_sr" not in rows[0]:
            continue
        for met in ["ppr_0.5", "ppr_0.85_przez_stopien", BASE]:
            for wid in ["q1.0", "q0.5", "q0.2", "q0.1", "w5", "w20"]:
                rr = [r for r in rows if r["metoda"] == met and r["widocznosc"] == wid]
                st = np.array([float(r["st_ziaren_sr"]) for r in rr])
                p = np.array([float(r["p50"]) for r in rr])
                rho, pv = spearmanr(st, p)
                hi, lo = p[st >= 20].mean() if (st >= 20).any() else float("nan"), p[st <= 3].mean() if (st <= 3).any() else float("nan")
                log(f"{plik.rsplit('/', 1)[-1]:<20}{met:<24}{wid:<6} rho {rho:+.2f} (p {pv:.2g}); P@50 ziarno st ≥ 20: {hi:.2f} "
                    f"(n {(st >= 20).sum()}), st ≤ 3: {lo:.2f} (n {(st <= 3).sum()})")

    # D
    if powt:
        a1, a2 = wczytaj(powt[0]), wczytaj(powt[1])
        wsp = [k for k in a1[0] if k in a2[0]]
        rozne = sum(1 for x, y in zip(a1, a2) if any(x[k] != y[k] for k in wsp))
        log(f"\n## D. Powtarzalność: {powt[0]} vs {powt[1]}: wierszy {len(a1)} / {len(a2)}, wspólnych kolumn {len(wsp)}, "
            f"wierszy różnych: {rozne}")
    # E
    if conti:
        kr = [(r["u"], r["v"], int(r["waga"])) for r in csv.DictReader(open(conti, encoding="utf-8"))]
        deg = defaultdict(int)
        for u, v, _ in kr:
            deg[u] += 1
            deg[v] += 1
        d = np.array(list(deg.values()))
        log("\n## E. Mechanizm: członkowie Conti bez żadnej widocznej więzi (nieosiągalni dla metod grafowych)")
        for q in (1.0, 0.5, 0.2, 0.1):
            log(f"q {q}: odsetek izolowanych (oczekiwany, średnia (1-q)^stopień) {np.mean((1 - q) ** d):.2f}; śr. stopień {q * d.mean():.2f}")
        for w in (5, 20):
            dw = defaultdict(int)
            for u, v, x in kr:
                if x >= w:
                    dw[u] += 1
                    dw[v] += 1
            log(f"waga ≥ {w}: izolowanych {1 - len(dw) / len(deg):.2f}; śr. stopień {sum(dw.values()) / len(deg):.2f}")
        czl, r2, iz = sorted(deg), np.random.default_rng(SEED), []
        for _ in range(500):
            s, dd = set(r2.choice(czl, 30, replace=False).tolist()), set()
            for u, v, _ in kr:
                if u in s and v in s:
                    dd.update((u, v))
            iz.append(1 - len(dd) / 30)
        log(f"30 losowych członków, pełna widoczność: izolowanych średnio {np.mean(iz):.2f} (500 losowań)")
        log("(grupa syntetyczna W1.3 — graf regularny d: izolowanych 0)")
    out.close()


if __name__ == "__main__":
    main()
