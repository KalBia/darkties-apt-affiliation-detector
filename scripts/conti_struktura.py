"""E6 / etykiety: struktura komunikacji grupy Conti — weryfikacja grafu z literatury, odbudowa z logów, spójność,
pseudonimy z aktów DOJ. Metoda budowy grafu: Manatova, McGrath, Camp, „The organizational anatomy of cybercrime”,
J. Cybersecurity 12(1) 2026, tyag014, sekcja „Construction of the social graph” + kod autorów (functions.py,
commit 73222516): aliasy scalane wg „user match list”, wiadomości łączone w pary użytkowników, usunięte rozmowy
jednostronne i „glitch” (echo do nadawcy), graf nieskierowany, waga = liczba jednostek rozmowy (próg τ dynamiczny:
τmin = 30 min, τmax = 12 h, 90. percentyl odstępów; ≤ 4 odstępy → τmin).

Użycie:
    python -I -X utf8 scripts/conti_struktura.py dane/conti/surowe dane/ziarna/ziarna_v0.csv dane/conti

Wyjście: <out>/conti_krawedzie.csv (u, v, waga — z grafu autorów), <out>/conti_struktura.txt (raport).
Bezpieczeństwo: treść wiadomości używana tylko do porównań (glitch, „zaszyfrowane”) — nigdy nie wypisywana.
"""
import csv, json, os, sys
from collections import Counter, defaultdict
from datetime import datetime
import networkx as nx
import numpy as np

TABELA1 = {"nodes": 301, "edges": 1456, "avg_degree": 9.67, "max_degree": 145, "min_degree": 1,
           "avg_w_degree": 126.50, "max_w_degree": 4227, "min_w_degree": 1, "total_weight": 19039,
           "components": 1, "avg_shortest_path": 2.56, "density": 0.03, "diameter": 44, "avg_clustering": 0.43}
ETAPY_PRACY = {"historie_par": 2426, "dwustronne": 1490, "po_glitch": 1456, "uzytkownicy": 301, "jednostki": 19039}
SZYFR = "[Ошибка: сообщение зашифровано, и невозможно его расшифровать.]"
TAU_MIN, TAU_MAX, P = 30 * 60, 12 * 3600, 90


