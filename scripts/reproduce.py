"""DarkTies — reproduction driver for the feasibility tests (November 2026).

Re-creates the local data set and re-runs every analysis described in docs/feasibility_tests_2026-11.md, then
verifies the result against published checksums and key numbers (scripts/expected/).

Usage (from the repository root; the data directory must be OUTSIDE version control — `dane/` is git-ignored):
    python scripts/reproduce.py --data-dir dane                  # everything: download, build, analyze, verify
    python scripts/reproduce.py --data-dir dane --steps verify   # only checks
    python scripts/reproduce.py --data-dir dane --dry-run        # print the commands, run nothing

Steps: download (DOJ API, AZSecure via Wayback Machine, Conti leak from the paper's repository, DOJ indictments via
Wayback) → build (SQLite corpus, dates, seed list, Conti graph) → analyze (W1.1, W1.2, W1.3/W1.4, E6) → verify.

Hand-made inputs are versioned in the repository (inputs/) and copied into <data>/ziarna/ by the step "inputs":
    ziarna_reczne.csv     seeds verified by hand in DOJ press releases and indictments (pseudonyms, group, level, tier,
                          source, public date); Infraud/GozNym seeds are added automatically by ziarna_buduj.py
    conti_role_doj.txt    personas whose roles are named in the DOJ TrickBot/Conti release of 2023-09-07
    kandydaci_b0.txt      NICK@forum candidates selected for the metadata review (W1.1)
    kandydaci_w12.txt     NICK@forum candidates reported in the graph statistics (W1.2)
An existing file in <data>/ziarna/ is never overwritten; a differing one is reported.

Each sub-script is run as `python -I -X utf8 <script> ...` (isolated mode: downloaded data cannot shadow modules).
"""
import argparse, csv, hashlib, json, os, re, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "expected")
INPUTS = os.path.join(HERE, "..", "inputs")


def copy_inputs(D):
    """Step "inputs": copy hand-made inputs from the repository into <data>/ziarna/ (never overwrite)."""
    if not os.path.isdir(INPUTS):
        print(f"   no {os.path.normpath(INPUTS)} directory - nothing to copy")
        return 0
    cel = os.path.join(D, "ziarna")
    os.makedirs(cel, exist_ok=True)
    rozne = 0
    for n in sorted(os.listdir(INPUTS)):
        src, dst = os.path.join(INPUTS, n), os.path.join(cel, n)
        dane = open(src, "rb").read()
        if not os.path.exists(dst):
            open(dst, "wb").write(dane)
            print(f"   copied {n}")
        elif open(dst, "rb").read() == dane:
            print(f"   {n}: already present, identical")
        else:
            rozne += 1
            print(f"   WARN {n}: already present and DIFFERENT from inputs/ - not overwritten")
    return 0 if rozne == 0 else 1


def s(name):
    return os.path.join(HERE, name)


