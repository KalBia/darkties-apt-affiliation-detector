# DarkTies — feasibility tests, November 2026: what we did and why

*Status: exploratory feasibility work before implementation (not results for H1–H5). Reproduction:
[`docs/reproduction.md`](reproduction.md). Scripts: [`scripts/`](../scripts/).*

## Summary

Before building the agentic pipeline we checked the three things most likely to kill the project: **data access**,
**labels** (known APT-linked personas present in the corpora) and **statistical power** (can a seed-based ranking find a
group at all, with the handful of seeds we will realistically have). In short:

1. **Data is no longer the blocker.** The AZSecure hacker-forum archives (portal offline since 2025) were recovered
   from the Internet Archive: 12 forums, 671,585 posts, including Russian-language forums. The CrimeBB request has been filed
   by the supervisor. The Conti leak was obtained from the code repository of a peer-reviewed paper.
2. **Labels are the blocker.** Official attribution (DOJ press releases and indictments) gives pseudonyms, but the
   forums named there are not in either corpus, and state-linked personas in DOJ cases come without any forum at all.
   In AZSecure only 3–5 seed personas are plausible after a metadata review, all from financially motivated groups.
3. **The ranking mechanics work** — on forum interaction graphs built with the method of Pastrana et al. (RAID 2018)
   and on the *real* communication structure of the Conti group injected into those graphs (Design Proposal E6). With
   four personas whose roles were named by DOJ as seeds, 67–97% of the top-50 ranked personas are true group members
   (chance: 1–4%).
4. **What decides feasibility is not the number of seeds but (i) how much of a group is present and connected on the
   same forum and (ii) whether the seeds are central.** If only 30 of Conti's 301 members were on one forum, more than
   half of them would have no visible tie to any other member and the ranking would barely work.
5. **Personalized PageRank (PPR) should be added to the E4a baselines.** In 96 paired comparisons on the Conti
   injection, PPR (α = 0.5) was significantly better than the shortest-path baseline from the proposal in 73 and never
   worse; without it, E4a would test the agentic system against weak opponents.

## 1. Why these tests

The Design Proposal names a small positive class as the main statistical risk (§4.9) and requires E4a (simple
proximity baselines) to run early as a design check (§4.4.1): "if a trivial proximity heuristic matches the full
pipeline, the design must be revised". It also plans E6, a semi-synthetic test injecting real APT communication traces
(§4.6), reported separately from the main results. The tests below are the cheapest versions of these checks that do
not need labels we do not yet have. Every method choice was taken from the literature where possible; choices without
a source are marked as assumptions.

## 2. Data acquisition — what, from where, and how it is handled

| Data | Source and route | Size | Why this route |
|---|---|---|---|
| DOJ press releases | official DOJ API (`/api/v1/press_releases.json`, filtered by 15 title keywords; the `keyword` parameter is ignored by the API, `parameters[title]` works) | 2,542 releases → 109 automatic candidates (forum + pseudonym) | primary source of law-enforcement attribution (gold tier); the website itself blocks automated clients, the API does not |
| Indictments (11 PDFs: APT27/i-Soon, Yahoo/FSB, DanaBot, TrickBot/Conti, an access-broker case 2:18-cr-00303 W.D. Wash.) | Internet Archive copies of the PDFs linked from the DOJ releases | 11 files | same documents, legal public route |
| AZSecure hacker forums | Internet Archive (CDX API) copies of the dataset files from the former AZSecure portal; licence on the archived page: free for non-commercial research | 10 archives: AntiChat, Webkill, Xakepok, DamageLab (RU); ExeTools, CrackingArena, HackHound, CrackingFire, Garage4Hackers (EN); Dark Net Forums 2019 (RuTor, Silk Road, Wall Street) — 12 forums, 671,585 posts, 79,038 forum–author pairs | portal offline since 2025; post counts match every dataset's ReadMe (parser completeness check) |
| Conti leak (2022) | official repository of Manatova, McGrath & Camp, *J. Cybersecurity* 2026 (`dalyapraz/conti-org-analysis`, pinned commit `73222516`): Jabber + "chat" logs, alias map, the paper's final graph | 168,624 messages, 2020-06 … 2022-02 | provenance from a peer-reviewed study and a published graph we can verify against; the popular translation repositories also contain malware code and unrelated document dumps, so they were not used |

Handling rules we applied: data is kept **outside the repository**, in an encrypted container; raw files
are read-only; nothing from the data is executed (scripts run Python in isolated mode, pickle files are never
downloaded); raw post or chat content is not sent to external model APIs; this public repository contains code,
checksums and aggregate numbers only — no forum data and no real pseudonyms. We did not bypass anti-bot protections
or paywalls; where a page blocked automated access we used an official API, an open-access copy or the Internet Archive.

