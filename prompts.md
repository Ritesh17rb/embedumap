# Prompts

<!--

cd /home/sanand/code/embedumap
dev.sh \
  -v /home/sanand/Downloads/csv-visualisation/:/home/sanand/Downloads/csv-visualisation/:ro \
  -v /home/sanand/Downloads/chart-map:/home/sanand/Downloads/chart-map:ro \
  -v /home/sanand/code/blog/analysis/embeddings/:/home/sanand/code/blog/analysis/embeddings/:ro \
  -v /home/sanand/code/calvinmap/:/home/sanand/code/calvinmap/:ro
codex --yolo --model gpt-5.4 --config model_reasoning_effort=xhigh

-->

I plan to create a command-line application that will create a single index.html that contains the UMAP embeddings visualization of an arbitrary CSV file.

I should be able to run this via:

```bash
uvx --from "git+https://github.com/sanand0/embedumap.git" embedumap ...
```

The output should be a single `index.html` file that I can open in a browser and see the UMAP visualization of the CSV file.
See /home/sanand/code/blog/analysis/embeddings/blogmap/index.html and /home/sanand/code/calvinmap/index.html as examples of the output.

The command line arguments must include:

- The CSV file path (can be local or a URL): required positional argument
- --embedding-columns: 0+ columns to include as text embeddings (text fields)
- --image-columns: 0+ columns to include the specified image URLs or filenames as image embeddings (e.g. the file column in calvinmap/index.html)
- --color-columns: 0+ columns to use as the color dimension (categorical fields, e.g. the category, cluster, or year in blogmap/index.html)
- --filter-columns: 0+ columns to expose as filters (categorical fields, e.g. years, categories, clusters dropdown in blogmap/index.html)
- --timeline-column: optional column to use as a timeline dimension (e.g. the year in blogmap/index.html, the date in calvinmap/index.html - see the timeline range slider at the bottom)
- --cluster-columns: 0+ columns to use for clustering. By default, the embeddings will be clustered using K-means. If cluster columns are provided, those will be used as the cluster labels instead of K-means. It can include "embeddings" as a special value to include the embeddings as clustering dimensions. --cluster-columns embeddings is the default. --cluster-columns embeddings,category would cluster using both the embeddings and the category column, which can be useful to get more semantically meaningful clusters.
- --label-column: 0+ columns to use as the primary label when hovering over points. By default, the first embedding column will be used as the label. If label columns are provided, those will be used as the label instead of the first embedding column. These will be truncated suitably to avoid overcrowding the tooltips. (Apart from the label column(s), all other columns will still be available in the tooltip when hovering over points.)
- --popup-style: table|grid|list. The style of the popup. "table" is the default. In every case, we want to show all CSV cells for the brushed/clicked row(s).
  - For table style, see the default in /home/sanand/code/blog/analysis/embeddings/blogmap/index.html.
  - For list style, see the default popups in /home/sanand/code/calvinmap/index.html.
  - For grid style, see the image popups in /home/sanand/Downloads/chart-map/index.html.
- --model: Which Gemini embedding model to use. `gemini-embedding-2-preview` is the default.
- --dimensions: Number of embeddings to use. 768 is the default.
- --sample N: Sample N rows before building
- --dry-run: Validate inputs and show what would be done without actually doing it

The `--*-columns` arguments should be able to take multiple column names separated by commas, e.g. `--embedding-columns text1,text2,text3` as well as multiple instances of the same argument, e.g. `--embedding-columns text1 --embedding-columns text2 --embedding-columns text3`.

Assume that `.env` will contain GEMINI_API_KEY.

Also keep in mind that the datasets I might cover could be very diverse. For example:

- Patent filings
- Research papers
- Videos, e.g the Warner Bros movie dataset with trailers, posters, metadata, etc. or their sports dataset with match highlights, player photos, stats, etc.
- Large image datasets, e.g. the Times of India image archive, or the Open Food Facts product images, or the historical map archive from the David Rumsey Map Collection.
- Tabular datasets, e.g. the Indian census
- Audio datasets, e.g. Parliament questions and debates, Arijit Singh songs

These are not yet covered. Factor that in. Also keep in mind that these requirements are not necessarily complete. Go through the other code bases while planning:

- /home/sanand/code/blog/analysis/embeddings/ - the primary source for text embedding visualization
- /home/sanand/code/calvinmap/ - the primary source for image embedding visualization
- /home/sanand/Downloads/chart-map - the secondary source for image embedding visualization

... and based on these, consider how the requirements might be expanded.

