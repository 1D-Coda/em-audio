# Venue evaluation (executed after Phase 0 and first results)

Scored from official journal pages on 2026-08-19; re-check before submission.

| Criterion | FSI: Digital Investigation | J. Information Security and Applications | EURASIP J. Information Security |
|---|---|---|---|
| Scope fit | **Highest.** Official aims and scope: "The primary pillar of this publication is digital evidence and multimedia, with the core qualities of **provenance, integrity and authenticity**", plus an explicit "Scientific practices" track for work that strengthens the scientific foundation and rigour of digital investigations | High — applied information security, includes multimedia security | High — multimedia and information security, open access |
| Methodological fit (formal + systems, no ML) | Strong; the journal explicitly welcomes tool evaluation, scientific practice and reproducible method work without requiring learned models | Strong | Strong |
| Readership | Forensic practitioners, laboratories, incident responders, researchers — precisely the audience for an evidence-claim contract | Security researchers | Security researchers |
| Length limits | No strict word limit stated in the guide for authors | No strict limit | No strict limit |
| LaTeX accepted | Yes (`elsarticle`) | Yes (`elsarticle`) | Yes |
| Open code / data expectations | Research-data statement and data linking requested | Same Elsevier framework | Required |
| AI-use disclosure policy | Required: "Authors must declare the use of generative AI tools in the manuscript preparation process upon submission of the paper." | Same Elsevier policy | Springer policy |
| Desk-reject risk | Moderate; mitigated by the explicit non-detection framing and the forensic-evidence vocabulary | Moderate | Moderate |
| Indicators | CiteScore 6.7, Impact Factor 3.1 | — | — |

**Ranked choice.**

1. **Forensic Science International: Digital Investigation** (Elsevier) — target.
2. *Journal of Information Security and Applications* (Elsevier) — same
   `elsarticle` source compiles unchanged, so reformatting cost is near zero.
3. *EURASIP Journal on Information Security* (Springer, open access).

No claim is made anywhere about review speed.

**Re-check, 2026-08-27.** The third choice has changed and is now a weaker fit.
EURASIP's title is now *Journal on Information Security* (Springer), and its
stated scope centres "security and privacy challenges in which signal processing
and data-centric methodologies play a central role", with an explicit
out-of-scope for submissions that "lack a clear connection between signal or
data-centric methods and security or privacy objectives". This work trains no
model and uses no acoustic feature by design, so it is exposed to a desk reject
on exactly that criterion. It stays on the list because the kernel-footprint
treatment is a signal-level argument, but it moves behind JISA rather than
alongside it. Choices 1 and 2 are unchanged.
