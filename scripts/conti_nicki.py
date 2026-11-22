"""Lista pseudonimów z wycieku Conti w formacie pliku ziaren (jak dane/ziarna/ziarna_v0.csv) — do dopasowania W1.1
(scripts/w11_dopasuj_ziarna.py) z korpusami forów.

Użycie:
    python -I -X utf8 scripts/conti_nicki.py dane/conti/surowe dane/conti/conti_nicki.csv

Źródła nicków: węzły grafu Manatova i in. 2026 (301) + nazwy i aliasy z mapy „user match list” (scalanie aliasów —
tamże). Tier: wyciek = gold dla członkostwa (Design Proposal); data publiczna = data wycieku (2022-02-27).
"""
import csv, json, os, sys
import networkx as nx

surowe, wyj = sys.argv[1:3]
tekst = open(os.path.join(surowe, "graph_clusters.graphml"), encoding="utf-8").read()
assert "<!ENTITY" not in tekst and "<!DOCTYPE" not in tekst
G = nx.read_graphml(os.path.join(surowe, "graph_clusters.graphml"))
nicki = {n: n for n in G.nodes()}
for e in json.load(open(os.path.join(surowe, "user_match_list.json"), encoding="utf-8")):
    for a in [e.get("primary")] + e.get("aliases", []):
        if a:
            nicki.setdefault(a, e.get("primary"))
with open(wyj, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["nick", "grupa", "typ_grupy", "poziom", "tier", "zrodlo", "data_publiczna"])
    for n, p in sorted(nicki.items()):
        w.writerow([n, f"Conti (wyciek; {'w grafie' if n in G else 'alias ' + str(p)})", "finansowa", "L3", "gold",
                    "wyciek Conti 2022 (graf Manatova i in. 2026)", "2022-02-27"])
print(f"nicków: {len(nicki)} (w grafie: {sum(1 for n in nicki if n in G)})")
