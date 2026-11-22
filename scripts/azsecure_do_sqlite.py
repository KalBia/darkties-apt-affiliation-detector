"""Konwersja zrzutów AZSecure (MySQL dump / CSV w ZIP) do jednej bazy SQLite z ujednoliconą tabelą `posty`.

Użycie:
    python -I -X utf8 scripts/azsecure_do_sqlite.py dane/azsecure

Czyta strumieniowo z dane/azsecure/surowe/*/*.zip (bez rozpakowywania na dysk), zapisuje dane/azsecure/azsecure.sqlite.
Dane traktowane jako nieufne: tylko parsowanie tekstu, nic nie jest wykonywane. Pomijana jest kolumna HTML.
"""
import csv, glob, io, os, re, sqlite3, sys, time, zipfile

POLA = ["forum", "post_id", "thread_id", "thread_title", "subforum", "author", "author_join_date",
        "author_membership", "author_reputation", "post_date_raw", "post_seq", "content_flat"]
MAPA = {  # nazwa kolumny w źródle (małe litery) -> pole ujednolicone
    "postid": "post_id", "threadid": "thread_id", "threadtitle": "thread_title", "subforum": "subforum",
    "authorname": "author", "postauthorjoindate": "author_join_date", "postauthormembership": "author_membership",
    "authorreputation": "author_reputation", "postdate": "post_date_raw", "postdatetime": "post_date_raw",
    "postsequence": "post_seq", "flatcontent": "content_flat",
}
TOKEN = re.compile(r"'(?:[^'\\]|\\.)*'|NULL|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?|\(|\)|,", re.S)
ESC = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a", "b": "\b"}


def sql_str(tok):
    s = tok[1:-1]
    return re.sub(r"\\(.)", lambda m: ESC.get(m.group(1), m.group(1)), s, flags=re.S)


def wartosc(tok):
    if tok == "NULL":
        return None
    if tok[0] == "'":
        return sql_str(tok)
    return int(tok) if re.fullmatch(r"-?\d+", tok) else float(tok)


def wiersze_sql(f):
    """Generator słowników z instrukcji INSERT w zrzucie MySQL (tekst strumieniowy)."""
    kolumny = None
    bufor = ""
    for linia in f:
        if kolumny is None or linia.startswith("CREATE TABLE"):
            bufor += linia
            if linia.strip().endswith(";") and "CREATE TABLE" in bufor:
                kolumny = re.findall(r"^\s*`(\w+)`\s+\w+", bufor, re.M)
                bufor = ""
            elif not linia.startswith("CREATE TABLE") and "CREATE TABLE" not in bufor:
                bufor = ""
            continue
        if not linia.startswith("INSERT INTO"):
            continue
        tekst = linia[linia.index("VALUES") + 6:]
        while not tekst.rstrip().endswith(";"):  # instrukcja rozbita na wiele linii
            nast = next(f, None)
            if nast is None:
                break
            tekst += nast
        rek, gleb = [], 0
        for m in TOKEN.finditer(tekst):
            t = m.group(0)
            if t == "(":
                gleb += 1
                if gleb == 1:
                    rek = []
            elif t == ")":
                gleb -= 1
                if gleb == 0:
                    yield dict(zip([k.lower() for k in kolumny], rek))
            elif t == ",":
                continue
            elif gleb == 1:
                rek.append(wartosc(t))


def wiersze_csv(f):
    csv.field_size_limit(2**31 - 1)
    for r in csv.DictReader(f):
        yield {k.lower(): (v if v != "" else None) for k, v in r.items() if k}


def ujednolic(forum, r):
    out = {p: None for p in POLA}
    out["forum"] = forum
    for k, v in r.items():
        if k in MAPA and out[MAPA[k]] is None:
            out[MAPA[k]] = v
    return out


def main():
    cel = sys.argv[1]
    db = os.path.join(cel, "azsecure.sqlite")
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.execute(f"CREATE TABLE posty ({', '.join(POLA)})")
    con.execute("CREATE TABLE zrodla (forum, plik_zip, czlonek, format, liczba_postow)")
    for z in sorted(glob.glob(os.path.join(cel, "surowe", "*", "*.zip"))):
        with zipfile.ZipFile(z) as zf:
            czlonkowie = [m for m in zf.infolist() if m.filename.lower().endswith((".sql", ".csv"))]
            # gdy ten sam zbiór jest jako CSV i SQL — bierzemy CSV (prostszy format)
            nazwy = {os.path.splitext(m.filename)[0] for m in czlonkowie if m.filename.lower().endswith(".csv")}
            czlonkowie = [m for m in czlonkowie if not (m.filename.lower().endswith(".sql") and os.path.splitext(m.filename)[0] in nazwy)]
            for m in czlonkowie:
                forum = os.path.splitext(os.path.basename(m.filename))[0].lower().replace("posts", "")
                fmt = "csv" if m.filename.lower().endswith(".csv") else "sql"
                t0, n = time.time(), 0
                with zf.open(m) as raw:
                    f = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="" if fmt == "csv" else None)
                    gen = wiersze_csv(f) if fmt == "csv" else wiersze_sql(f)
                    partia = []
                    for r in gen:
                        u = ujednolic(forum, r)
                        partia.append(tuple(u[p] for p in POLA))
                        if len(partia) >= 5000:
                            con.executemany(f"INSERT INTO posty VALUES ({','.join('?' * len(POLA))})", partia)
                            n += len(partia)
                            partia = []
                    con.executemany(f"INSERT INTO posty VALUES ({','.join('?' * len(POLA))})", partia)
                    n += len(partia)
                con.execute("INSERT INTO zrodla VALUES (?,?,?,?,?)", (forum, os.path.relpath(z, cel), m.filename, fmt, n))
                con.commit()
                print(f"{forum:16s} {fmt}  postów: {n:>9,}  ({time.time() - t0:.0f} s)", flush=True)
    print("indeksy…", flush=True)
    con.execute("CREATE INDEX i_autor ON posty(forum, author)")
    con.execute("CREATE INDEX i_watek ON posty(forum, thread_id, post_seq)")
    con.execute("CREATE INDEX i_autor_lower ON posty(lower(author))")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
