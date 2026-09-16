import os

from openai import AsyncOpenAI


_client = None


def get_openai_client():

    global _client

    if _client is not None:

        return _client

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENAI_API_KEY absente. "
            "Ajoute-la dans ~/scarlett/.env"
        )

    _client = AsyncOpenAI(
        api_key=api_key
    )

    return _client
