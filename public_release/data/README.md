# Data

All files under `derived/` are written by the scripts in `src/` and the notebooks in `notebooks/scraping/`. Do not edit them by hand.

The steps also write check outputs to `diagnostics/` (summaries of counts, unmatched papers, intermediate values). That folder is not committed; it appears when you run the steps, for example with `reproduce.ipynb`.

## Main tables

| File | One row is | Rows | Key |
|---|---|---:|---|
| `derived/papers/papers.csv` | a paper as listed on a website | 917 | `paper_uid` |
| `derived/papers/authorships.csv` | an author of a paper | 4,448 | `paper_uid` + `author_seq` |
| `derived/papers/paper_references.csv` | a reference of a paper | 27,247 | `paper_uid` + `ref_seq` |
| `derived/researchers/researchers.csv` | a researcher after name disambiguation | 1,682 | `cluster_id` |

`paper_uid` is a hash of the source website, the normalized title and the normalized DOI. It does not depend on row order, so it stays the same when the table is rebuilt.

The four websites appear in the `source_org` column under their Japanese names:

| `source_org` | Organization | Rows in `papers.csv` |
|---|---|---:|
| `豊田中央研究所` | Toyota Central R&D Labs. | 355 |
| `AISIN IMRA(米国・imra.com)` | IMRA America | 312 |
| `トヨタ自動車未来創成センター` | Toyota Motor Corporation, Frontier Research Center (official Japanese name: 未来創生センター) | 153 |
| `AISIN IMRA(日本・aisin.com)` | AISIN IMRA (Japan) | 97 |

The four lists have 919 entries. Two duplicate entries (one on imra.com, one on the Frontier Research Center site) collapse, leaving 917 rows. Of these, 857 are matched to OpenAlex (852 distinct works).

## Read this first

- **When counting works, filter on `is_work_primary == True`.** Five papers are listed on two websites. Without the filter they are counted twice.
- **Use `year_openalex` for the publication year.** `year_site` comes from the website and is mostly empty for imra.com.
- **Do not use `openalex_author_id` to identify people.** OpenAlex sometimes merges different people into one author (one "S. Nakamura" has a 74-year career). Use `orcid`, and `name_key` (family name and first initial) when there is no ORCID. On the 950 records that have an ORCID, `name_key` merges different people in 4.8% of keys and splits one person in 0.8% of ORCIDs (step 9 writes the details to `diagnostics/researchers/namekey_validation.json`).
- **E-mail addresses in affiliation strings are partly hidden.** Some affiliation strings in OpenAlex contain the authors' e-mail addresses. We replaced the part before `@` with `[email]` in the saved API responses and rebuilt the author tables from them. The domain is kept because it identifies the organization in a few cases.
- **Do not use `inst_openalex` to decide affiliations.** OpenAlex often assigns Toyota authors to the Swiss Toyota entity by mistake. For organization-level counts use `affil_scopus` (247 normalized names) or `is_toyota`.
- `authorships.csv` covers only the 857 papers matched to OpenAlex. The other 60 papers have no author rows.

---

## papers.csv (917 rows × 31 columns)

| Column | Non-null | Distinct | Meaning |
|---|---:|---:|---|
| `paper_uid` | 100% | 917 | Key |
| `source_org` | 100% | 4 | Source website (see above) |
| `title_site` | 100% | 916 | Title on the website |
| `authors_site` | 66% | 571 | Authors on the website. Always empty for imra.com |
| `venue_site` | 100% | 721 | Journal, volume and pages on the website |
| `year_site` | 70% | 23 | Year on the website. **Do not use for counts.** Use `year_openalex` |
| `link` | 98% | 892 | Link on the website |
| `doi` / `doi_norm` | 70% | 641 | `doi_norm` is normalized. Join on it |
| `toyota_authors_site` | 17% | 106 | Frontier Research Center only. Authors the site marks as its own staff. Used as ground truth for affiliation checks |
| `work_id` | 93% | 852 | OpenAlex work ID. Empty when no match was found (60 papers) |
| `match_method` | 94% | 2 | `doi_exact` or `title_fuzzy` |
| `match_score` | 94% | 21 | Title similarity. 1.0 for `doi_exact` |
| `review_status` | 94% | 4 | `auto` / `review` / `accepted_by_review` / `rejected_by_review` |
| `review_decision` / `review_reason` | 1% | 2 | Manual decisions (10 papers) |
| `matched` | 100% | 2 | Whether the paper is matched to OpenAlex |
| `is_work_primary` | 100% | 2 | **Filter on this when counting works** |
| `matched_title` | 93% | 852 | Title in OpenAlex, for checking the match |
| `year_openalex` | 93% | 38 | **Publication year** |
| `type` | 93% | 5 | `article` / `conference-paper` / `book-chapter` / `preprint` / `editorial` |
| `cited_by_count` | 93% | 137 | Citations in OpenAlex |
| `referenced_works_count` | 93% | 102 | Number of references. Reference-based measures cannot be computed for the 62 papers with 0 |
| `n_authors` | 93% | 19 | Number of authors |
| `institutions_distinct_count` | 93% | 16 | Number of institutions |
| `primary_topic` | 93% | 280 | OpenAlex topic (4th level) |
| `primary_subfield` | 93% | 80 | OpenAlex subfield (3rd level) |
| `primary_field` | 93% | 21 | OpenAlex field (2nd level) |
| `primary_domain` | 93% | 4 | OpenAlex domain (1st level) |
| `venue_openalex` | 80% | 307 | Journal name in OpenAlex |
| `openalex_doi` | 93% | 848 | DOI in OpenAlex. If it differs from `doi_norm`, suspect the match |

