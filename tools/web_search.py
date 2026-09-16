from config import WEB_MODEL

from realtime.client import (
    get_openai_client,
)


async def search_web(
    query: str
) -> str:

    print()
    print(
        "===================================="
    )
    print(
        "🌐 RECHERCHE WEB"
    )
    print(
        "===================================="
    )
    print(
        "Recherche :",
        query
    )
    print()

    client = get_openai_client()

    try:

        response = (
            await client.responses.create(

                model=WEB_MODEL,

                tools=[
                    {
                        "type":
                            "web_search"
                    }
                ],

                input=(
                    "Recherche sur Internet "
                    "des informations récentes "
                    "et fiables pour répondre "
                    "à la demande suivante. "

                    "Réponds en français, "
                    "de manière factuelle "
                    "et concise. "

                    "La réponse sera ensuite "
                    "lue oralement par Scarlett.\n\n"

                    f"Demande : {query}"
                )
            )
        )

        result = (
            response.output_text
        )

        print(
            "Résultat web :"
        )

        print(
            result
        )

        return result

    except Exception as error:

        print(
            "Erreur search_web :",
            error
        )

        return (
            "La recherche Internet "
            "a échoué. "
            f"Erreur technique : {error}"
        )
