import json
import re
from typing import List, Dict

from config import (
    LINK_SELECTOR_MODEL,
    MAX_LINKS_FOR_SELECTION,
)

from realtime.client import (
    get_openai_client,
)


# ============================================================
# LOCAL FALLBACK
# ============================================================

def local_rank_links(
    question: str,
    links: List[Dict],
    max_results: int,
) -> List[Dict]:

    words = {
        word.lower()
        for word in re.findall(
            r"\w+",
            question
        )
        if len(word) >= 4
    }

    ranked = []

    for link in links:

        text = (
            (
                link.get("text", "")
                + " "
                + link.get("url", "")
            )
            .lower()
        )

        score = 0

        for word in words:

            if word in text:
                score += 3

        # Quelques indices génériques utiles
        useful_terms = [
            "about",
            "a-propos",
            "apropos",
            "tarif",
            "price",
            "pricing",
            "faq",
            "condition",
            "service",
            "vendeur",
            "seller",
            "contact",
            "legal",
            "mentions",
            "partner",
            "partenaire",
            "agent",
        ]

        for term in useful_terms:

            if term in text:
                score += 1

        ranked.append(
            (
                score,
                link
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        item[1]
        for item in ranked[
            :max_results
        ]
    ]


# ============================================================
# JSON PARSER
# ============================================================

def parse_indexes(
    raw: str
) -> List[int]:

    if not raw:

        return []

    raw = raw.strip()

    # Supprime éventuellement les fences Markdown
    raw = re.sub(
        r"^```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    raw = re.sub(
        r"```$",
        "",
        raw,
    )

    raw = raw.strip()

    # On cherche uniquement un tableau JSON.
    start = raw.find("[")
    end = raw.rfind("]")

    if (
        start == -1
        or end == -1
        or end <= start
    ):

        return []

    try:

        data = json.loads(
            raw[start:end + 1]
        )

    except Exception:

        return []

    if not isinstance(
        data,
        list
    ):

        return []

    indexes = []

    for value in data:

        try:

            index = int(
                value
            )

        except Exception:

            continue

        if index not in indexes:

            indexes.append(
                index
            )

    return indexes


# ============================================================
# AI LINK SELECTOR
# ============================================================

async def select_relevant_links(
    question: str,
    current_url: str,
    page_title: str,
    links: List[Dict],
    max_results: int = 3,
) -> List[Dict]:

    if not links:

        return []

    # Limite le nombre de liens envoyés au modèle.
    links = links[
        :MAX_LINKS_FOR_SELECTION
    ]

    client = get_openai_client()

    formatted = []

    for index, link in enumerate(
        links
    ):

        formatted.append(
            (
                f"[{index}] "
                f"{link.get('text', '')} "
                f"-> {link.get('url', '')}"
            )
        )

    links_text = "\n".join(
        formatted
    )

    prompt = f"""
Tu aides un navigateur web autonome à choisir les liens internes
les plus pertinents pour répondre à une question.

QUESTION:
{question}

PAGE ACTUELLE:
Titre: {page_title}
URL: {current_url}

LIENS DISPONIBLES:
{links_text}

Choisis au maximum {max_results} liens qui ont le plus de chances
de mener à l'information demandée.

RÈGLES:
- Ne sélectionne que des identifiants présents dans la liste.
- Privilégie les pages de contenu, FAQ, services, tarifs,
  conditions, mentions, contact ou pages spécialisées pertinentes.
- Évite les réseaux sociaux.
- Évite les fichiers, images, login et logout.
- Évite les liens sans rapport avec la question.
- Si plusieurs liens semblent utiles, classe le meilleur en premier.
- Si aucun lien n'est pertinent, renvoie [].

Réponds UNIQUEMENT avec un tableau JSON d'identifiants.

Exemple:
[4, 1, 7]
""".strip()

    print()
    print(
        "[SELECTOR] Analyse intelligente "
        f"de {len(links)} liens..."
    )

    try:

        response = (
            await client.responses.create(
                model=LINK_SELECTOR_MODEL,
                input=prompt,
            )
        )

        raw = (
            response.output_text
            or ""
        )

        indexes = parse_indexes(
            raw
        )

        selected = []

        for index in indexes:

            if (
                0 <= index
                < len(links)
            ):

                selected.append(
                    links[index]
                )

            if (
                len(selected)
                >= max_results
            ):

                break

        if selected:

            print(
                "[SELECTOR] Liens retenus :"
            )

            for link in selected:

                print(
                    " -",
                    link.get(
                        "url",
                        ""
                    )
                )

            return selected

        print(
            "[SELECTOR] Aucun résultat IA, "
            "fallback local."
        )

    except Exception as error:

        print(
            "[SELECTOR] Erreur :",
            error
        )

    return local_rank_links(
        question,
        links,
        max_results,
    )
