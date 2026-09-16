import re

from urllib.parse import (
    urlparse,
    urljoin,
    urldefrag,
)

from playwright.async_api import (
    async_playwright,
)

from config import (
    CHROMIUM_PATH,
    MAX_SITE_PAGE_CHARS,
    MAX_SITE_RESULT_CHARS,
    MAX_SITE_DEPTH,
    MAX_LINKS_FOR_SELECTION,
    SITE_LINKS_PER_STEP,
    MAX_LINK_SELECTION_CALLS,
)

from utils.security import (
    url_is_allowed,
)

from tools.link_selector import (
    select_relevant_links,
)


# ============================================================
# CONSTANTS
# ============================================================

SKIP_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".mp3",
    ".wav",
    ".mp4",
    ".avi",
    ".mov",
    ".zip",
    ".rar",
    ".7z",
    ".exe",
    ".dmg",
    ".apk",
)


# ============================================================
# URL HELPERS
# ============================================================

def normalize_domain(
    url: str
) -> str:

    return (
        urlparse(url)
        .netloc
        .lower()
        .replace(
            "www.",
            "",
        )
    )


def normalize_link(
    base_url: str,
    href: str,
):

    if not href:

        return None

    href = href.strip()

    if href.startswith(
        (
            "mailto:",
            "tel:",
            "javascript:",
            "#",
        )
    ):

        return None

    absolute = urljoin(
        base_url,
        href,
    )

    absolute, _ = urldefrag(
        absolute
    )

    parsed = urlparse(
        absolute
    )

    if parsed.scheme not in (
        "http",
        "https",
    ):

        return None

    lowered_path = (
        parsed.path.lower()
    )

    if lowered_path.endswith(
        SKIP_EXTENSIONS
    ):

        return None

    return absolute


def clean_link_text(
    text: str
) -> str:

    if not text:

        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()[:200]


# ============================================================
# PAGE TEXT CLEANING
# ============================================================

def clean_page_text(
    text: str
) -> str:

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# EXTRACT INTERNAL LINKS
# ============================================================

async def extract_internal_links(
    page,
    current_url: str,
    allowed_domain: str,
    already_known: set,
):

    raw_links = (
        await page
        .locator("a[href]")
        .evaluate_all(
            """
            els => els.map(
                el => ({
                    href:
                        el.getAttribute('href'),

                    text:
                        (
                            el.innerText
                            || el.getAttribute('aria-label')
                            || el.getAttribute('title')
                            || ''
                        ).trim()
                })
            )
            """
        )
    )

    results = []

    seen_here = set()

    for item in raw_links:

        link = normalize_link(
            current_url,
            item.get(
                "href"
            ),
        )

        if not link:

            continue

        if (
            normalize_domain(link)
            != allowed_domain
        ):

            continue

        if (
            link in already_known
            or link in seen_here
        ):

            continue

        parsed = urlparse(
            link
        )

        # Évite quelques routes inutiles classiques.
        path_lower = (
            parsed.path.lower()
        )

        blocked_parts = (
            "/login",
            "/logout",
            "/signin",
            "/sign-in",
            "/wp-admin",
            "/cart",
            "/checkout",
        )

        if any(
            part in path_lower
            for part in blocked_parts
        ):

            continue

        seen_here.add(
            link
        )

        results.append(
            {
                "url": link,
                "text": clean_link_text(
                    item.get(
                        "text",
                        ""
                    )
                ),
            }
        )

        if (
            len(results)
            >= MAX_LINKS_FOR_SELECTION
        ):

            break

    return results


# ============================================================
# SITE BROWSER V3.2
# ============================================================

