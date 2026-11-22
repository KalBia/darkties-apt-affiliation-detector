"""E6 (Design Proposal 4.6): półsyntetyczne wstrzyknięcie PRAWDZIWEJ struktury komunikacji grupy (Conti) w graf
forum — rozszerzenie W1.3/W1.4 (scripts/w13_wstrzykiwanie.py, tryb „osadzony”). Metoda: docs/feasibility_tests_2026-11.md.

Źródła: struktura grupy — graf Manatova, McGrath, Camp (J. Cybersecurity 2026, tyag014), zweryfikowany i odbudowany
przez scripts/conti_struktura.py; osadzenie wśród istniejących person (planted partition) i zmiana gęstości
wewnętrznej (p_in) — Kloumann, Ugander, Kleinberg (arXiv:1607.03483); powtórzenia, AUC — SybilRank (NSDI 2012, §6.1);
PPR / stopień — SybilRank §4.3; baseline'y, precyzja w top-k (10, 50, 200), test permutacyjny — DP 4.4.1, 4.2.2.

Użycie:
    python -I -X utf8 scripts/e6_conti_wstrzykniecie.py dane/azsecure/grafy/rutor_eve_b.csv dane/conti/conti_krawedzie.csv dane/ziarna/ziarna_v0.csv dane/ziarna/conti_role_doj.txt dane/conti/e6_rutor.csv

conti_role_doj.txt — PRYWATNY plik (poza repozytorium): pseudonimy z rolami nazwanymi w komunikacie DOJ 2023-09-07,
jeden w wierszu (ziarna „doj_role4”).
Wybory bez źródła (oznaczone w raporcie): odwzorowanie członków na losowe persony forum; poziomy widoczności
relacji na forum (WIDOCZNOSC); scenariusz „30 członków na forum”.
"""
import csv, sys, time
import networkx as nx
import numpy as np
from scipy.stats import hypergeom, rankdata

WIDOCZNOSC = ["q1.0", "q0.5", "q0.2", "q0.1", "w5", "w20"]  # q = losowe zachowanie krawędzi; w = próg wagi
ALFY = [0.5, 0.85, 0.95]
POWT = 100  # SybilRank §6.1: 100 powtórzeń na scenariusz
SEED = 2026
TOPK = [10, 50, 200]