## 3. Labels (feasibility test W0.2 / W1.1)

**Seed list.** 155 pseudonyms from official attribution (DOJ releases and indictments), each with group, group type
(state-linked / financial), affiliation level (L1–L3), tier and public-attribution date. The two largest blocks are
the Infraud carding organisation (84) and Conti/TrickBot (13 pseudonyms from the DOJ release of 2023-09-07 on the
TrickBot/Conti indictments).

**Observations.**
- **State-linked personas are rare in DOJ material and never come with a forum**: 3 cases in 2,542 releases; the
  indictments we read (APT27/i-Soon, Yahoo/FSB) identify people through infrastructure, accounts and communications,
  not forum activity. Forums are named mostly for financially motivated groups (carding, access brokers, ransomware).
- **The labelled forums (e.g. Exploit, XSS, Darkode, Infraud) are in neither corpus** — neither in AZSecure nor in the
  2018 CrimeBB forum list.
- **AZSecure string matching (W1.1):** 37 of 155 seeds match an author name; most are common words or first names.
  A metadata-only review (post counts, ranks, join dates, sub-forums, thread titles — no post content) leaves 3
  plausible and 2 possible candidates; 2 matches were excluded because the person was demonstrably in custody when
  the posts were written. Such a *temporal-impossibility filter* (arrest, death, account creation) is cheap and strong
  and should become part of the L1 module.
- **Conti:** 10 of the 13 DOJ pseudonyms are nodes of the leak's communication graph (the four with roles named in the
  release are among its five most central members); 3 do not appear in the 2020–2022 logs. Matching all 621 Conti
  names (with aliases) against AZSecure gives 184 string matches — almost all common English names and words, none
  verified. A leak gives membership labels (L3), but not the forum personas of the members.

**Consequence.** The decisive open question is the definition of "APT" (team decision): if financially motivated
groups count, gold labels exist; if only state-sponsored groups count, the forum-based positive class is close to empty.

## 4. Interaction graphs (W1.2)

**Method** — Pastrana et al., *Characterizing Eve*, RAID 2018, §4.2: directed edge V → W when V replies in a thread
started by W (variant b; variant a, quotes, needs the HTML and is not done yet). Thread order comes from the post
sequence number, so edges do not depend on the date formats.

**Data quality.** Dates in many formats (English and Russian, relative dates) were normalised for 97.9–100% of posts
per forum. Three dumps were collected only up to the first page of each thread (CrackingFire, HackHound fully,
AntiChat partly — threads stop at 20 posts). ExeTools has no thread identifiers and Webkill's thread identifiers are
broken; Silk Road has ambiguous thread starters.

| Forum | Nodes with an edge | Edges | Largest weakly connected component |
|---|---|---|---|
| AntiChat (truncated) | 27,869 | 102,964 | 99.4% |
| CrackingArena | 11,634 | 26,507 | 99.9% |
| CrackingFire (truncated) | 14,118 | 22,723 | 99.4% |
| DamageLab | 1,151 | 3,038 | 99.8% |
| Garage4Hackers | 804 | 2,370 | 98.9% |
| HackHound (truncated) | 753 | 1,721 | 99.2% |
| RuTor | 8,176 | 32,546 | 99.6% |
| Wall Street | 5,103 | 15,233 | 98.3% |
| Xakepok | 3,956 | 12,900 | 98.7% |

The graph gate is met on 8 forums (Silk Road uncertain; ExeTools and Webkill unusable). All candidate seeds lie in the
giant component.

## 5. Semi-synthetic test with a synthetic group (W1.3 / W1.4)

**Design.** Injection as in SybilRank (Cao et al., NSDI 2012, §6.1: regular group graph with d = 4, varying attack
edges, repeated runs, AUC) combined with seed set expansion in a planted-partition model (Kloumann, Ugander & Kleinberg,
PNAS 2017). Methods: PPR (α = 0.5 / 0.85 / 0.95), PPR divided by degree (SybilRank §4.3), and the E4a baselines of the
proposal (shortest path to seeds, common neighbours, degree), plus a random ranking as an internal control. Metrics:
precision among the top-k (proposal §4.2.2) and AUC; significance by the exact hypergeometric test, which is
equivalent to the label-permutation test of the proposal; power = share of runs with p < 0.05.

**A lesson first.** Adding the group as *new* nodes connected to the forum by random edges made group members hubs;
degree alone then matched PPR (precision 0.70 for both). That variant measured our own construction, so we moved to
the *embedded* variant: the group consists of existing forum personas, only d internal edges per member are added.
Always keeping "degree" and "random" baselines is what exposed the artefact.

