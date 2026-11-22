"""W1.3/W1.4: półsyntetyczny test rankingu od ziaren — metoda: docs/feasibility_tests_2026-11.md.

Źródła: wstrzyknięcie grupy (graf regularny d=4, g losowych krawędzi do gospodarza, wiele powtórzeń, AUC) —
Cao i in., SybilRank, NSDI 2012, §6.1; ranking od ziaren i PPR — Kloumann, Ugander, Kleinberg (arXiv:1607.03483);
baseline'y (najkrótsza ścieżka, wspólni sąsiedzi, centralność), precyzja w top-k i test permutacyjny — Design
Proposal 4.4.1 i 4.2.2. P-wartość dla precyzji w top-k = rozkład hipergeometryczny (dokładny test permutacyjny).

Użycie:
    python -I -X utf8 scripts/w13_wstrzykiwanie.py dane/azsecure/grafy/rutor_eve_b.csv dane/azsecure/w13_rutor.csv
    python -I -X utf8 scripts/w13_wstrzykiwanie.py dane/azsecure/grafy/damagelab_eve_b.csv dane/azsecure/w13_damagelab.csv 1,3,10,30,100
    python -I -X utf8 scripts/w13_wstrzykiwanie.py dane/azsecure/grafy/damagelab_eve_b.csv dane/azsecure/w13_damagelab_osadzony.csv 1,2,4 osadzony

Parametry (s, g/s, k, alfa, powtórzenia) w stałych poniżej — wybory bez źródła oznaczone [Predykcja] w notatce.
"""
import csv, sys, time
import networkx as nx
import numpy as np
from scipy.stats import hypergeom, rankdata

S_LIST = [10, 30]          # rozmiar grupy [Predykcja]
G_RATIO = [1, 3, 10]       # krawędzi do gospodarza na członka [Predykcja]
K_LIST = [1, 3, 5, 10]     # liczba ziaren [Predykcja]
ALFY = [0.5, 0.85, 0.95]   # PPR: prawdopodobieństwo kontynuacji spaceru (NetworkX alpha) — wrażliwość
D = 4                      # SybilRank §6.1
POWT = 50                  # SybilRank: 100 — redukcja [Predykcja]
SEED = 2026


def wczytaj(sciezka):
    G = nx.Graph()
    with open(sciezka, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_edge(r["zrodlo"], r["cel"])
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    return nx.convert_node_labels_to_integers(G)


def oceny(H, ziarna, rng):
    n = H.number_of_nodes()
    wyniki = {}
    pers = {z: 1.0 for z in ziarna}
    for a in ALFY:
        pr = nx.pagerank(H, alpha=a, personalization=pers, tol=1e-8)
        wyniki[f"ppr_{a}"] = np.array([pr[i] for i in range(n)])
        if a == 0.85:  # normalizacja stopniem — SybilRank §4.3 („eliminating the node degree bias”)
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


def main():
    global G_RATIO
    wej, wyj = sys.argv[1:3]
    if len(sys.argv) > 3:  # opcjonalnie: lista g/s, np. 30,100 (SybilRank: g zwiększane do degradacji)
        G_RATIO = [int(x) for x in sys.argv[3].split(",")]
    # tryb: "dolaczony" (domyślnie; nowe węzły + g krawędzi, SybilRank) albo "osadzony" (grupa = s istniejących
    # person gospodarza + d wewnętrznych krawędzi na członka; planted partition, Kloumann i in.). W trybie
    # osadzonym kolumna g_na_czlonka oznacza d (wewnętrzny stopień grupy), a lista z argv[3] — wartości d.
    tryb = sys.argv[4] if len(sys.argv) > 4 else "dolaczony"
    G = wczytaj(wej)
    n0 = G.number_of_nodes()
    print(f"gospodarz: {n0} węzłów, {G.number_of_edges()} krawędzi (największa składowa)", flush=True)
    rng = np.random.default_rng(SEED)
    pola = ["s", "g_na_czlonka", "k", "powt", "metoda", "p10", "p50", "auc", "pval10", "pval50"]
    with open(wyj, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=pola)
        wr.writeheader()
        for s in S_LIST:
            for gr in G_RATIO:
                for k in K_LIST:
                    if k >= s:
                        continue
                    t0 = time.time()
                    for r in range(POWT):
                        H = G.copy()
                        if tryb == "osadzony":
                            grupa = [int(x) for x in rng.choice(n0, size=s, replace=False)]
                            wew = nx.random_regular_graph(gr, s, seed=int(rng.integers(1 << 30)))
                            H.add_edges_from((grupa[u], grupa[v]) for u, v in wew.edges())
                        else:
                            grupa = list(range(n0, n0 + s))
                            wew = nx.random_regular_graph(D, s, seed=int(rng.integers(1 << 30)))
                            H.add_edges_from((n0 + u, n0 + v) for u, v in wew.edges())
                            for _ in range(gr * s):
                                H.add_edge(int(rng.choice(grupa)), int(rng.integers(n0)))
                        ziarna = [int(x) for x in rng.choice(grupa, size=k, replace=False)]
                        pozyt = np.zeros(H.number_of_nodes(), dtype=bool)
                        pozyt[grupa] = True
                        kand = np.ones(H.number_of_nodes(), dtype=bool)
                        kand[ziarna] = False
                        y = pozyt[kand]
                        N, m = int(kand.sum()), int(y.sum())
                        for metoda, sc in oceny(H, ziarna, rng).items():
                            sc = sc[kand] + rng.random(N) * 1e-12  # losowe rozstrzyganie remisów
                            kol = np.argsort(-sc)
                            h10, h50 = int(y[kol[:10]].sum()), int(y[kol[:50]].sum())
                            rk = rankdata(sc)
                            auc = (rk[y].sum() - m * (m + 1) / 2) / (m * (N - m))
                            wr.writerow({"s": s, "g_na_czlonka": gr, "k": k, "powt": r, "metoda": metoda,
                                         "p10": h10 / 10, "p50": h50 / 50, "auc": round(auc, 5),
                                         "pval10": hypergeom.sf(h10 - 1, N, m, 10), "pval50": hypergeom.sf(h50 - 1, N, m, 50)})
                    print(f"s={s} g/s={gr} k={k}: {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
