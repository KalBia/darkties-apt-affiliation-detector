"""W1.1 (b0): profil metadanych kandydatów na ziarna — bez treści postów.

Użycie:
    python -I -X utf8 scripts/w11_b0_metadane.py dane/azsecure/azsecure.sqlite dane/azsecure/w11_b0_metadane.txt NICK@FORUM [NICK@FORUM ...]

Dla każdej pary (autor, forum): liczba postów, ranga, data dołączenia, zakres dat (surowych), top subfora i top tytuły
wątków. Dopasowanie autora bez wielkości liter.
"""
import sqlite3, sys
from collections import Counter

db, wyj, pary = sys.argv[1], sys.argv[2], sys.argv[3:]
con = sqlite3.connect(db)
out = []
for p in pary:
    nick, forum = p.rsplit("@", 1)
    rows = con.execute("SELECT author, subforum, thread_title, post_date_raw, author_membership, author_join_date, "
                       "author_reputation FROM posty WHERE forum=? AND lower(author)=lower(?)", (forum, nick)).fetchall()
    out.append(f"\n===== {nick} @ {forum}: {len(rows)} postów")
    if not rows:
        continue
    autorzy = Counter(r[0] for r in rows)
    out.append(f"  autor(zy): {dict(autorzy)}")
    out.append(f"  ranga: {Counter(r[4] for r in rows).most_common(2)}; dołączył: {Counter(r[5] for r in rows).most_common(2)}; "
               f"reputacja: {Counter(r[6] for r in rows).most_common(2)}")
    daty = sorted(str(r[3]).strip() for r in rows if r[3])
    out.append(f"  daty (surowe, posortowane tekstowo — tylko orientacyjnie): {daty[:3]} … {daty[-3:]}")
    out.append(f"  subfora: {Counter(r[1] for r in rows).most_common(5)}")
    for t, n in Counter(r[2] for r in rows).most_common(8):
        out.append(f"    [{n}] {str(t)[:110]}")
tekst = "\n".join(out)
open(wyj, "w", encoding="utf-8").write(tekst)
print(tekst)
