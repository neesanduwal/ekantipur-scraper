Ekantipur Entertainment & Cartoon Scraper
=========================================

Overview
--------
This project uses Playwright to scrape data from https://ekantipur.com.

It extracts:
1. Cartoon of the Day from https://ekantipur.com/cartoon
   - title
   - image_url
   - cartoonist

2. Top 5 entertainment articles from https://ekantipur.com/entertainment
   - title
   - image_url
   - category
   - author

All extracted data is saved as structured JSON in output.json.


Project Structure
-----------------
- scraper.py      : Main scraping script using Playwright (sync API).
- output.json     : Extracted data (cartoon + top 5 entertainment articles).
- pyproject.toml  : Project dependencies and configuration.
- prompts.txt     : Prompts used with Cursor AI during development.
- README.txt      : Project documentation (this file).


Dependencies
------------
This project uses Python 3.12+ and Playwright.

Dependencies are defined in pyproject.toml. You can install them using uv or pip.

Using uv (recommended if uv is installed):
    uv sync

Using pip:
    pip install playwright
    playwright install chromium


How It Works
------------
1. The script starts Playwright and launches a visible Chromium browser (non-headless).
2. It visits the Ekantipur homepage and then navigates to:
   - https://ekantipur.com/cartoon   for the Cartoon of the Day
   - https://ekantipur.com/entertainment   for entertainment articles
3. For the cartoon:
   - Finds the main image inside <main> or <article>.
   - Extracts the title from <h1> in main/article.
   - Tries to find the cartoonist via author links (/author/...).
   - Normalizes image URLs, handling src, data-* attributes, srcset, and thumb.php?src= wrappers.
4. For the entertainment section:
   - Locates article cards using the semantic "main article" selector.
   - For each of the first 5 articles, extracts title, thumbnail image, category/tag, and author.
   - Image URLs are again normalized and made absolute.
5. All data is combined into a single Python dictionary, written to output.json as UTF‑8 encoded JSON with indentation.
6. The script reopens output.json and prints the full JSON content to the console (with a small encoding workaround for Windows terminals).


Running the Scraper
-------------------
From the project directory (where scraper.py lives), run:

    python scraper.py

What you should see:
- Playwright will open a Chromium window and navigate through the required pages.
- After scraping, output.json will be created or updated.
- The script will print the contents of output.json in the terminal.


Output Format
-------------
output.json has the structure:

{
  "cartoon": {
    "title": "...",
    "image_url": "...",
    "cartoonist": "..."
  },
  "entertainment_articles": [
    {
      "title": "...",
      "image_url": "...",
      "category": "...",
      "author": "..."
    },
    ...
  ]
}


Notes on Selectors and Robustness
---------------------------------
- The scraper favors semantic selectors (main, article, h1, h2 a) over fragile CSS class names.
- Author and category links are detected using href patterns such as /author/, /tag/, and /category/.
- Images are resolved via src, data-src, data-original, data-lazy, and srcset, then normalized to absolute URLs.
- thumb.php?src= wrappers are unwrapped so that the direct underlying image URL is preserved in the output.


Using Cursor & Prompts
----------------------
The development process used Cursor AI to:
- Generate initial Playwright boilerplate.
- Suggest robust CSS selector strategies.
- Handle URL normalization and srcset parsing.
- Solve Windows console Unicode printing issues.

All key prompts used during development are listed in prompts.txt.


License
-------
For educational/demo use. Adjust or extend as needed for your own projects.