def plan(D):
    j = lambda *p: os.path.join(D, *p)
    db = j("azsecure", "azsecure.sqlite")
    seeds = j("ziarna", "ziarna_v0.csv")
    roles = j("ziarna", "conti_role_doj.txt")
    st = []
    add = lambda grp, name, cmd, needs=(), out=None: st.append((grp, name, cmd, list(needs), out))
    # download
    add("download", "doj_sweep", [s("doj_sweep.py"), j("doj_2026-11-17")])
    add("download", "azsecure", [s("azsecure_pobierz.py"), j("azsecure")])
    add("download", "conti", [s("conti_pobierz.py"), j("conti")])
    add("download", "doj_akty", [s("doj_akty_pobierz.py"), os.path.join(EXP, "doj_akty.csv"), j("doj_akty")])
    # build
    add("build", "sqlite", [s("azsecure_do_sqlite.py"), j("azsecure")])
    add("build", "dates", [s("azsecure_daty.py"), db])
    reczne = j("ziarna", "ziarna_reczne.csv")
    add("build", "inputs", "copy_inputs")  # internal step: inputs/ -> <data>/ziarna/
    add("build", "seeds", [s("ziarna_buduj.py"), j("doj_2026-11-17", "doj_kandydaci.json"), reczne, seeds], [reczne])
    add("build", "conti_graph", [s("conti_struktura.py"), j("conti", "surowe"), seeds, j("conti")], [seeds])
    add("build", "conti_nicks", [s("conti_nicki.py"), j("conti", "surowe"), j("conti", "conti_nicki.csv")])
    # analyze
    w11 = j("azsecure", "w11_dopasowania.csv")
    add("analyze", "w11_match", [s("w11_dopasuj_ziarna.py"), seeds, db, w11], [seeds])
    # ("@lines", path) = NICK@forum list read when the step runs
    add("analyze", "w11_b0", [s("w11_b0_metadane.py"), db, j("azsecure", "w11_b0_metadane.txt"),
                              ("@lines", j("ziarna", "kandydaci_b0.txt"))], [j("ziarna", "kandydaci_b0.txt")])
    add("analyze", "w12_profile", [s("w12_profil_struktury.py"), db, j("azsecure", "w12_profil_struktury.txt")])
    add("analyze", "w12_graphs", [s("w12_graf.py"), db, j("azsecure", "grafy"), j("azsecure", "w12_graf.txt"),
                                  ("@lines", j("ziarna", "kandydaci_w12.txt"))], [j("ziarna", "kandydaci_w12.txt")])
    g = lambda f: j("azsecure", "grafy", f"{f}_eve_b.csv")
    for nazwa, extra in (("w13_damagelab", [g("damagelab"), "1,3,10,30,100"]),
                         ("w13_damagelab_osadzony", [g("damagelab"), "1,2,4", "osadzony"]),
                         ("w13_rutor", [g("rutor")]),
                         ("w13_rutor_osadzony", [g("rutor"), "1,2,4", "osadzony"])):
        wyj = j("azsecure", nazwa + ".csv")
        add("analyze", nazwa, [s("w13_wstrzykiwanie.py"), extra[0], wyj] + extra[1:])
        add("analyze", nazwa + "_summary", [s("w13_podsumuj.py"), wyj], out=j("azsecure", nazwa + "_podsumowanie.txt"))
    for forum in ("rutor", "antichat"):
        wyj = j("conti", f"e6_{forum}.csv")
        add("analyze", f"e6_{forum}", [s("e6_conti_wstrzykniecie.py"), g(forum), j("conti", "conti_krawedzie.csv"),
                                       seeds, roles, wyj], [seeds, roles])
        add("analyze", f"e6_{forum}_summary", [s("e6_podsumuj.py"), wyj], out=j("conti", f"e6_{forum}_podsumowanie.txt"))
    add("analyze", "e6_analysis", [s("e6_analiza.py"), j("conti", "e6_analiza.txt"), j("conti", "e6_rutor.csv"),
                                   j("conti", "e6_antichat.csv"), "--conti", j("conti", "conti_krawedzie.csv")])
    return st


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify(D):
    bad, warn = 0, 0
    def chk(ok, msg, hard=True):
        nonlocal bad, warn
        print(("OK    " if ok else ("FAIL  " if hard else "WARN  ")) + msg)
        if not ok:
            bad += hard
            warn += not hard
    for name, sub in (("azsecure.csv", lambda r: os.path.join(D, "azsecure", "surowe", r["zbior"], r["plik"])),
                      ("conti.csv", lambda r: os.path.join(D, "conti", "surowe", r["plik"])),
                      ("doj_akty.csv", lambda r: os.path.join(D, "doj_akty", r["sprawa"], r["plik"]))):
        rows = list(csv.DictReader(open(os.path.join(EXP, name), encoding="utf-8")))
        ok = sum(1 for r in rows if os.path.exists(sub(r)) and sha(sub(r)) == r["sha256"])
        chk(ok == len(rows), f"raw files {name}: {ok}/{len(rows)} sha256 match")
    exp = json.load(open(os.path.join(EXP, "derived.json"), encoding="utf-8"))
    db = os.path.join(D, "azsecure", "azsecure.sqlite")
    if os.path.exists(db):
        con = sqlite3.connect(db)
        n = con.execute("SELECT COUNT(*) FROM posty").fetchone()[0]
        f = con.execute("SELECT COUNT(DISTINCT forum) FROM posty").fetchone()[0]
        chk(n == exp["posts"] and f == exp["forums"], f"AZSecure corpus: {n} posts in {f} forums "
            f"(expected {exp['posts']} / {exp['forums']})")
    rep = os.path.join(D, "conti", "conti_struktura.txt")
    if os.path.exists(rep):
        t = open(rep, encoding="utf-8").read()
        stages = re.findall(r"praca\s+\d+\s+odbudowa\s+\d+\s+(TAK|NIE)", t)
        table_no = re.findall(r"^(\w+)\s+[\d.]+\s+[\d.]+\s+NIE$", t, re.M)
        chk(stages and all(x == "TAK" for x in stages), f"Conti graph rebuilt from logs: {stages.count('TAK')}/{len(stages)} stages match the paper")
        chk(table_no == ["diameter"], f"Conti graph vs paper Table 1: mismatches {table_no} (only 'diameter' expected: weighted vs unweighted)")
    for key, path, hard in (("seeds_sha256", os.path.join(D, "ziarna", "ziarna_v0.csv"), False),
                            ("conti_edges_sha256", os.path.join(D, "conti", "conti_krawedzie.csv"), True),
                            ("e6_rutor_sha256", os.path.join(D, "conti", "e6_rutor.csv"), False),
                            ("e6_antichat_sha256", os.path.join(D, "conti", "e6_antichat.csv"), False)):
        if exp.get(key) and os.path.exists(path):
            same = sha(path) == exp[key]
            chk(same, f"{os.path.relpath(path, D)} sha256 {'matches' if same else 'differs'}"
                + ("" if hard or same else " (allowed: DOJ API content changes over time; other library versions)"), hard)
    print(f"\nverify: {bad} failure(s), {warn} warning(s)")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="dane")
    ap.add_argument("--steps", default="download,build,analyze,verify")
    ap.add_argument("--only", help="run a single named step (see --dry-run for names)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # step headers appear in order when output goes to a log file
    D, grupy = a.data_dir, a.steps.split(",")
    req = {l.split("==")[0]: l.split("==")[1].strip() for l in open(os.path.join(HERE, "..", "requirements.txt"))
           if "==" in l} if os.path.exists(os.path.join(HERE, "..", "requirements.txt")) else {}
    for mod, ver in req.items():
        try:
            v = __import__(mod).__version__
            print(f"{'OK  ' if v == ver else 'WARN'} {mod} {v} (tested: {ver})")
        except ImportError:
            print(f"MISSING {mod} (pip install -r requirements.txt)")
    print(f"python {sys.version.split()[0]} (tested: 3.12.7)\n")
    def rel(x):  # no absolute paths (user names) in the output; other drive (e.g. encrypted volume) stays absolute
        try:
            return os.path.relpath(x) if os.path.isabs(x) else x
        except ValueError:
            return x
    for grp, name, cmd, needs, out in plan(D):
        if (a.only and name != a.only) or (not a.only and grp not in grupy):
            continue
        if cmd == "copy_inputs":
            print(f"[{grp}/{name}] copy inputs/ -> {rel(os.path.join(D, 'ziarna'))}")
            if not a.dry_run and copy_inputs(D) != 0:
                sys.exit("step inputs failed: a file in the data directory differs from inputs/ (see WARN above)")
            continue
        shown = [f"<NICK@forum list from {os.path.basename(x[1])}>" if isinstance(x, tuple) else rel(x) for x in cmd]
        print(f"[{grp}/{name}] python -I -X utf8 " + " ".join(f'"{x}"' if " " in x else x for x in shown)
              + (f" > {out}" if out else ""))
        brak = [p for p in needs if not os.path.exists(p)]
        if brak:
            print(f"   SKIPPED - missing input: {', '.join(rel(p) for p in brak)} (see the messages above / docs/reproduction.md)")
            continue
        if a.dry_run:
            continue
        lines = lambda p: [x.rstrip("\r\n") for x in open(p, encoding="utf-8") if x.strip()]
        full = [sys.executable, "-I", "-X", "utf8"]
        for x in cmd:
            full += lines(x[1]) if isinstance(x, tuple) else [x]
        if out:
            with open(out, "w", encoding="utf-8") as f:
                r = subprocess.run(full, stdout=f)
        else:
            r = subprocess.run(full)
        if r.returncode != 0:
            sys.exit(f"step {name} failed (exit {r.returncode})")
    if "verify" in grupy and not a.only:
        print("\n== verify")
        sys.exit(0 if a.dry_run or verify(D) else 1)


if __name__ == "__main__":
    main()
