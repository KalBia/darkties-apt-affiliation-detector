"""Weryfikacja kopii katalogu danych (np. po przeniesieniu do zaszyfrowanego kontenera): porównanie sha256 każdego pliku + zgodność z manifestami.

Użycie:
    python -I -X utf8 scripts/weryfikuj_kopie.py dane dane_kopia
(pierwszy argument: katalog źródłowy, drugi: katalog kopii, np. w zamontowanym kontenerze)

Kod wyjścia 0 = wszystko zgodne; 1 = rozbieżności (wypisane).
Manifesty: azsecure/MANIFEST.csv (kolumny zbior, plik, sha256 -> surowe/<zbior>/<plik>),
           doj_akty/MANIFEST.csv (kolumny sprawa, plik, sha256 -> <sprawa>/<plik>).
"""
import csv, hashlib, os, sys


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def drzewo(root):
    out = {}
    for d, _, pliki in os.walk(root):
        for n in pliki:
            p = os.path.join(d, n)
            out[os.path.relpath(p, root).replace("\\", "/")] = p
    return out


src, dst = sys.argv[1], sys.argv[2]
A, B = drzewo(src), drzewo(dst)
bledy = []
for k in sorted(set(A) - set(B)):
    bledy.append(f"brak w kopii: {k}")
for k in sorted(set(B) - set(A)):
    bledy.append(f"nadmiarowy w kopii: {k}")
zgodne = 0
for k in sorted(set(A) & set(B)):
    if sha(A[k]) != sha(B[k]):
        bledy.append(f"różna treść: {k}")
    else:
        zgodne += 1
print(f"plików: źródło {len(A)}, kopia {len(B)}, identycznych {zgodne}")

for man, klucz, sciezka in (("azsecure/MANIFEST.csv", "zbior", "azsecure/surowe/{}/{}"),
                            ("doj_akty/MANIFEST.csv", "sprawa", "doj_akty/{}/{}")):
    mp = os.path.join(dst, man)
    if not os.path.exists(mp):
        bledy.append(f"brak manifestu w kopii: {man}")
        continue
    n = 0
    for r in csv.DictReader(open(mp, encoding="utf-8")):
        p = os.path.join(dst, sciezka.format(r[klucz], r["plik"]))
        if not os.path.exists(p):
            bledy.append(f"{man}: brak pliku {p}")
        elif sha(p) != r["sha256"]:
            bledy.append(f"{man}: sha256 niezgodne {p}")
        else:
            n += 1
    print(f"{man}: zgodnych z manifestem {n}")

if bledy:
    print("ROZBIEŻNOŚCI:")
    print("\n".join(bledy))
    sys.exit(1)
print("WSZYSTKO ZGODNE")
