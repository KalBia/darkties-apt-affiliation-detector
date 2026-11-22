"""Normalizacja dat postów AZSecure do ISO (W1.2, gotchy G10) + kontrole.

Użycie:
    python -I -X utf8 scripts/azsecure_daty.py dane/azsecure/azsecure.sqlite

Tworzy (od nowa) tabelę `daty(rid INTEGER PRIMARY KEY, data_iso TEXT, dokladnosc TEXT, wzgledna INTEGER)`,
gdzie rid = rowid z tabeli `posty`. dokladnosc: dzien | minuta | sekunda. Daty względne („Yesterday”, „Сегодня”,
„только что”, dzień tygodnia „Пятница в 12:00”) kotwiczone na najpóźniejszej dacie bezwzględnej danego forum
(przybliżenie daty zebrania — ReadMe nie podają dokładnej daty; wybór bez źródła = [Predykcja]), wzgledna=1.
Formaty NN-NN-RRRR czytane jako MM-DD (vBulletin, US) — potwierdzane kontrolą w wyjściu skryptu.
Wypisuje: pokrycie parsowania per forum, nieznane wzorce, kontrolę MM-DD vs DD-MM, kontrolę obcięcia wątków.
"""
import datetime as dt, re, sqlite3, sys
from collections import Counter, defaultdict

EN = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
RU_KR = {m: i + 1 for i, m in enumerate(["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"])}
RU_DOP = {m: i + 1 for i, m in enumerate(["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
                                          "сентября", "октября", "ноября", "декабря"])}
WZGL = {"today": 0, "yesterday": 1, "сегодня": 0, "вчера": 1, "только что": 0}


def h12(h, ampm):
    h = int(h)
    if ampm:
        ampm = ampm.lower()
        if ampm == "pm" and h != 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
    return h


def parsuj(s):
    """Zwraca (datetime | None, dokladnosc, offset_dni_wzgl | None, kolejnosc_md)."""
    s = re.sub(r"\s+", " ", str(s or "")).strip().lower()
    s = re.sub(r"<.*$", "", s).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})", s)
    if m:
        y, mo, d, H, M, S = map(int, m.groups())
        return dt.datetime(y, mo, d, H, M, S), "sekunda", None, None
    m = re.fullmatch(r"(\d{1,2})\.(\d{2})\.(\d{4})(?:, (\d{1,2}):(\d{2}))?", s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        if m[4]:
            return dt.datetime(y, mo, d, int(m[4]), int(m[5])), "minuta", None, None
        return dt.datetime(y, mo, d), "dzien", None, None
    m = re.fullmatch(r"(\d{1,2}) ([a-z]{3}) (\d{4})", s)
    if m and m[2] in EN:
        return dt.datetime(int(m[3]), EN[m[2]], int(m[1])), "dzien", None, None
    m = re.fullmatch(r"(\d{1,2}) ([а-я]{3})\.? (\d{4})", s)
    if m and m[2] in RU_KR:
        return dt.datetime(int(m[3]), RU_KR[m[2]], int(m[1])), "dzien", None, None
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4}),(?:\s?(\d{1,2}):(\d{2})\s?(am|pm)?)?", s)
    if m:  # vBulletin US: MM-DD-YYYY (sprawdzane kontrolą kolejności)
        mo, d, y = int(m[1]), int(m[2]), int(m[3])
        if m[4]:
            return dt.datetime(y, mo, d, h12(m[4], m[6]), int(m[5])), "minuta", None, (m[1], m[2])
        return dt.datetime(y, mo, d), "dzien", None, (m[1], m[2])
    m = re.fullmatch(r"([a-z]{3})[a-z]* (\d{1,2})(?:st|nd|rd|th)?, (\d{4}),? (?:at )?(\d{1,2}):(\d{2}) ?(am|pm)", s)
    if m and m[1] in EN:
        return dt.datetime(int(m[3]), EN[m[1]], int(m[2]), h12(m[4], m[6]), int(m[5])), "minuta", None, None
    m = re.fullmatch(r"([а-я]+) (\d{1,2}), (\d{4}), (\d{1,2}):(\d{2}):(\d{2}) ?(am|pm)", s)
    if m and m[1] in RU_DOP:
        return dt.datetime(int(m[3]), RU_DOP[m[1]], int(m[2]), h12(m[4], m[7]), int(m[5]), int(m[6])), "sekunda", None, None
    m = re.fullmatch(r"(today|yesterday|сегодня|вчера|только что),?\s?(?:(?:at |в )?(\d{1,2}):(\d{2})(?::(\d{2}))?\s?(am|pm)?)?", s)
    if m:
        t = (h12(m[2], m[5]), int(m[3])) if m[2] else (0, 0)
        return t, ("minuta" if m[2] else "dzien"), WZGL[m[1]], None
    m = re.fullmatch(r"(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье),? в (\d{1,2}):(\d{2})", s)
    if m:  # dzień tygodnia = ostatni taki dzień przed kotwicą
        return (int(m[2]), int(m[3])), "minuta", ("dt", DNI_RU.index(m[1])), None
    return None, None, None, None


