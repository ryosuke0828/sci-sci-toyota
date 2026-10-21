# Novelty of papers from Toyota-related research organizations

This repository contains the code and data used to measure the novelty and disruption of papers published by four Toyota-related research organizations, and to compare them with other papers in the same field and year.

**This repository is private and is shared only within the lab.** It contains author affiliations and author IDs obtained from Scopus under Osaka University's subscription. The Scopus terms do not allow showing Scopus data on a website or in any other public place, and allow access only to members of the subscribing institution. Do not make this repository public, and do not copy its data to places outside the lab.

The work has three parts.

1. **Paper and researcher tables.** We collected the publication lists of four organizations from their websites, linked each paper to [OpenAlex](https://openalex.org/), and filled in authors and affiliations from OpenAlex and Scopus. We then grouped the authors into researchers (`data/derived/researchers/researchers.csv`). The researcher table is not used in the novelty analysis; it is kept as a database of the researchers.
2. **Checking SciSciNet.** We recomputed the novelty measure of Uzzi et al. (2013) ourselves and compared it with the values published in [SciSciNet](https://northwestern-cssi.github.io/sciscinet/).
3. **Analysis.** Using the SciSciNet values, we ranked each paper against a random sample of papers from the same field and year, and tested two hypotheses about team size and international collaboration.

## Data sources

| Source | What we took | When |
|---|---|---|
| Toyota Motor Corporation, Frontier Research Center | Publication list (JSON used by the site): `https://www.toyota.co.jp/jpn/tech/partner_robot/search/json/articles.json` | 2026-07-27 |
| Toyota Central R&D Labs. | Publication list: `https://www.tytlabs.co.jp/ja/technology/papers.html` | 2026-07-27 |
| AISIN IMRA (Japan) | Publication list: `https://www.aisin.com/jp/group/imra-japan/paper/` (pages 1–6) | 2026-07-27 |
| IMRA America | Publication list: `https://www.imra.com/imra-research-papers/` | 2026-07-27 |
| OpenAlex API | Matching papers to OpenAlex works; authors, affiliations, fields | August–September 2026 |
| OpenAlex snapshot | References of all papers, used for the novelty computation, the covariates and the baseline sample. Parquet snapshot whose newest partition is `updated_date=2026-06-26` | Downloaded 2026-08-24 |
| Scopus Abstract Retrieval API | Authors' affiliations of papers with a DOI (institutional subscription) | 2026-08-06 |
| SciSciNet v2 | Novelty, conventionality, disruption, citations and team size: `gs://sciscinet-neo/v2/sciscinet_papers.parquet` | 2026-09-14 |

The scraped web pages themselves are not included, only the publication lists extracted from them. Some affiliation strings contain the authors' e-mail addresses; we hide the part before `@` (see `data/README.md`).

SciSciNet: the first version of SciSciNet is released under CC0. The distribution page of version 2 does not state a license and asks users to cite Lin et al. (2023). `data/derived/analysis/baseline_sample.csv` and `data/derived/papers/sciscinet_metrics.csv` contain SciSciNet values.

## Pipeline

Run every script from the repository root. Outputs go to `data/derived/`.

| Step | Code | Main output | Reproduced by default |
|---|---|---|---|
| 1. Scrape the four websites | `notebooks/scraping/*.ipynb` | `toyota_official_scrape/{site}.csv` | No (the sites change) |
| 2. Combine the four lists | `src/rebuild_combined_papers.py` | `toyota_official_scrape/combined_papers.csv` | Yes |
| 3. Match papers to OpenAlex | `src/openalex_link_toyota_papers.py` | `openalex_linking/openalex_links.csv` | Yes (saved API responses) |
| 4. Apply manual review decisions | `src/apply_review_decisions.py` | `openalex_linking/openalex_links_reviewed.csv` | Yes |
| 5. Build the paper table | `src/build_paper_table.py` | `papers/papers.csv` | Yes |
| 6. Fetch affiliations from Scopus | `src/enrich_papers_scopus.py` | `paper_enrichment/scopus_paper_authors.csv` | No (needs a Scopus API key) |
| 7. Build the author table | `src/build_authorship_table.py` | `papers/authorships.csv` | Yes |
| 8. Normalize affiliations | `src/normalize_affiliations.py` | `papers/authorship_affiliations.csv` | Yes |
| 9. Disambiguate researchers | `src/aggregate_researchers.py` | `researchers/researchers.csv` | Yes |
| 10. Extract columns from the OpenAlex snapshot | `src/openalex_snapshot_extract.py` | about 23 GB outside the repository | No |
| 11. List references | `src/build_reference_titles.py` | `papers/paper_references.csv` | No (needs step 10) |
| 12. Paper covariates | `src/build_paper_covariates.py` | `papers/paper_covariates.csv` | No (needs step 10) |
| 13. Our own novelty values | `src/novelty_uzzi.py` (test: `src/novelty_uzzi_selftest.py`) | `novelty/paper_novelty.csv` | No (needs step 10); the test runs |
| 14. Fetch SciSciNet values | `src/fetch_sciscinet_metrics.py` | `papers/sciscinet_metrics.csv` | Yes (reads SciSciNet over the internet) |
| 15. Compare our values with SciSciNet | `src/verify_novelty_sciscinet.py` | `novelty/sciscinet_check.json` | Yes (reads SciSciNet over the internet) |
| 16. Analysis table | `src/build_analysis_table.py` | `analysis/paper_analysis.csv` | Yes |
| 17. Baseline sample and percentiles | `src/build_matched_baseline.py` | `analysis/baseline_sample.csv`, `analysis/paper_percentiles.csv` | Percentiles yes; drawing a new sample needs step 10 |
| 18. Analysis | `src/analyze_novelty.py` | `analysis/novelty_analysis.json` | Yes |

The columns of each table are described in [`data/README.md`](data/README.md).

## How to reproduce

Requirements: Python 3.14, an internet connection, and about 1 GB of free disk space.

```sh
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # optional: set SCISCI_CONTACT_EMAIL
jupyter execute reproduce.ipynb
```

`reproduce.ipynb` copies the committed outputs aside, reruns the steps marked "Yes" above in order, and compares every output with the committed file. It stops with an error if any file differs. You can also open it in Jupyter and run the cells one by one. A run takes about 10 minutes, most of it spent reading SciSciNet in steps 14 and 15; it can take longer on a slow connection.

To rerun the other steps, set the switches at the top of `reproduce.ipynb`:

- `RUN_SCRAPING`: scrape the four websites again (step 1).
- `RUN_SCOPUS`: fetch affiliations from Scopus again (step 6). Needs `SCOPUS_API_KEY` and access from a network of an institution that subscribes to Scopus.
- `RUN_SNAPSHOT`: download and use the OpenAlex snapshot (steps 10–13, and a new baseline sample in step 17). Needs about 50 GB of download and about 35 GB of disk space. Set `SCISCI_SLIM_GLOB` and the other `SCISCI_*` variables described in each script if you keep the data somewhere other than `~/scisci-data/`.

These steps will not give exactly the committed outputs, for the reasons below.

## What cannot be reproduced exactly

- **Scraping.** The websites change. The extracted lists and the dates are included.
- **OpenAlex snapshot.** OpenAlex replaces the snapshot regularly and does not keep old versions. The outputs of steps 11–13 and the snapshot version are included.
- **Scopus.** Access requires a subscription. The affiliation strings and Scopus author IDs used in the author table are included, but not the raw API responses.
- **SciSciNet.** If the file is moved or updated, steps 14 and 15 will fail or give different values. The values we used (`papers/sciscinet_metrics.csv`) and the baseline sample (`analysis/baseline_sample.csv`) are included.

Step 3 calls the OpenAlex API only for requests that are not in the saved responses (`data/cache/`), so it reproduces the committed output.

## Findings

Exact values are in `data/derived/novelty/sciscinet_check.json` and `data/derived/analysis/novelty_analysis.json`.

- **Our novelty values agree with SciSciNet in ranking but not in scale.** For the 490 papers that have both values, the rank correlation is 0.82 for conventionality (median z) and 0.90 for novelty (10th percentile z). The medians differ (conventionality: 113 in ours, 217 in SciSciNet), probably because SciSciNet's assignment of papers to journals is not published. We therefore use only SciSciNet values in the analysis and do not mix the two.
- **Organizations differ in how unconventional their papers are.** Measured as a percentile against papers of the same field and year (higher means more unconventional), the median over 624 papers from 2000 onward is 65.6 for Toyota Central R&D Labs., 63.1 for the Frontier Research Center, 42.8 for IMRA America and 41.3 for AISIN IMRA (Japan). The difference between organizations remains after controlling for the number of references and interdisciplinarity (p = 0.027). For disruption, compared with papers of the same field and year that also have a similar number of references and a similar team size, the median percentile is between 48 and 53 for all four.
- **Neither hypothesis is supported.** Larger teams do not have more unconventional papers (p = 0.39), and international collaboration is not associated with more unconventional papers (p = 0.81). Both models control for the number of references and interdisciplinarity, and the second also for team size (533 papers from 2000 onward).
- **Team size is the SciSciNet value, used as it is.** SciSciNet gives a team size of 0 for 136 of the 679 papers from 2000 onward that have SciSciNet values, although OpenAlex lists authors for them (median 4). The same happens for 19% of the comparison papers. We did not correct these values. In the models, 0 is counted as 1 when taking the logarithm (46 of the 533 papers). In the disruption comparison, a paper with team size 0 is compared with papers of team size 0 or 1.

## Repository layout

```
README.md            this file
CONTRIBUTING.md      general rules for lab repositories (in Japanese): structure, what to commit, naming
AGENTS.md            rules specific to this repository, for people and AI agents
reproduce.ipynb      reruns the pipeline and checks the outputs
requirements.txt     Python packages and versions
.env.example         environment variables
notebooks/scraping/  step 1
src/                 steps 2–18
data/cache/          saved OpenAlex API responses (step 3)
data/review/         manual decisions on uncertain OpenAlex matches (step 4)
data/derived/        outputs of every step
data/diagnostics/    check outputs written by the steps: summaries, unmatched papers, intermediate values (not committed)
```

## References

- Uzzi, B., Mukherjee, S., Stringer, M., & Jones, B. (2013). Atypical combinations and scientific impact. *Science*, 342(6157), 468–472.
- Funk, R. J., & Owen-Smith, J. (2017). A dynamic network measure of technological change. *Management Science*, 63(3), 791–817.
- Wu, L., Wang, D., & Evans, J. A. (2019). Large teams develop and small teams disrupt science and technology. *Nature*, 566, 378–382.
- Lin, Z., Yin, Y., Liu, L., & Wang, D. (2023). SciSciNet: A large-scale open data lake for the science of science research. *Scientific Data*, 10, 315.
- Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts. arXiv:2205.01833.

## License

No license is granted. The repository is for use within the lab only (see the note at the top).
