# Working rules

The general rules for lab repositories are in [`CONTRIBUTING.md`](CONTRIBUTING.md) (in Japanese): structure, what to commit, naming and commit messages. They apply to people and AI coding agents alike. Read it before making changes. This file adds the rules specific to this repository.

## Rules specific to this repository

- **Do not make this repository public or copy its data outside the lab.** It contains Scopus data, and the Scopus terms do not allow showing it in public or giving access to people outside the subscribing institution (Osaka University).
- The main line of this repository has five parts. Commit only what belongs to them:
  1. publication lists scraped from the four organizations' websites;
  2. matching to OpenAlex and filling in authors and affiliations (OpenAlex, Scopus);
  3. the researcher table built from the authors and affiliations (steps 7-9);
  4. checking SciSciNet's novelty values against our own computation;
  5. the analysis based on SciSciNet values.
- Do not commit raw copies of the scraped web pages, raw Scopus API responses, or the OpenAlex snapshot extract. `.gitignore` excludes them.
- Keep SciSciNet values (`ss_*`, used as they are) and our own values (`own_*`) in separate columns. They are on different scales.
- Keys: `paper_uid` is one paper as listed on a website; `work_id` is the OpenAlex work ID; `paperid` is the SciSciNet paper ID.
- Environment variables: `SCISCI_*` for paths and options (each script lists its own at the top), `SCISCI_CONTACT_EMAIL` for the contact address sent to OpenAlex, `SCOPUS_API_KEY` for Scopus.
- Use Python 3.14. Comments in the code are in Japanese; `README.md` and `data/README.md` are in English.
- After changing a script, run `reproduce.ipynb` and confirm that the outputs still match, or say why they changed.
