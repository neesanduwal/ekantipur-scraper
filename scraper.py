from urllib.parse import parse_qs, unquote, urljoin, urlparse
import json

from playwright.sync_api import sync_playwright


def _first_url_from_srcset(srcset: str | None) -> str | None:
    """Parse srcset and return the first candidate URL (if any)."""
    if not srcset:
        return None
    
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


def _unwrap_thumb_php(maybe_thumb_url: str | None) -> str | None:
    """
    If the URL looks like a thumb.php?src=... wrapper, return the direct `src` URL.
    Otherwise, return the original URL unchanged.
    """
    if not maybe_thumb_url:
        return None
    u = maybe_thumb_url.strip()
    parsed = urlparse(u)
    if not parsed.path.endswith("/thumb.php"):
        return u
    qs = parse_qs(parsed.query)
    src_vals = qs.get("src") or []
    if not src_vals:
        return u
    
    return unquote(src_vals[0]) or u


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

        # Avoid "networkidle" on news sites (they often keep long-polling/analytics open).
        # Instead, wait for a basic, stable DOM element that indicates the page is rendered.
        page.wait_for_load_state("load")
        page.locator("body").wait_for(state="visible", timeout=30_000)

        # --- Cartoon of the Day (homepage: व्यंग्यचित्र / कार्टुन) ---
        # Navigate to the dedicated cartoon page, which reliably represents
        # the current "Cartoon of the Day".
        page.goto("https://ekantipur.com/cartoon", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Wait for the main cartoon content to be visible (best-effort; don't crash if layout changes).
        hero_img = page.locator("main img, article img").first
        if hero_img.count() > 0:
            hero_img.wait_for(state="visible", timeout=30_000)

        # Title (cartoon headline) - return None if missing
        cartoon_title: str | None = None
        title_loc = page.locator("main h1, article h1").first
        if title_loc.count() > 0:
            t = title_loc.inner_text().strip()
            cartoon_title = t or None

        # Image URL (handle relative / lazy / srcset)
        cartoon_img = page.locator("main img, article img").first
        cartoon_src = None
        if cartoon_img.count() > 0:
            cartoon_src = cartoon_img.get_attribute("src")
        if not cartoon_src and cartoon_img.count() > 0:
            cartoon_src = (
                cartoon_img.get_attribute("data-src")
                or cartoon_img.get_attribute("data-original")
                or cartoon_img.get_attribute("data-lazy")
                or cartoon_img.get_attribute("data-srcset")
            )
        if not cartoon_src and cartoon_img.count() > 0:
            cartoon_src = _first_url_from_srcset(cartoon_img.get_attribute("srcset"))

        cartoon_image_url = _resolve_to_absolute(page.url, cartoon_src)
        # Ensure we return a direct/original image URL even if the site wraps it with thumb.php?src=...
        cartoon_image_url = _unwrap_thumb_php(cartoon_image_url)

        # Cartoonist name (if present; otherwise None)
        cartoonist: str | None = None
        cartoon_author_loc = page.locator('a[href^="/author/"], a[href^="https://ekantipur.com/author/"]').first
        if cartoon_author_loc.count() > 0:
            text = cartoon_author_loc.inner_text().strip()
            cartoonist = text or None

        cartoon = {
            "title": cartoon_title,
            "image_url": cartoon_image_url,
            "cartoonist": cartoonist,
        }

        print("\nCartoon of the Day:")
        print(f"  title: {cartoon['title']}")
        print(f"  image_url: {cartoon['image_url']}")
        print(f"  cartoonist: {cartoon['cartoonist']}")

        # --- Entertainment section (top 5 articles) ---
        # Go to the entertainment section labeled “मनोरञ्जन”.
        page.goto("https://ekantipur.com/entertainment", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Wait until at least one news article card is visible.
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

        # --- Write all extracted data to output.json ---
        data = {
            "cartoon": cartoon,
            "entertainment_articles": articles,
        }

        output_path = "output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Show the contents of output.json after extraction.
        print(f"\nWrote extracted data to {output_path}. Full contents:")
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Safely print even if console encoding can't handle some characters.
            safe_content = content.encode("cp1252", errors="replace").decode("cp1252")
            print(safe_content)

        # Close the browser context and the browser
        context.close()
        browser.close()

if __name__ == "__main__":
    main()