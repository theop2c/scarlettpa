import os
import re

from playwright.async_api import (
    async_playwright,
)

from config import (
    CHROMIUM_PATH,
    MAX_PAGE_CHARS,
)

from utils.security import (
    url_is_allowed,
)


async def browse_url(
    url: str,
    question: str = "",
):

    print()
    print(
        "===================================="
    )
    print(
        "🌍 NAVIGATION WEB"
    )
    print(
        "===================================="
    )
    print(
        "URL :",
        url
    )
    print(
        "Question :",
        question
    )
    print()

    if not url.startswith(
        (
            "http://",
            "https://",
        )
    ):

        url = (
            "https://"
            + url
        )

    allowed, reason = (
        url_is_allowed(
            url
        )
    )

    if not allowed:

        return reason

    if not os.path.exists(
        CHROMIUM_PATH
    ):

        return (
            "Chromium n'est pas installé "
            f"à {CHROMIUM_PATH}."
        )

    try:

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

                    user_agent=(
                        "Mozilla/5.0 "
                        "(X11; Linux aarch64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/130 Safari/537.36"
                    ),

                    viewport={
                        "width": 1280,
                        "height": 900,
                    },
                )
            )

            page = (
                await context.new_page()
            )

            page.set_default_timeout(
                20000
            )

            print(
                "[WEB] Chargement "
                "de la page..."
            )

            response = (
                await page.goto(

                    url,

                    wait_until=
                        "domcontentloaded",

                    timeout=20000,
                )
            )

            try:

                await (
                    page.wait_for_load_state(

                        "networkidle",

                        timeout=5000,
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

                await browser.close()

                return (
                    "Redirection refusée. "
                    + reason
                )

            title = (
                await page.title()
            )

            status = (
                response.status
                if response
                else None
            )

            await page.evaluate(
                """
                () => {
                    document.querySelectorAll(
                        'script,style,noscript,svg,canvas'
                    ).forEach(
                        el => el.remove()
                    );
                }
                """
            )

            text = (
                await page
                .locator("body")
                .inner_text()
            )

            await browser.close()

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        ).strip()

        if (
            len(text)
            > MAX_PAGE_CHARS
        ):

            text = (
                text[
                    :MAX_PAGE_CHARS
                ]
                + "\n\n"
                "[Contenu tronqué]"
            )

        print(
            f"[WEB] Page lue : {title}"
        )

        print(
            "[WEB] "
            f"{len(text)} caractères "
            "extraits"
        )

        return (
            f"Titre : {title}\n"
            f"URL finale : {final_url}\n"
            f"HTTP : {status}\n\n"

            "Question utilisateur : "
            f"{question}\n\n"

            "Contenu visible :\n"
            f"{text}"
        )

    except Exception as error:

        print(
            "Erreur browse_url :",
            error
        )

        return (
            "Je n'ai pas réussi "
            "à ouvrir cette page. "
            f"Erreur : {error}"
        )