## authorships.csv (4,448 rows × 19 columns, 857 papers)

| Column | Non-null | Distinct | Meaning |
|---|---:|---:|---|
| `paper_uid` | 100% | 857 | Key 1. Refers to `papers.csv` |
| `author_seq` | 100% | 25 | Key 2. Author order, starting at 1 |
| `work_id` | 100% | 852 | Copied from `papers.csv` to save a join |
| `doi` | 72% | 640 | Same |
| `source_org` | 100% | 4 | Same |
| `name_raw` | 100% | 1,997 | Author name as given |
| `given` / `family` | 100% | 1,188 / 1,258 | Given name / family name |
| `name_key` | 100% | 1,639 | Disambiguation key (`family|first initial`) |
| `orcid` | 21% | 501 | ORCID registered with the paper in OpenAlex. **Use this first to identify people** |
| `affiliation` | 99% | 1,536 | Affiliation (best available) |
| `affil_openalex` | 98% | 1,529 | From OpenAlex. **Most complete, but spelled in many ways** (311 variants that contain Toyota Central R&D Labs.) |
| `affil_scopus` | 55% | 247 | From Scopus. **Normalized. Use this for organization-level counts** |
| `inst_openalex` | 94% | 410 | Institution assigned by OpenAlex. **Do not use for affiliations** (includes wrong assignments to the Swiss Toyota entity) |
| `openalex_author_id` | 98% | 1,910 | Kept for reference. **Do not use to identify people** |
| `scopus_author_id` | 56% | 1,128 | Kept for reference |
| `is_corresponding` | 100% | 2 | Corresponding author |
| `is_toyota` | 100% | 2 | Affiliation is a Toyota group organization. Toyota Technological Institute, National Institute of Technology, Toyota College and Kariya Toyota General Hospital are excluded |
| `matched_scopus` | 100% | 2 | Whether the author was matched in Scopus. Always False when the paper has no DOI |

## researchers.csv (1,682 rows × 26 columns)

The 4,448 rows of `authorships.csv` grouped by person (`src/aggregate_researchers.py`). People are grouped by ORCID first and by `name_key` otherwise. Name keys attached to the same ORCID are treated as one person.

**Note:** `first_year` and the columns after it cover only the papers listed on the four websites, not the person's whole career.

| Column | Non-null | Distinct | Meaning |
|---|---:|---:|---|
| `cluster_id` | 100% | 1,682 | Key. `orcid:...` or `name:...` |
| `canonical_name` | 100% | 1,662 | Representative name (the longest variant) |
| `n_name_variants` / `name_variants` | 100% | 8 / 1,667 | Number and list of name variants |
| `orcid` | 30% | 501 | ORCID, for rows with `id_source == "orcid"` |
| `n_papers` | 100% | 30 | Number of papers. Median 1; 197 people have 5 or more, 64 have 10 or more, 18 have 20 or more |
| `first_year` / `last_year` / `career_span` | 100% | — | Years of activity within the collected papers |
| `source_orgs` / `n_source_orgs` | 100% | 12 / 3 | Source websites. 113 people appear on two or more |
| `n_first_author` / `n_corresponding` | 100% | — | Times as first author / corresponding author |
| `n_toyota_records` / `toyota_orgs` | 100% / 46% | 26 / 36 | Number of records with a Toyota affiliation, and the normalized organization names |
| `sectors` | 99% | 18 | Sectors of the affiliations (university / company / government / hospital / other) |
| `affiliations` | 99% | 861 | Affiliation strings (cut at 500 characters) |
| `primary_fields` | 100% | 134 | OpenAlex fields (2nd level) of the papers |
| `scopus_author_ids` / `openalex_author_ids` | 64% / 99% | — | Kept for reference. **Do not use to identify people** |
| `total_citations` | 100% | 296 | Sum of citations, counting each paper once |
| `id_source` | 100% | 2 | `orcid` (501 people) or `name_key` (1,181 people) |
| `n_orcids` | 100% | 2 | Number of ORCIDs in the group (0 or 1) |
| `has_affiliation_data` | 100% | 2 | Whether any record of the person has an affiliation (False for 13 people) |
| `initials_only` | 100% | 2 | Whether the given name appears only as initials in every record (180 people) |
| `confidence` | 100% | 3 | `high` 501 / `medium` 1,008 / `low` 173. `low` means a `name_key` group whose given name is only initials |