def log(f, *a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    f.write(s + "\n")


def graf_autorow(surowe, f):
    sc = os.path.join(surowe, "graph_clusters.graphml")
    tekst = open(sc, encoding="utf-8").read()
    assert "<!ENTITY" not in tekst and "<!DOCTYPE" not in tekst, "graphml z deklaracjami encji — nie parsuję"
    G = nx.read_graphml(sc)
    G = nx.Graph(G)
    st = [d for _, d in G.degree()]
    wst = [d for _, d in G.degree(weight="weight")]
    lcc = G.subgraph(max(nx.connected_components(G), key=len))
    obl = {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "avg_degree": round(np.mean(st), 2),
           "max_degree": max(st), "min_degree": min(st), "avg_w_degree": round(np.mean(wst), 2),
           "max_w_degree": max(wst), "min_w_degree": min(wst), "total_weight": int(sum(w for *_, w in G.edges(data="weight"))),
           "components": nx.number_connected_components(G), "avg_shortest_path": round(nx.average_shortest_path_length(lcc), 2),
           "density": round(nx.density(G), 3), "diameter": nx.diameter(lcc), "avg_clustering": round(nx.average_clustering(G), 2)}
    log(f, "\n## A. Graf autorów (graph_clusters.graphml) vs Tabela 1 pracy")
    log(f, f"{'miara':<20}{'Tabela 1':>10}{'plik':>10}  zgodne")
    for k, v in TABELA1.items():
        tol = 0.011 if isinstance(v, float) else 0
        ok = abs(obl[k] - v) <= tol
        log(f, f"{k:<20}{v:>10}{obl[k]:>10}  {'TAK' if ok else 'NIE'}")
    log(f, "atrybuty grafu zapisane w pliku:", {k: G.graph.get(k) for k in ("diameter", "avg_shortest_path", "density")})
    return G


def odbuduj(surowe, f):
    alias = {}
    for e in json.load(open(os.path.join(surowe, "user_match_list.json"), encoding="utf-8")):
        if e.get("primary"):
            alias[e["primary"]] = e["primary"]
            for a in e.get("aliases", []):
                alias[a] = e["primary"]
    pary = defaultdict(list)
    n_wiad = 0
    for fn in ("chat_logs.json", "jabber_logs.json"):
        for m in json.load(open(os.path.join(surowe, fn), encoding="utf-8")):
            n_wiad += 1
            s, r = alias.get(m["from"], m["from"]), alias.get(m["to"], m["to"])
            k = tuple(sorted([s, r]))
            pary[k].append((datetime.fromisoformat(m["ts"]), s, r, m["body"]))
    for k in pary:
        pary[k].sort(key=lambda x: x[0])
    log(f, "\n## B. Odbudowa z surowych logów (metoda pracy) — porównanie etapów")
    log(f, f"wiadomości: {n_wiad}; aliasów w mapie: {len(alias)}")
    dwu = {k: v for k, v in pary.items() if len({x[1] for x in v}) > 1}
    def glitch(k, v):
        a, b = k
        if len(v) == 2:
            return v[0][1] == a and v[1][1] == b and v[0][3] == v[1][3]
        if len(v) == 4:
            return (v[0][1] == a and v[1][1] == a and v[2][1] == b and v[3][1] == b
                    and v[0][3] == v[2][3] and v[1][3] == v[3][3])
        return False
    bez_g = {k: v for k, v in dwu.items() if not glitch(k, v)}
    bez_sz = {k: [x for x in v if x[3] != SZYFR] for k, v in bez_g.items()}
    bez_sz = {k: v for k, v in bez_sz.items() if v}
    uz = {u for k in bez_g for u in k}
    jedn = {}
    for k, v in bez_sz.items():
        dt = np.array([(v[i][0] - v[i - 1][0]).total_seconds() for i in range(1, len(v))])
        tau = TAU_MIN if len(dt) <= 4 else min(max(np.percentile(dt, P), TAU_MIN), TAU_MAX)
        jedn[k] = 1 + int((dt > tau).sum())
    wyn = {"historie_par": len(pary), "dwustronne": len(dwu), "po_glitch": len(bez_g), "uzytkownicy": len(uz),
           "jednostki": sum(jedn.values())}
    for k, v in ETAPY_PRACY.items():
        log(f, f"{k:<14} praca {v:>6}  odbudowa {wyn[k]:>6}  {'TAK' if v == wyn[k] else 'NIE'}")
    samo = sum(1 for k in pary if k[0] == k[1])
    log(f, f"(pary „sam ze sobą”: {samo}; wiadomości „zaszyfrowane”: {sum(len(v) for v in bez_g.values()) - sum(len(v) for v in bez_sz.values())})")
    return jedn


def spojnosc(G, f):
    log(f, "\n## C. Spójność grupy (pytanie z W1.3: ile wewnętrznych połączeń ma członek?)")
    st = np.array([d for _, d in G.degree()])
    log(f, f"stopień: mediana {np.median(st):.0f}, kwartyle {np.percentile(st, 25):.0f}/{np.percentile(st, 75):.0f}; "
           f"odsetek ≥1: {np.mean(st >= 1):.2f}, ≥2: {np.mean(st >= 2):.2f}, ≥4: {np.mean(st >= 4):.2f}, ≥10: {np.mean(st >= 10):.2f}")
    rdz = nx.core_number(G)
    log(f, "rdzenie k (k: liczba węzłów w k-rdzeniu):", {k: sum(1 for v in rdz.values() if v >= k) for k in (1, 2, 3, 4, 6, 10, 15, 20)})
    for w in (1, 2, 5, 10, 20):
        H = nx.Graph([(u, v) for u, v, x in G.edges(data="weight") if x >= w])
        if H.number_of_nodes() == 0:
            continue
        lcc = max(nx.connected_components(H), key=len)
        log(f, f"krawędzie z wagą ≥ {w:>2}: {H.number_of_edges():>5}, węzłów {H.number_of_nodes():>3}, "
               f"śr. stopień {2 * H.number_of_edges() / H.number_of_nodes():.2f}, największa składowa {len(lcc)}")


def doj(G, ziarna_csv, f):
    log(f, "\n## D. Pseudonimy z aktów DOJ (2023-09-07) w grafie Conti")
    st, wst = dict(G.degree()), dict(G.degree(weight="weight"))
    niski = {n.lower(): n for n in G.nodes()}
    for r in csv.DictReader(open(ziarna_csv, encoding="utf-8")):
        if "Conti" not in r["grupa"]:
            continue
        n = niski.get(r["nick"].lower())
        if n is None:
            log(f, f"{r['nick']:<10} — brak w grafie")
        else:
            log(f, f"{r['nick']:<10} węzeł „{n}”: stopień {st[n]}, stopień ważony {wst[n]}, klaster GMM {G.nodes[n].get('gmm_cluster')}")


def main():
    surowe, ziarna_csv, out = sys.argv[1:4]
    with open(os.path.join(out, "conti_struktura.txt"), "w", encoding="utf-8") as f:
        log(f, "# Conti — struktura komunikacji (scripts/conti_struktura.py)")
        G = graf_autorow(surowe, f)
        jedn = odbuduj(surowe, f)
        zgodne = sum(1 for (u, v), w in jedn.items() if G.has_edge(u, v) and G[u][v]["weight"] == w)
        log(f, f"wagi krawędzi: odbudowa = plik autorów dla {zgodne} / {G.number_of_edges()} krawędzi")
        spojnosc(G, f)
        doj(G, ziarna_csv, f)
    with open(os.path.join(out, "conti_krawedzie.csv"), "w", encoding="utf-8", newline="") as g:
        w = csv.writer(g)
        w.writerow(["u", "v", "waga"])
        for u, v, x in G.edges(data="weight"):
            w.writerow([u, v, x])


if __name__ == "__main__":
    main()