**Embedded results** (RuTor 8,144 nodes, DamageLab 1,149 nodes; 50 runs per configuration): with d = 2 internal ties
per member, already 1 seed gives top-10 precision ≈ 0.3 and power 0.9–1.0; with d = 4 precision reaches 0.6–0.8;
with d = 1 precision stays at 0.1–0.45. PPR/degree and PPR α = 0.5 are clearly better than the proposal's baselines
(RuTor, 30 members, d = 4, 10 seeds: 0.766 vs 0.274 for shortest path); degree is no better than random. Power grows
with graph size even at equal precision, so **precision must always be reported next to significance**.

## 6. Real group structure: Conti (E6)

**The graph.** Manatova et al. (2026) build an undirected graph: node = member pseudonym (aliases merged), edge = two
members who talked to each other (one-sided conversations removed), weight = number of *conversation units* (a unit ends
after a pause longer than the 90th percentile of gaps in that conversation, clipped to 30 min … 12 h). We verified the
paper's published graph against its Table 1 (13 of 14 statistics identical; the diameter 44 in the paper is the
weighted diameter, the unweighted one is 6) and **rebuilt it independently from the raw logs with identical numbers at
every stage**: 2,426 pair histories → 1,490 two-way → 1,456 after removing an echo glitch → 301 members → 19,039
conversation units; all 1,456 edge weights match.

**Cohesion.** Median degree 5 (quartiles 2 / 10); 75% of members have ≥ 2 ties, 56% ≥ 4. The distribution is very
uneven (maximum 145; the paper reports a power law).

**Injection design.** Conti members are mapped onto random existing personas of RuTor and AntiChat (both
Russian-language) and the Conti edges are added between them. How many of the private-chat relations would be visible
as forum interactions is unknown, so it is swept: each edge kept with probability q ∈ {1, 0.5, 0.2, 0.1}, or only edges
with weight ≥ 5 / ≥ 20. Scenarios: the whole group on the forum, or only 30 random members. Seeds: 1 / 5 / 10 random
members, the 4 personas with roles named by DOJ, or all 10 DOJ personas. 100 runs per configuration (as in SybilRank).

**Top-50 precision on RuTor** (chance ≈ 0.04). Power (share of runs with p < 0.05 for top-50 precision, PPR α = 0.5):
1.00 for the 4 DOJ seeds in every column; 0.74–1.00 for 5 random seeds; 0.28–0.96 for 1 random seed.

| Seeds | Method | q = 1 | q = 0.5 | q = 0.2 | q = 0.1 | weight ≥ 5 | weight ≥ 20 |
|---|---|---|---|---|---|---|---|
| 1 random | PPR α = 0.5 | 0.63 | 0.37 | 0.23 | 0.09 | 0.38 | 0.15 |
| 5 random | PPR α = 0.5 | 0.63 | 0.47 | 0.27 | 0.19 | 0.44 | 0.20 |
| 5 random | shortest path | 0.53 | 0.37 | 0.19 | 0.14 | 0.35 | 0.16 |
| 4 DOJ (roles) | PPR α = 0.5 | 0.97 | 0.95 | 0.84 | 0.67 | 0.96 | 0.81 |
| 4 DOJ (roles) | PPR / degree | 0.96 | 0.94 | 0.90 | 0.78 | 0.95 | 0.90 |
| 10 DOJ | PPR / degree | 0.82 | 0.79 | 0.76 | 0.64 | 0.78 | 0.71 |
| any | degree | 0.04–0.08 | 0.04 | 0.04 | 0.04 | 0.06 | 0.04 |

AntiChat (27,869 nodes) shows the same picture, slightly higher (e.g. 4 DOJ seeds: 1.00 / 0.99 / 0.88 / 0.71).
**Only 30 members on the forum:** on average just 15 visible internal edges at q = 1 (about one tie per member);
top-10 precision with 5 seeds falls from 0.28 (q = 1) to 0.06 (q = 0.1).

**Analysis.**
- *Paired comparison* (same runs for both methods; sign-flip permutation test on the difference in top-50 precision,
  i.e. Fisher's randomization test as in the proposal and in ranx; Holm correction over the whole family of 192
  comparisons fixed before the analysis): PPR α = 0.5 significantly better than shortest path in 73/96 configurations,
  worse in 0/96; PPR/degree better in 65/96, worse in 1/96. Where neither wins, nothing works (30 members, low
  visibility). PPR/degree is better under low visibility and with DOJ seeds, α = 0.5 under full visibility.
- *Why real structure is harder than a synthetic group:* at the same average degree (~2) the real structure gives about
  half the precision of the regular synthetic group (0.38 vs 0.64). Measured cause: with uneven degrees, removing edges
  cuts peripheral members off completely — 40% of members have no visible tie at q = 0.2, 56% of a random 30-member
  subset at full visibility, versus 0% in a regular graph. Graph methods cannot reach isolated members. **The average
  number of ties overstates detectability; the share of members connected to the rest of the group is what matters.**