## paper_references.csv (27,247 rows, 790 papers)

What each paper cites. The citation links come from the OpenAlex snapshot; the titles of the cited works come from the OpenAlex API (`src/build_reference_titles.py`).

| Column | Meaning |
|---|---|
| `paper_uid` | Refers to `papers.csv` |
| `paper_title` / `paper_title_site` | Title of the citing paper (OpenAlex / website) |
| `ref_seq` | Order of the reference |
| `ref_work_id` / `ref_doi` / `ref_year` | OpenAlex work ID / DOI / year of the cited work |
| `ref_title` | Title of the cited work |

The median number of references per paper is 31. `ref_title` is filled for 94.7% of rows. Most missing titles (1,407) belong to OpenAlex works that were merged or deleted, so rerunning does not fill them.

---

## Other files

| Folder | Files | Written by |
|---|---|---|
| `derived/toyota_official_scrape/` | The four publication lists, their run metadata (`*_meta.json`), and `combined_papers.csv` | step 1, step 2 |
| `derived/openalex_linking/` | Matches to OpenAlex (`openalex_links.csv`), metadata of matched works, matches after manual review | steps 3–4 |
| `review/openalex_review_decisions.csv` | Manual decisions on uncertain matches. The only hand-made input | by hand |
| `derived/paper_enrichment/` | Authors and affiliations from Scopus. The file keeps only the columns used to build `authorships.csv` | step 6 |
| `derived/papers/authorship_affiliations.csv` | Normalized organization names and sectors for each author row | step 8 |
| `derived/papers/paper_covariates.csv` | Number of authors in OpenAlex (the analysis uses the SciSciNet team size instead), international collaboration, interdisciplinarity of references, industry–academia collaboration | step 12 |
| `derived/novelty/` | Our own novelty values (`paper_novelty.csv`), summary of the comparison with SciSciNet (`sciscinet_check.json`) | steps 13, 15 |
| `derived/papers/sciscinet_metrics.csv` | SciSciNet values for our papers (`ss_*`) | step 14 |
| `derived/analysis/paper_analysis.csv` | One row per paper: paper data, SciSciNet values (`ss_*`), our own values (`own_*`), covariates | step 16 |
| `derived/analysis/baseline_sample.csv` | Random sample of 3,000 papers per field and year (157 cells) with SciSciNet values | step 17 |
| `derived/analysis/paper_percentiles.csv` | Percentiles of our papers within their field and year | step 17 |
| `derived/analysis/novelty_analysis.json` | Results of the analysis | step 18 |
| `cache/` | Saved OpenAlex API responses | step 3 |

**Do not mix `ss_*` and `own_*` values.** They are on different scales (median conventionality 217 in SciSciNet, 113 in ours).

## Known limitations

- The websites do not list all papers of these organizations. Among papers with an OpenAlex publication year, the share from 2018 onward is 99.4% for Toyota Central R&D Labs., 98.5% for the Frontier Research Center, 51.2% for AISIN IMRA (Japan) and 17.9% for imra.com. The analysis uses papers from 2000 onward.
- Normalization of affiliation strings is not complete. `affil_openalex` spells the same organization in many ways; use `affil_scopus` or `is_toyota` for organization-level counts.
- The SciSciNet team size (`ss_team_size`) is 0 for 136 of the 679 papers from 2000 onward that have SciSciNet values, although OpenAlex lists authors for them. The analysis uses the SciSciNet values as they are (see the README).
- One match still has `review_status == "review"`.
- One AISIN IMRA (Japan) entry has part of the journal name in `authors_site`, because the website splits the journal name across two HTML elements.
- The `source_org` value `トヨタ自動車未来創成センター` uses a different character from the official name (未来創生センター). It refers to the same organization.
