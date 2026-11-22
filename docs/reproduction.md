# Reproducing the feasibility tests (November 2026)

This guide re-creates, from public sources, the data and every number in
[`docs/feasibility_tests_2026-11.md`](feasibility_tests_2026-11.md). The repository contains **code, checksums and
aggregate numbers only** — no forum data, no leaked chats and no real pseudonyms. You download the data yourself;
`scripts/reproduce.py` then checks that you got exactly the same files and results.

## 1. Before you start — handling the data

The data includes underground-forum posts, leaked criminal chats (with victims' information) and indictments with
names. Please follow the team's rules:

- Keep the data directory **outside version control**. `dane/` and `data/` are git-ignored; never `git add -f` them.
- Prefer an **encrypted container** (we use a VeraCrypt file container mounted as a drive, with `dane/` pointing into
  it). Unmount it when not working.
- Downloaded archives and documents are made read-only by the download scripts. **Never execute anything from the data** and do not open the
  dumps in tools that run macros or scripts. The scripts run Python in isolated mode (`-I`) so that a downloaded
  file cannot shadow a Python module; pickle files are never downloaded.
- Do **not** send raw posts or chat contents to external LLM APIs (pending the supervisor's decision on data-use terms).
- Do not commit outputs that contain pseudonyms (match tables, candidate lists, edge lists).

## 2. Requirements

- Python 3.12 (tested: 3.12.7, Windows 10) and `pip install -r requirements.txt` (networkx, numpy, scipy; the rest is
  the standard library).
- About 2 GB of free disk space (a full run used 1.7 GB, of which the SQLite corpus is 1.4 GB), network access to `justice.gov` (API only),
  `web.archive.org` and `raw.githubusercontent.com`.
- Run all commands from the repository root.

## 3. Private inputs (not in the repository)

Four small files contain real pseudonyms and are shared inside the team only (not by e-mail to third parties). Put
them in `dane/ziarna/`. Steps that need a missing file are skipped with a message; everything else still runs.

| File | Content | Format |
|---|---|---|
| `ziarna_reczne.csv` | seeds verified by hand in DOJ press releases and indictments (60 rows; sources: access-broker indictment 2:18-cr-00303 W.D. Wash.; DOJ releases on DanaBot 2025-05-22, APT27/i-Soon 2025-03-05, Yahoo/FSB 2017-03-15, Thanos 2022-05-16, TrickBot/Conti 2023-09-07 and others listed in the `zrodlo` column) | CSV with columns `nick,grupa,typ_grupy,poziom,tier,zrodlo,data_publiczna` — e.g. `example_nick,ExampleGroup,finansowa,L3,gold,komunikat DOJ 2023-09-07,2023-09-07` |
| `conti_role_doj.txt` | the 4 personas whose roles are named in the DOJ TrickBot/Conti release of 2023-09-07 | one pseudonym per line, lower case |
| `kandydaci_b0.txt` (optional) | candidates for the metadata review (W1.1 b0) | one `NICK@forum` per line |
| `kandydaci_w12.txt` (optional) | candidates whose degree is reported in the graph statistics (W1.2) | one `NICK@forum` per line |

The Infraud and GozNym seeds are extracted automatically from the DOJ releases; only the hand-checked ones are private.

## 4. One command

```
python scripts/reproduce.py --data-dir dane
```

This runs four step groups and stops at the first failing step. Times were measured on a full run from an empty data
directory (2026-11-22, Windows 10, data on an encrypted volume; AZSecure archives already present, so their 271 MB
download is not included; the DOJ API sweep was not timed):

| Group | Step | Script | Output in `dane/` | Approx. time |
|---|---|---|---|---|
| download | DOJ press releases | `doj_sweep.py` | `doj_2026-11-17/` | not measured |
| download | AZSecure archives (Wayback) | `azsecure_pobierz.py` | `azsecure/surowe/`, `azsecure/MANIFEST.csv` (271 MB) | not measured |
| download | Conti leak (paper repository, pinned commit) | `conti_pobierz.py` | `conti/surowe/` (44 MB) | ~1.5 min together with the AZSecure step when the archives are already present |
| download | DOJ indictments (Wayback) | `doj_akty_pobierz.py` | `doj_akty/` | ~25 s |
| build | SQLite corpus | `azsecure_do_sqlite.py` | `azsecure/azsecure.sqlite` | ~1.5 min together with the next step |
| build | date normalisation | `azsecure_daty.py` | table `daty` | (see above) |
| build | seed list | `ziarna_buduj.py` | `ziarna/ziarna_v0.csv` | < 1 s |
| build | Conti graph check and rebuild | `conti_struktura.py` | `conti/conti_struktura.txt`, `conti/conti_krawedzie.csv` | ~1 s |
| build | Conti name list | `conti_nicki.py` | `conti/conti_nicki.csv` | ~1 s |
| analyze | W1.1 seed matching, metadata review | `w11_dopasuj_ziarna.py`, `w11_b0_metadane.py` | `azsecure/w11_*` | ~1 s |
| analyze | W1.2 structure profile, reply graphs | `w12_profil_struktury.py`, `w12_graf.py` | `azsecure/w12_*`, `azsecure/grafy/` | ~10 s |
| analyze | W1.3/W1.4 synthetic injection (4 runs) + summaries | `w13_wstrzykiwanie.py`, `w13_podsumuj.py` | `azsecure/w13_*` | ~6 min in total |
| analyze | E6 Conti injection (RuTor, AntiChat) + summaries | `e6_conti_wstrzykniecie.py`, `e6_podsumuj.py` | `conti/e6_*` | ~10 min / ~33 min |
| analyze | E6 analysis (paired tests, mechanism, seed quality) | `e6_analiza.py` | `conti/e6_analiza.txt` | ~5 s |
| verify | checksums and key numbers | (built in) | — | seconds |

Useful options: `--dry-run` (print commands only), `--steps download,build` (selected groups), `--only e6_rutor`
(one step; names are printed by `--dry-run`). Every step can also be run by hand — the exact command is printed before
it runs and is documented at the top of each script.

## 5. What "verify" checks

- sha256 of every downloaded raw file against `scripts/expected/{azsecure,conti,doj_akty}.csv` (hard check);
- the corpus: 671,585 posts in 12 forums (hard check);
- the Conti graph: all rebuild stages equal to the paper (2,426 → 1,490 → 1,456 conversations, 301 members, 19,039
  conversation units) and the published graph equal to the paper's Table 1 except the diameter (hard check);
- the Conti edge list checksum (hard check);
- checksums of the seed list and of the E6 result tables (soft check — they can legitimately differ: the DOJ API returns
  new releases over time, and floating-point results may change with other library versions).

## 6. Known caveats

- **DOJ API:** results change as new releases are published; the 2026-11-17 sweep had 2,542 releases. The `keyword`
  parameter is ignored by the API — the script filters with `parameters[title]`.
- **Internet Archive:** occasionally slow or rate-limited; the scripts retry. The indictments are fetched from fixed
  archive timestamps; the AZSecure downloader takes the newest archived copy of each file (CDX API) — `verify` compares
  it with the checksums of the copies we used (timestamps listed in `scripts/expected/azsecure.csv`).
- **AZSecure licence** (archived portal page): free for non-commercial research. Some dumps contain only the first page
  of each thread (threads stop at 20 posts) — see the report, section 4.
- **Conti data** comes from the repository of Manatova et al. (2026) at commit `73222516`; it contains chat contents in
  Russian. Only `.json`, `.txt` and the published `.graphml` are downloaded.
- Script comments and variable names are in Polish (working language of the team); this guide and the report are in
  English.