DNI_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def main():
    db = sys.argv[1]
    con = sqlite3.connect(db)
    con.execute("DROP TABLE IF EXISTS daty")
    con.execute("CREATE TABLE daty (rid INTEGER PRIMARY KEY, data_iso TEXT, dokladnosc TEXT, wzgledna INTEGER)")
    wyn, wzgl, nieznane = [], [], defaultdict(Counter)
    kolej = defaultdict(lambda: [0, 0])  # forum -> [pierwsze>12, drugie>12]
    maks = {}
    for rid, forum, s in con.execute("SELECT rowid, forum, post_date_raw FROM posty"):
        d, dok, off, md = parsuj(s)
        if md:
            kolej[forum][0] += int(md[0]) > 12
            kolej[forum][1] += int(md[1]) > 12
        if d is None:
            nieznane[forum][re.sub(r"\d", "9", re.sub(r"\s+", " ", str(s)).strip())[:40]] += 1
            wyn.append((rid, None, None, 0))
        elif off is not None:
            wzgl.append((rid, forum, d, dok, off))
        else:
            wyn.append((rid, d.isoformat(), dok, 0))
            if forum not in maks or d > maks[forum]:
                maks[forum] = d
    for rid, forum, (H, M), dok, off in wzgl:
        kotw = maks.get(forum)
        if kotw is None:
            wyn.append((rid, None, None, 1))
            continue
        if isinstance(off, tuple):  # ("dt", dzień tygodnia 0=pon)
            off = (kotw.weekday() - off[1]) % 7
        d = (kotw - dt.timedelta(days=off)).replace(hour=H, minute=M, second=0)
        wyn.append((rid, d.isoformat(), dok, 1))
    con.executemany("INSERT INTO daty VALUES (?,?,?,?)", wyn)
    con.commit()

    print("forum | postów | sparsowanych | względnych | nieparsowalnych | zakres dat")
    for forum, n, ok, wz, mn, mx in con.execute(
            "SELECT p.forum, COUNT(*), SUM(d.data_iso IS NOT NULL), SUM(d.wzgledna), MIN(d.data_iso), MAX(d.data_iso) "
            "FROM posty p JOIN daty d ON d.rid=p.rowid GROUP BY p.forum ORDER BY p.forum"):
        print(f"{forum:15s} {n:>7} {ok:>7} ({100*ok/n:5.1f}%) {wz:>5} {n-ok:>6}  {str(mn)[:10]} … {str(mx)[:10]}")
    print("\nkontrola kolejności NN-NN-RRRR (ile razy pierwsze / drugie pole > 12):")
    for f, (a, b) in kolej.items():
        print(f"  {f}: pierwsze>12 {a}, drugie>12 {b}  -> {'MM-DD (OK)' if a == 0 and b > 0 else 'SPRAWDZIĆ'}")
    if nieznane:
        print("\nnieparsowalne wzorce (top):")
        for f, c in nieznane.items():
            print(f"  {f}: {c.most_common(4)}")
    print("\nkontrola obcięcia wątków (liczba wątków o długości 18, 19, 20, 21):")
    for f in ("crackingfire", "hackhound", "antichat", "rutor"):
        dl = Counter(r[0] for r in con.execute(
            "SELECT COUNT(*) FROM posty WHERE forum=? GROUP BY thread_id", (f,)))
        print(f"  {f}: {[dl.get(k, 0) for k in (18, 19, 20, 21)]}")


if __name__ == "__main__":
    main()
