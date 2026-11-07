# DarkTies: Detecting APT-Affiliated Actors in Underground Forums

DarkTies (darkties-apt-affiliation-detector) is a research project proposing the design, implementation, and evaluation of a **passive, agentic system** that ingests archived underground-forum data, builds interaction graphs over forum personas, infers communities and user roles, and produces a **graded APT-affiliation score** for each persona, seeded by known APT-linked usernames. The system analyzes already-collected corpora (e.g., CrimeBB, AZsecure archives) and never interacts with forum users.

- **Team:** Kalina Bialek, Konrad Majewski, Igor Woźniak
- **Supervisor:** Mateusz Bednarczyk
- **Institution:** Warsaw University of Technology, Faculty of Computer Science, Intelligent Systems specialization
- **Date:** November 2026 - February 2027
- **Full specification:** [`docs/design_proposal.pdf`](docs/design_proposal.pdf)
- **Annotated bibliography:** [`docs/literature_review.md`](docs/literature_review.md)

## Motivation

Underground hacking forums are a documented early-warning source for cyber threats: analysis of 88 million forum posts showed that over 60% of threat-relevant keywords appear in forum discussions before professional security reports. Yet APT groups use these forums in a narrowly purposive way - recruiting partners, selling malware-as-a-service and network access, trading compromised data - and industry investigations have identified forum usernames of nearly twenty known APT groups. Meanwhile, peer-reviewed APT research profiles groups from historical incidents and technical artifacts (malware samples), not from forum behavior. The intersection - **behavioral analysis of forum users to detect affiliation with known APT actors** - is largely unoccupied. DarkTies targets exactly that question: which members of the wider underground population are likely cooperating with, or belonging to, known APT groups?

## The affiliation construct

Affiliation is decomposed into three levels, each with a different evidence threshold:

| Level | Claim |
| --- | --- |
| **L1 - Identity match** | Two nicknames refer to the same person |
| **L2 - Cooperation** | Two personas interact in a way consistent with operational collaboration |
| **L3 - Membership** | A persona belongs to a named APT group |

Every label is graded into one of three **confidence tiers** with documented provenance:

- **Gold** - law-enforcement-endorsed links (indictments, prosecution records); internal group records such as the Conti leaks (Feb 2022) for membership.
- **Silver** - vendor-attributed personas (e.g., APT forum usernames from industry investigations).
- **Bronze** - entity-level evidence (mentions of APT tooling/actor names), used only to anchor the entity-recognition layer, not as persona labels.

## Research questions and hypotheses

- **RQ1** - Can a persona's behavioral and structural footprint distinguish APT-affiliated actors from the general underground population?
- **RQ2** - Which signals (community position, inferred role, interaction proximity to seed personas, LLM-extracted textual signals) carry the affiliation signal, and how do they combine?
- **RQ3** - Does a multi-agent LLM pipeline that adaptively selects and weighs signals per persona rank affiliated personas better than fixed, non-agentic scoring from the same signals?
- **RQ4** - Can the system surface affiliated personas before their public attribution (actionable early warning)?

Hypotheses H1–H5 (discrimination, lead time, agentic advantage, component necessity, cross-forum transfer) are each mapped to a dedicated experiment in the proposal (Table 1 therein).

## Evaluation plan (E1–E7)

- **E1** - Data and ground-truth protocol; tiered labels with documented provenance; frozen evaluation protocol; worst-case label-noise analysis.
- **E2a** - Component-wise validation against denser subtask ground truth (role detection, key-actor ranking, related-account identification).
- **E2b** - Affiliation ranking (tests H1): top-k precision at k = 10/50/200, PR curves, nDCG, permutation tests.
- **E3** - Temporal holdout and lead time (tests H2): tune only on pre-cutoff data and labels, measure median lead time between first flag and public attribution.
- **E4a** - Baselines (tests H3): graph proximity, content similarity via domain embeddings, centrality - run early as a design check.
- **E4b** - Ablations (tests H4): remove community detection, then role inference.
- **E5** - Cross-forum transfer (tests H5): calibrate on one forum, evaluate unchanged on a held-out forum.
- **E6** - Robustness: semi-synthetic injection of real APT communication traces (reported separately, never as headline) and label-noise sensitivity.
- **E7** - Analyst adjudication: blinded human review of evidence dossiers for unlabeled flagged personas, agreement reported with Cohen's κ.

## Ethics and scope

- Core experiments use **archived research corpora only**; the system is passive.
- Outputs are **probabilistic risk scores over personas, not assertions over persons**; no named individuals are published; live scraping is an optional, ethics-approved extension, not the core method.
- Explicit risk-of-harm analysis: mislabeling a pseudonymous user as APT-affiliated could expose them to retaliation, so all outputs carry calibrated uncertainty.

## Expected contributions

1. The first peer-reviewed system for APT-affiliation analysis of underground forum users.
2. A documented, reusable evaluation protocol for LLM-driven behavioral analysis of underground forums (partially filling the benchmark gap identified in the reviews).
3. Empirical evidence on the relative contribution of structural, behavioral, and content signals to the affiliation task.

## Repository layout

```
├── README.md                        ← this file
└── docs/
    ├── design_proposal.pdf          ← full design proposal (problem, hypotheses, experiments)
    └── literature_review.md         ← annotated literature table aligned with the proposal
```
