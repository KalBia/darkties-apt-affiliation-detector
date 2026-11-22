"""W1.2: graf odpowiedzi per forum wg Characterizing Eve (Pastrana i in., RAID 2018, sekcja 4.2), wariant (b):
krawędź V -> W, gdy V odpowiada w wątku założonym przez W. Autor wątku = autor postu o najmniejszym post_seq
(przy remisie — najmniejszy rowid). Waga = liczba odpowiedzi. Bez pętli własnych i bez postów bez autora.

Użycie:
    python -I -X utf8 scripts/w12_graf.py dane/azsecure/azsecure.sqlite dane/azsecure/grafy dane/azsecure/w12_graf.txt NICK@FORUM [...]

Zapisuje listy krawędzi <forum>_eve_b.csv (zrodlo, cel, waga) i raport. Fora bez użytecznych wątków (exetools, webkill)
są pomijane — profil: scripts/w12_profil_struktury.py.
"""
import csv, os, sqlite3, sys
from collections import defaultdict
import networkx as nx

POMIN = {"exetools": "brak thread_id", "webkill": "96% wątków jednopostowych"}
OBCIETE = {"crackingfire", "hackhound", "antichat"}  # skok liczby wątków na 20 postach (w12 kontrola obcięcia)

db, kat, wyj, kandydaci = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
os.makedirs(kat, exist_ok=True)
con = sqlite3.connect(db)
kand = defaultdict(list)
for k in kandydaci:
    nick, forum = k.rsplit("@", 1)
    kand[forum].append(nick)
out = []
for (forum,) in con.execute("SELECT DISTINCT forum FROM posty ORDER BY forum"):
    if forum in POMIN:
        out.append(f"\n===== {forum}: POMINIĘTE ({POMIN[forum]})")
        continue
    autor_watku, remisy = {}, 0
    for tid, autor, n_min in con.execute(
            "SELECT p.thread_id, p.author, (SELECT COUNT(*) FROM posty q WHERE q.forum=p.forum AND q.thread_id=p.thread_id "
            "AND q.post_seq=p.post_seq) FROM posty p WHERE p.forum=? AND p.rowid = (SELECT r.rowid FROM posty r WHERE "
            "r.forum=p.forum AND r.thread_id=p.thread_id ORDER BY r.post_seq, r.rowid LIMIT 1)", (forum,)):
        autor_watku[tid] = autor
        remisy += n_min > 1
    G = nx.DiGraph()
    autorzy = set()
    for tid, autor in con.execute("SELECT thread_id, author FROM posty WHERE forum=? AND author IS NOT NULL AND author<>''",
                                  (forum,)):
        autorzy.add(autor)
        w = autor_watku.get(tid)
        if not w or w == autor:
            continue
        if G.has_edge(autor, w):
            G[autor][w]["waga"] += 1
        else:
            G.add_edge(autor, w, waga=1)
    with open(os.path.join(kat, f"{forum}_eve_b.csv"), "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["zrodlo", "cel", "waga"])
        wr.writerows((u, v, d["waga"]) for u, v, d in G.edges(data=True))
    n_aut, n_wez = len(autorzy), G.number_of_nodes()
    wcc = max(nx.weakly_connected_components(G), key=len) if n_wez else set()
    out.append(f"\n===== {forum}{'  [UWAGA: wątki obcięte]' if forum in OBCIETE else ''}")
    out.append(f"  autorów {n_aut}; węzłów z krawędzią {n_wez}; izolowanych {n_aut - n_wez} ({100*(n_aut-n_wez)/max(n_aut,1):.1f}%)")
    out.append(f"  krawędzi {G.number_of_edges()}; suma wag {sum(d['waga'] for *_, d in G.edges(data=True))}; "
               f"gęstość {nx.density(G):.2e}; wzajemność {nx.reciprocity(G) if n_wez else 0:.3f}")
    out.append(f"  największa słabo spójna składowa: {len(wcc)} ({100*len(wcc)/max(n_wez,1):.1f}% węzłów); "
               f"wątków z remisem post_seq na początku: {remisy}")
    if kand.get(forum):
        stop = sorted((G.in_degree(n) + G.out_degree(n) for n in G), reverse=True)
        low = {n.lower(): n for n in G}
        for nick in kand[forum]:
            n = low.get(nick.lower())
            if n is None:
                out.append(f"  kandydat {nick}: izolowany lub brak w grafie")
                continue
            st = G.in_degree(n) + G.out_degree(n)
            pct = 100 * sum(1 for x in stop if x > st) / len(stop)
            out.append(f"  kandydat {nick}: in {G.in_degree(n)}, out {G.out_degree(n)}, stopień {st} "
                       f"(top {pct:.1f}%), w największej składowej: {n in wcc}")
tekst = "\n".join(out)
open(wyj, "w", encoding="utf-8").write(tekst)
print(tekst)