- *Seed quality:* the Conti degree of a single seed correlates with top-50 precision (Spearman ρ = +0.45 … +0.80 across
  all visibility levels and methods). A seed with ≥ 20 ties gives 0.90 vs 0.45 for a seed with ≤ 3 ties (full
  visibility), 0.48 vs 0.09 at q = 0.2. This is why 4 central DOJ seeds beat all 10 DOJ seeds (the extra six are
  peripheral and dilute the random walk). Averages over random seeds hide this spread.
- *Artefact check:* degree has AUC up to 0.79 (injected edges raise members' degree) while being at chance level in the
  top-k — the degree baseline must stay in every synthetic report.
- *Reproducibility:* a second full run with a fixed random seed reproduced all 38,400 result rows exactly.

## 7. What changed in our thinking

- From "can we get data?" to "do we have labels with forums?" (after recovering AZSecure).
- From "is a real APT group cohesive?" to "how much of it is visible on one forum, and are our seeds central?" (after
  E6). An earlier rule of thumb from the synthetic test ("≥ 2 internal ties per member is enough") was withdrawn: it
  holds for regular synthetic groups, not as an average for real ones.

## 8. Decisions needed from the team

1. **What counts as APT** (drives the size of the positive class). Proposal: NIST SP 800-39 definition (not limited to
   states) as used by Chen et al. (CMS 2014); membership from official attribution (gold); MITRE ATT&CK / MISP only as
   a vocabulary and silver source (ATT&CK groups are clusters aggregated from vendor reports); financially motivated
   groups reported separately.
2. **Add PPR (α = 0.5) to the E4a baselines**, with PPR/degree as a sensitivity variant.
3. **Role of AZSecure:** main corpus (few seeds) or test bed for the mechanics until CrimeBB arrives (our
   recommendation: test bed).
4. **Evaluation protocol (to freeze before E1):** top-10/50/200 precision and AUC; paired permutation tests with Holm
   correction inside a pre-registered family; results **stratified by seed centrality**; report the share of group
   members without a visible tie.

## 9. Next steps

1. Read the TrickBot/Conti and DanaBot indictments for forum names and forum pseudonyms of group members — the only
   thing that could link the leak to a forum.
2. Robustness of E6 to two assumptions without a literature source: mapping members to personas of similar activity
   instead of random personas; role-dependent visibility (leaders' ties visible more often).
3. When CrimeBB arrives: ask for current forum coverage (Russian-language forums), API-model usage terms, and forums
   with many members of one group; run the same pipeline (the Conti name list is ready for matching).
4. Graph variant (a) — quote relations from HTML.

## 10. Assumptions without a literature source

Group sizes 10 / 30 and degrees d in W1.3; mapping members to random personas; visibility levels q and weight
thresholds in E6; the 30-member scenario; anchoring relative dates at each forum's latest date (< 1% of posts);
50 instead of 100 runs in W1.3; Spearman correlation as the seed-quality measure.

## References

- Cao, Sirivianos, Yang, Pregueiro — *SybilRank*, USENIX NSDI 2012, pp. 197–210.
- Chen, Desmet, Huygens — *A Study on Advanced Persistent Threats*, CMS 2014, LNCS, doi:10.1007/978-3-662-44885-4_5.
- Holm — *A simple sequentially rejective multiple test procedure*, Scandinavian Journal of Statistics 6(2):65–70, 1979.
- Kloumann, Ugander, Kleinberg — *Block models and personalized PageRank*, PNAS 114(1):33–38, 2017,
  doi:10.1073/pnas.1611275114 (arXiv:1607.03483).
- Manatova, McGrath, Camp — *The organizational anatomy of cybercrime: a multilayer framework for modeling
  resilience*, Journal of Cybersecurity 12(1), 2026, tyag014 (CC BY 4.0); code: github.com/dalyapraz/conti-org-analysis.
- Pastrana, Hutchings, Caines, Buttery — *Characterizing Eve*, RAID 2018, LNCS pp. 207–227,
  doi:10.1007/978-3-030-00470-5_10.
- Pastrana, Thomas, Hutchings, Clayton — *CrimeBB*, WWW 2018, doi:10.1145/3178876.3186178.
- Ruellan, Paquet-Clouston, Garcia — *Conti Inc.: Understanding the Internal Discussions of a large
  Ransomware-as-a-Service Operator with Machine Learning*, Crime Science 13:16, 2024, doi:10.1186/s40163-024-00212-y.
- Bassani — *ranx*, ECIR 2022, LNCS 13186:259–264, doi:10.1007/978-3-030-99739-7_30.
- NIST SP 800-39 (definition of "advanced persistent threat", NIST CSRC glossary).