async def browse_site(
    start_url: str,
    question: str,
    max_pages: int = 5,
    max_depth: int = None,
):

    print()
    print(
        "===================================="
    )
    print(
        "🧠 NAVIGATION INTELLIGENTE V3.2"
    )
    print(
        "===================================="
    )

    print(
        "Site :",
        start_url
    )

    print(
        "Question :",
        question
    )

    if max_depth is None:

        max_depth = (
            MAX_SITE_DEPTH
        )

    if not start_url.startswith(
        (
            "http://",
            "https://",
        )
    ):

        start_url = (
            "https://"
            + start_url
        )

    allowed, reason = (
        url_is_allowed(
            start_url
        )
    )

    if not allowed:

        return reason

    start_domain = (
        normalize_domain(
            start_url
        )
    )

    visited = set()

    queued = {
        start_url
    }

    # queue:
    # (url, profondeur)
    queue = [
        (
            start_url,
            0,
        )
    ]

    collected = []

    selector_calls = 0

    async with (
        async_playwright()
        as p
    ):

        browser = (
            await p.chromium.launch(

                headless=True,

                executable_path=
                    CHROMIUM_PATH,

                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
        )

        context = (
            await browser.new_context(

                viewport={
                    "width": 1280,
                    "height": 900,
                },

                user_agent=(
                    "Mozilla/5.0 "
                    "(X11; Linux aarch64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/130 Safari/537.36"
                ),
            )
        )

        while (
            queue
            and len(visited)
            < max_pages
        ):

            (
                requested_url,
                depth,
            ) = queue.pop(0)

            if (
                requested_url
                in visited
            ):

                continue

            allowed, reason = (
                url_is_allowed(
                    requested_url
                )
            )

            if not allowed:

                print(
                    "[SITE] URL refusée :",
                    reason
                )

                continue

            if (
                normalize_domain(
                    requested_url
                )
                != start_domain
            ):

                continue

            print()
            print(
                "[SITE] Page "
                f"{len(visited)+1}/"
                f"{max_pages}"
                f" | profondeur {depth}/"
                f"{max_depth}"
            )

            print(
                "[SITE]",
                requested_url
            )

            page = (
                await context.new_page()
            )

            try:

                response = (
                    await page.goto(

                        requested_url,

                        wait_until=
                            "domcontentloaded",

                        timeout=20000,
                    )
                )

                try:

                    await (
                        page
                        .wait_for_load_state(

                            "networkidle",

                            timeout=4000,
                        )
                    )

                except Exception:

                    pass

                final_url = (
                    page.url
                )

                allowed, reason = (
                    url_is_allowed(
                        final_url
                    )
                )

                if not allowed:

                    print(
                        "[SITE] "
                        "Redirection refusée :",
                        reason
                    )

                    continue

                if (
                    normalize_domain(
                        final_url
                    )
                    != start_domain
                ):

                    print(
                        "[SITE] "
                        "Redirection hors domaine."
                    )

                    continue

                if final_url in visited:

                    continue

                title = (
                    await page.title()
                )

                status = (
                    response.status
                    if response
                    else None
                )

                # ============================================
                # LINKS BEFORE DOM CLEANUP
                # ============================================

                known_urls = (
                    visited
                    | queued
                )

                links = (
                    await extract_internal_links(

                        page,

                        final_url,

                        start_domain,

                        known_urls,
                    )
                )


                # ============================================
                # CLEAN PAGE
                # ============================================

                await page.evaluate(
                    """
                    () => {
                        document
                          .querySelectorAll(
                            'script,style,noscript,svg,canvas'
                          )
                          .forEach(
                            el => el.remove()
                          );
                    }
                    """
                )


                # ============================================
                # EXTRACT CONTENT
                # ============================================

                text = (
                    await page
                    .locator("body")
                    .inner_text()
                )

                text = (
                    clean_page_text(
                        text
                    )
                )

                if (
                    len(text)
                    > MAX_SITE_PAGE_CHARS
                ):

                    text = (
                        text[
                            :MAX_SITE_PAGE_CHARS
                        ]
                        + "\n\n"
                        "[Page tronquée]"
                    )

                visited.add(
                    final_url
                )

                collected.append(
                    (
                        "\n\n"
                        "===== PAGE CONSULTÉE =====\n"

                        f"Titre : {title}\n"

                        f"URL : {final_url}\n"

                        f"HTTP : {status}\n"

                        f"Profondeur : {depth}\n\n"

                        f"{text}"
                    )
                )

                print(
                    "[SITE] Page lue :",
                    title
                )

                print(
                    "[SITE]",
                    len(text),
                    "caractères"
                )

                print(
                    "[SITE]",
                    len(links),
                    "liens internes candidats"
                )


                # ============================================
                # SMART LINK SELECTION
                # ============================================

                remaining_pages = (
                    max_pages
                    - len(visited)
                )

                if (
                    remaining_pages > 0
                    and depth < max_depth
                    and links
                ):

                    number_to_select = min(
                        SITE_LINKS_PER_STEP,
                        remaining_pages,
                    )

                    if (
                        selector_calls
                        < MAX_LINK_SELECTION_CALLS
                    ):

                        selector_calls += 1

                        selected_links = (
                            await select_relevant_links(

                                question=
                                    question,

                                current_url=
                                    final_url,

                                page_title=
                                    title,

                                links=
                                    links,

                                max_results=
                                    number_to_select,
                            )
                        )

                    else:

                        # Le sélecteur contient lui-même
                        # un fallback local, mais au-delà
                        # de la limite on évite un appel API.
                        from tools.link_selector import (
                            local_rank_links,
                        )

                        selected_links = (
                            local_rank_links(

                                question,

                                links,

                                number_to_select,
                            )
                        )


                    # ========================================
                    # DEPTH-FIRST PRIORITY
                    # ========================================

                    new_entries = []

                    for item in selected_links:

                        selected_url = (
                            item.get(
                                "url"
                            )
                        )

                        if not selected_url:

                            continue

                        if (
                            selected_url
                            in visited
                            or selected_url
                            in queued
                        ):

                            continue

                        queued.add(
                            selected_url
                        )

                        new_entries.append(
                            (
                                selected_url,
                                depth + 1,
                            )
                        )

                    # On privilégie immédiatement les liens
                    # trouvés sur la page la plus pertinente.
                    queue = (
                        new_entries
                        + queue
                    )


            except Exception as error:

                print(
                    "[SITE] Erreur :",
                    error
                )

            finally:

                await page.close()


        await browser.close()


    # ========================================================
    # OUTPUT
    # ========================================================

    if not collected:

        return (
            "Je n'ai réussi à lire "
            "aucune page de ce site."
        )

    result = (
        "QUESTION DE L'UTILISATEUR:\n"
        f"{question}\n\n"

        "RÉSUMÉ DE LA NAVIGATION:\n"
        f"Pages réellement consultées : "
        f"{len(visited)}\n"

        f"Profondeur maximale autorisée : "
        f"{max_depth}\n"

        f"Sélections intelligentes effectuées : "
        f"{selector_calls}\n"

        + "".join(
            collected
        )
    )

    if (
        len(result)
        > MAX_SITE_RESULT_CHARS
    ):

        result = (
            result[
                :MAX_SITE_RESULT_CHARS
            ]
            + "\n\n"
            "[Résultat global tronqué]"
        )

    print()
    print(
        "[SITE] Navigation terminée."
    )

    print(
        "[SITE] Pages consultées :",
        len(visited)
    )

    return result
