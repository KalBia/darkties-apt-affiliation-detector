"""W1.2 krok 1: profil struktury danych AZSecure per forum (bez treści postów).

Użycie:
    python -I -X utf8 scripts/w12_profil_struktury.py dane/azsecure/azsecure.sqlite dane/azsecure/w12_profil_struktury.txt

Dla każdego forum: braki thread_id / author / post_seq, rozkład liczby postów w wątku, odsetek wątków jednopostowych,
duplikaty post_seq w wątku, wzorce formatów dat (cyfry -> 9, litery łacińskie -> a, cyrylica -> я).
"""
import re, sqlite3, statistics, sys
from collections import Counter

db, wyj = sys.argv[1:3]
con = sqlite3.connect(db)


def wzorzec(s):
    s = re.sub(r"\s+", " ", str(s)).strip()
    s = re.sub(r"\d", "9", s)
    s = re.sub(r"[A-Za-z]", "a", s)
    s = re.sub(r"[А-Яа-яЁё]", "я", s)
    return re.sub(r"a+", "a", re.sub(r"я+", "я", s))


out = []
for (forum,) in con.execute("SELECT DISTINCT forum FROM posty ORDER BY forum"):
    n, bez_watku, bez_autora, bez_seq = con.execute(
        "SELECT COUNT(*), SUM(thread_id IS NULL), SUM(author IS NULL OR author=''), SUM(post_seq IS NULL) "
        "FROM posty WHERE forum=?", (forum,)).fetchone()
    rozm = [r[0] for r in con.execute(
        "SELECT COUNT(*) FROM posty WHERE forum=? AND thread_id IS NOT NULL GROUP BY thread_id", (forum,))]
    dup = con.execute("SELECT COUNT(*) FROM (SELECT thread_id, post_seq FROM posty WHERE forum=? AND thread_id IS NOT NULL "
                      "AND post_seq IS NOT NULL GROUP BY thread_id, post_seq HAVING COUNT(*)>1)", (forum,)).fetchone()[0]
    wz = Counter(wzorzec(r[0]) for r in con.execute("SELECT post_date_raw FROM posty WHERE forum=?", (forum,)))
    out.append(f"\n===== {forum}: postów {n}")
    out.append(f"  braki: thread_id {bez_watku} ({100*bez_watku/n:.1f}%), autor {bez_autora} ({100*bez_autora/n:.1f}%), "
               f"post_seq {bez_seq} ({100*bez_seq/n:.1f}%)")
    if rozm:
        out.append(f"  wątków {len(rozm)}; postów/wątek: mediana {statistics.median(rozm)}, średnia {statistics.mean(rozm):.2f}, "
                   f"max {max(rozm)}; jednopostowych {sum(1 for x in rozm if x == 1)} ({100*sum(1 for x in rozm if x == 1)/len(rozm):.1f}%)")
    out.append(f"  duplikaty (thread_id, post_seq): {dup}")
    out.append(f"  formaty dat (top 8 z {len(wz)}):")
    for w, c in wz.most_common(8):
        out.append(f"    {c:>7}  {w[:60]!r}")
tekst = "\n".join(out)
open(wyj, "w", encoding="utf-8").write(tekst)
print(tekst)