DO NOT COMPLICATE. Keep the CLI and implementation as simple and ELEGANT as possible, delegating the hard word to Gemini (e.g. embedding videos, audio, images, text, etc.). Feel free to drop what's hard (e.g. embedding large videos isn't possible and that's OK).

Research online for what you need - best practices, use cases, etc.

Don't execute this yet.
Analyze CAREFULLY. Create a plan.
Give me an easy way to verify your plan and assumptions before you start coding.
Make a list of questions you have for me.
Document what I should look at in `notes.md` under a `## How to review the plan` giving me a checklist of things to verify in the plan.

---

I agree with the plan except for the following changes:

- For v1, drop thumbnails. We will show only the full images, if they're available. No need to create thumbnails or embed them or link to them. Skip the thumbnail concept for now.
- In all three popup modes, allow sorting by timeline and any other CSV column, not just in `table` mode. The default sort when timeline is present should be by timeline, but the user can change it to any column they want.

Additionally, use the newly added `uv-uvx` skill to understand how to create a repo that can work like this:

```bash
uvx --from "git+https://github.com/sanand0/embedumap.git@main" embedumap ...
```

Based on these, revise PLAN.md.

Commit as you go (including prompts.md which I'm editing). Create a public repo using the `gh` CLI and test the `uvx --from ...` workflow with it before you finish the implementation.

Then implement it and test it on small datasets derived from the samples I've provided.

Implement EFFICIENTLY. Use sub-agents as required.

### Enhancements 1

Append PLAN.md with the following under an `# Enhancements 1` section:

- Resumable embedding cache. Keep it minimal - for example, if only .duckdb is needed and not the .parquet, that's fine. Or any other lightweight, elegant approach.
- Audio embedding
- Cluster naming by LLM using a lightweight model like `gemini-3.1-flash-lite-preview` or `gemini-3-flash-preview`, passing the top-N closest rows across all clusters as context and asking for a structured JSON output with the name for each cluster - characterizing the cluster well (not too broadly/narrowly), while also disambiguating clusters with similar themes.
- A test text dataset with ~300 rows that can be used to test the application, along with instructions on how to run it with that dataset. I should just be able to type the command even without cloning the repo and it should generate an index.html with uvx cloning from GitHub and pulling the dataset from GitHub.

Give me an easy way to verify your plan and assumptions before you start coding.
Make a list of questions you have for me.
Update `notes.md` under a `## How to review Enhancements 1` with a checklist of things to verify in the plan.

---

I agree with the plan & assumptions. Here are answers to your questions:

1. I want the resumable cache to be on by default
2. Store the cache in the current working directory, next to the output HTML. (Add it it .gitignore, along with index.html)
3. Add an option for the user to include audio metadata but by default only embed the audio contents
4. Expose cluster naming as a build flag from the start
5. Prefer reasonably short names - disambiguating similar neighboring clusters is important, but short is equally important
6. The ~300-row test dataset just needs to be representative and convenient

Based on these, revise PLAN.md.

Implement it and test it EFFICIENTLY. Use sub-agents as required. Commit as you go (including prompts.md which I'm editing).

---

There are a few problems.

- Show an elegant loading indicator while the dataset loads - it can be quite large sometimes.
- Brushing does not work. When I drag and release, no popup appears. The references I have you had these working.
- Escape does not close popup. The close button is not positioned well - the references had an icon on the right. Closing the popup shows a blurred set of circles. Clicking fixes the opacity.
- There's no play option in timeline. Dragging the timeline range does not work. Again, something that's working on the references.
- Usebetter formatting of timeline labels (auto-discover - it might be year, date, datetime, etc. Format accordingly. ISO date is terrible for UI.)
- Add a CLI option for the page branding that will appear on the top left.
- Add a CLI option for opacity that defaults to 1.

Implement it and test it EFFICIENTLY. Use sub-agents as required. Commit as you go (including prompts.md which I'm editing).

---

More fixes:

- Brushing works, but the rectangle that should appear when I brush does not appear.
- The dropdowns show light grey on white when opened, making them almost invisible.

Review the code for any other issues, opportunities to simplify, or refactor for elegance.
Implement it and test it EFFICIENTLY. Use sub-agents as required. Commit as you go (including prompts.md which I'm editing).

---

Modify the HTML to:

- Make the state (filters, time range, color, etc.) bookmarkable and shareable. See reference implementations

<!-- codex --yolo --model gpt-5.4 --config model_reasoning_effort=xhigh resume 019d3df6-1192-7b01-be69-3b5f2a092a92 -->
