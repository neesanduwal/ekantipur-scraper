from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


def _first_url_from_srcset(srcset: str | None) -> str | None:
    """Parse srcset and return the first candidate URL (if any)."""
    if not srcset:
        return None
    # Example: "https://a.jpg 1x, https://b.jpg 2x"
    first = srcset.split(",")[0].strip()
    return first.split()[0].strip() if first else None


def _resolve_to_absolute(base_url: str, maybe_url: str | None) -> str | None:
    """Resolve relative/protocol-relative URLs to an absolute URL."""
    if not maybe_url:
        return None
    u = maybe_url.strip()
    if u.startswith("//"):
        return "https:" + u
    return urljoin(base_url, u)

def main():
    # Start the Playwright context manager
    with sync_playwright() as p:
        # Launch Chromium browser in non-headless mode (visible window)
        browser = p.chromium.launch(headless=False)

        # Open a new browser context (like a separate user profile)
        context = browser.new_context()

        # Open a new page (tab) in the context
        page = context.new_page()

        # Navigate to the ekantipur homepage
        page.goto("https://ekantipur.com", wait_until="domcontentloaded")

        # Wait for the network to be mostly idle to ensure the page has loaded
        # Adjust timeout or wait strategy later as needed for scraping
        page.wait_for_load_state("networkidle")

        # Click on the Entertainment section labeled “मनोरञ्जन”.
        # We use a role-based locator for resilience (it will match a visible link named exactly that).
        entertainment_link = page.get_by_role("link", name="मनोरञ्जन").first

        # Clicking may trigger either a full navigation or a client-side route change.
        # Wait for a URL that looks like the entertainment section, then wait for articles to appear.
        with page.expect_url("**/entertainment**", timeout=30_000):
            entertainment_link.click()

        # Ensure the entertainment page finishes loading.
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")

        # Wait until at least one news article card is visible (no data extraction yet).
        # Using semantic HTML (`article`) is typically more stable than class-based selectors.
        page.locator("main article").first.wait_for(state="visible", timeout=30_000)

        # Optional (still no extraction): ensure the first card has a clickable title link.
        page.locator("main article h2 a").first.wait_for(state="visible", timeout=30_000)

        # Extract the top 5 entertainment articles as a list of dictionaries.
        # We iterate per `article` card so fields stay aligned.
        article_cards = page.locator("main article")
        articles: list[dict[str, str | None]] = []

        for i in range(5):
            card = article_cards.nth(i)

            # Title (headline link text)
            title = card.locator("h2 a").first.inner_text().strip()

            # Category/section label
            # On the entertainment section page this is often implicitly "मनोरञ्जन", but we
            # still attempt to find a per-card label if the UI provides one.
            category: str | None = None
            category_locator = card.locator(
                # Common patterns for category/tag links in news card UIs
                'a[href^="/tag/"], a[href^="/category/"], a[class*="tag"], a[class*="category"]'
            ).first
            if category_locator.count() > 0:
                category_text = category_locator.inner_text().strip()
                category = category_text or None
            if category is None:
                category = "मनोरञ्जन"

            # Author name (return None if missing)
            author: str | None = None
            author_locator = card.locator('a[href^="/author/"], a[href^="https://ekantipur.com/author/"]').first
            if author_locator.count() > 0:
                author_text = author_locator.inner_text().strip()
                author = author_text or None

            # Thumbnail image URL (handle lazy-loaded/relative URLs)
            img = card.locator("img").first
            src = None
            if img.count() > 0:
                src = img.get_attribute("src")
            if not src:
                # Common lazy-load attributes (site may use one of these)
                if img.count() > 0:
                    src = (
                        img.get_attribute("data-src")
                        or img.get_attribute("data-original")
                        or img.get_attribute("data-lazy")
                        or img.get_attribute("data-srcset")
                    )

            if not src:
                # If only srcset is present, take the first candidate URL
                if img.count() > 0:
                    src = _first_url_from_srcset(img.get_attribute("srcset"))

            thumbnail_url = _resolve_to_absolute(page.url, src)

            articles.append(
                {
                    "title": title,
                    "image_url": thumbnail_url,
                    "category": category,
                    "author": author,
                }
            )

        # Print the structured list (no file output yet).
        print("\nTop 5 Entertainment (structured):")
        for idx, article in enumerate(articles, start=1):
            print(f"{idx}. title: {article['title']}")
            print(f"   image_url: {article['image_url']}")
            print(f"   category: {article['category']}")
            print(f"   author: {article['author']}")

        # Close the browser context and the browser
        context.close()
        browser.close()

if __name__ == "__main__":
    main()