def wczytaj_gospodarza(sciezka):  # jak w w13_wstrzykiwanie.py
    G = nx.Graph()
    with open(sciezka, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_edge(r["zrodlo"], r["cel"])
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    return nx.convert_node_labels_to_integers(G)


def oceny(H, ziarna, rng):  # jak w w13_wstrzykiwanie.py
    n = H.number_of_nodes()
    wyniki = {}
    pers = {z: 1.0 for z in ziarna}
    for a in ALFY:
        pr = nx.pagerank(H, alpha=a, personalization=pers, tol=1e-8)
        wyniki[f"ppr_{a}"] = np.array([pr[i] for i in range(n)])
        if a == 0.85:
            wyniki["ppr_0.85_przez_stopien"] = np.array([pr[i] / max(H.degree(i), 1) for i in range(n)])
    dist = nx.multi_source_dijkstra_path_length(H, ziarna)
    wyniki["najkr_sciezka"] = np.array([-dist.get(i, 1e9) for i in range(n)], dtype=float)
    cn = np.zeros(n)
    for z in ziarna:
        for w in H[z]:
            for v in H[w]:
                cn[v] += 1
    wyniki["wspolni_sasiedzi"] = cn
    wyniki["stopien"] = np.array([H.degree(i) for i in range(n)], dtype=float)
    wyniki["losowy"] = rng.random(n)
    return wyniki


def widoczne(kraw, wid, rng):
    if wid.startswith("q"):
        q = float(wid[1:])
        return [(u, v) for u, v, _ in kraw if rng.random() < q]
    prog = int(wid[1:])
    return [(u, v) for u, v, w in kraw if w >= prog]


def main():
    global POWT
    wej, conti_csv, ziarna_csv, role_txt, wyj = sys.argv[1:6]
    if len(sys.argv) > 6:  # opcjonalnie liczba powtórzeń (np. 2 do testu dymnego)
        POWT = int(sys.argv[6])
    # pseudonimy z rolami nazwanymi w komunikacie DOJ 2023-09-07 — prywatny plik (jeden nick w wierszu), poza repozytorium
    role_doj = [x.strip().lower() for x in open(role_txt, encoding="utf-8") if x.strip()]
    G =wczytaj_gospodarza(wej)
    n0 = G.number_of_nodes()
    kraw = [(r["u"], r["v"], int(r["waga"])) for r in csv.DictReader(open(conti_csv, encoding="utf-8"))]
    czl = sorted({u for u, v, _ in kraw} | {v for u, v, _ in kraw})
    doj = sorted({r["nick"].lower() for r in csv.DictReader(open(ziarna_csv, encoding="utf-8"))
                  if "Conti" in r["grupa"]} & set(czl))
    print(f"gospodarz: {n0} węzłów, {G.number_of_edges()} krawędzi; Conti: {len(czl)} członków, {len(kraw)} krawędzi; "
          f"ziarna DOJ w grafie: {len(doj)} {doj}", flush=True)
    rng = np.random.default_rng(SEED)
    scen = {"cala": {"los1": 1, "los5": 5, "los10": 10, "doj_role4": role_doj, "doj10": doj},
            "los30": {"los1": 1, "los3": 3, "los5": 5}}
    st_conti = {}  # stopień w pełnym grafie Conti (przed ograniczeniem widoczności) — do analizy jakości ziaren
    for u, v, _ in kraw:
        st_conti[u] = st_conti.get(u, 0) + 1
        st_conti[v] = st_conti.get(v, 0) + 1
    pola = ["scenariusz", "widocznosc", "ziarna", "powt", "s", "kraw_wew", "st_ziaren_sr", "st_ziaren_max", "metoda", "auc"] + \
           [f"p{k}" for k in TOPK] + [f"pval{k}" for k in TOPK]
    with open(wyj, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=pola)
        wr.writeheader()
        for sc, zestawy in scen.items():
            for wid in WIDOCZNOSC:
                t0 = time.time()
                for r in range(POWT):
                    grupa_n = czl if sc == "cala" else sorted(rng.choice(czl, size=30, replace=False).tolist())
                    zb = set(grupa_n)
                    ew = [(u, v) for u, v in widoczne(kraw, wid, rng) if u in zb and v in zb]
                    mapa = dict(zip(grupa_n, (int(x) for x in rng.choice(n0, size=len(grupa_n), replace=False))))
                    H = G.copy()
                    H.add_edges_from((mapa[u], mapa[v]) for u, v in ew)
                    grupa = list(mapa.values())
                    for nazwa, z in zestawy.items():
                        zn = z if isinstance(z, list) else rng.choice(grupa_n, size=z, replace=False).tolist()
                        ziarna = [mapa[x] for x in zn]
                        pozyt = np.zeros(n0, dtype=bool)
                        pozyt[grupa] = True
                        kand = np.ones(n0, dtype=bool)
                        kand[ziarna] = False
                        y = pozyt[kand]
                        N, m = int(kand.sum()), int(y.sum())
                        for metoda, sco in oceny(H, ziarna, rng).items():
                            sco = sco[kand] + rng.random(N) * 1e-12
                            kol = np.argsort(-sco)
                            rk = rankdata(sco)
                            wiersz = {"scenariusz": sc, "widocznosc": wid, "ziarna": nazwa, "powt": r, "s": len(grupa),
                                      "kraw_wew": len(ew), "metoda": metoda,
                                      "st_ziaren_sr": round(float(np.mean([st_conti[x] for x in zn])), 2),
                                      "st_ziaren_max": max(st_conti[x] for x in zn),
                                      "auc": round((rk[y].sum() - m * (m + 1) / 2) / (m * (N - m)), 5)}
                            for k in TOPK:
                                h = int(y[kol[:k]].sum())
                                wiersz[f"p{k}"] = h / k
                                wiersz[f"pval{k}"] = hypergeom.sf(h - 1, N, m, k)
                            wr.writerow(wiersz)
                f.flush()
                print(f"{sc} {wid}: {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
