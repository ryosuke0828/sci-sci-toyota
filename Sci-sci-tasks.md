# 2026-27 Toyota—SciSci

<aside>
<img src="https://app.notion.com/icons/bullseye_gray.svg" alt="https://app.notion.com/icons/bullseye_gray.svg" width="40px" />

**Background**:

- I am studying the research activities of researchers and engineers at Toyota Motor Corporation.
- I would like to use a “Science of Science” approach to understand how Toyota researchers collaborate and generate knowledge.
- I am interested in questions such as:
    - Where and under what conditions do innovations emerge?
    - Which researchers or engineers become especially successful or influential?
    - What kinds of teams or collaboration structures lead to better research outcomes?
- However, I do not have much experience collecting or analyzing this type of data, so I would appreciate your help in learning the basics and conducting data collection and analysis.

**Assistants**: Sota Hayashi and Ryosuke Ikura

**Task**: Data collection and analysis / Paper reading and discussion

</aside>

[Ryosuke notes](https://app.notion.com/p/Ryosuke-notes-376793f76bf6807c98baca73334910d8?pvs=21)

[Sota notes](https://app.notion.com/p/Sota-notes-379793f76bf680ef9a93ce7f13eefbe1?pvs=21)

## Task

### Preliminary: “What is Science of Science”?

- Read “Science of Science” to have an overview idea.
- Tick the box below when you finish reading the book
    - [x]  Ryosuke
    - [x]  Sota

### Explore OpenAlex

https://openalex.org/

<aside>
<img src="https://app.notion.com/icons/bullseye_gray.svg" alt="https://app.notion.com/icons/bullseye_gray.svg" width="40px" />

The purpose of this task is to become familiar with OpenAlex as a major source of scholarly metadata and to evaluate its usefulness for future Science of Science research projects.

We want to understand:

1. What information OpenAlex records.
2. How the database is structured.
3. What information is missing or difficult to obtain.
4. How to retrieve data programmatically using Python or R.
</aside>

OpenAlex is an open scholarly knowledge graph containing information on:

- Works (papers, books, etc.)
- Authors
- Institutions
- Sources (journals, conferences, repositories)
- Topics and concepts
- Citations and references
- Funding information (when available)

Many contemporary Science of Science studies use OpenAlex either directly or as a complement to other data sources.

→ For this task, use members of your lab (PI, faculty, postdocs, PhD students, etc.) as example cases whenever possible.

#### Step 1: Manual exploration

Spend some time exploring OpenAlex through its website and API documentation.

- Choose “target” researchers (e.g. your lab PI or other lab members whose works you are familiar with)
- For each person:
    - Locate their author profile.
    - Examine:
        - publication list
        - affiliations
        - citation counts
        - coauthors
        - topics
        - … and other information you can find
    - Follow links to have rough ideas about the structure
- Record observations about:
    - what information is available
    - what appears to be missing
    - any obvious errors or ambiguities
- Deliverable: Create a subpage and:
    - Use it as a working memo.
    - Document your findings there.
    
    → At an appropriate point, consolidate the two notes into a single document and walk me through the key observations.
    

Important: I do not yet have a full understanding of the data structure—that is the primary reason for this task. At this stage, any information, observations, or findings you uncover will be valuable and may help inform future work.

#### Step 2: API Exploration “Manual to Automation”

Goal: Write Python codes (and Jupyter notebook) that retrieve data through the OpenAlex API.

Note: The instructions below are provided as guidance only and do not need to be followed exactly. As you work through the task, you will likely gain a better understanding of OpenAlex than I currently have, so please use your judgment and feel free to explore any directions that seem valuable or relevant.

1. Author retrieval
    - Input: PI name or OpenAlex Author ID
    - Output:
        - author metadata
        - publication count
        - citation count
2. Publication retrieval
    - Publications for the selected author.
    - Extract:
        - title
        - publication year
        - citation count
        - journal/source
        - authorship information
3. Citation analysis
    - Fix a paper as the “target” and
        - retrieve papers cited in the target paper
        - retrieve papers that cite the target paper
4. … and probably many other things you can do with API— be creative!

### Build a Researcher Database

[To be added]

[More instructions will be added and refined below.]

- Read and discuss the following papers as a team
    - https://doi.org/10.1038/s41597-023-02198-9
    - https://www.nature.com/articles/s43588-025-00906-6
- Study the literature on measuring “novelty,” “hot streak,” …, and related concepts.
    - [Identify and prioritize key papers for reading and discussion.]
- Data collection
    - Collect and organize data from:
        - Toyota-related websites (via web scraping)
        - OpenAlex
        - Other relevant sources as needed.

Note: We want to exploit the team power— You two may have different strengths so let’s try to communicate and allocate tasks in a way that maximizes the overall quality of your work and our understanding.