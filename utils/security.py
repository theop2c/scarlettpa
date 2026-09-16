import socket
import ipaddress

from urllib.parse import (
    urlparse,
)


def url_is_allowed(
    url: str
):

    try:

        parsed = urlparse(
            url
        )

        if parsed.scheme not in (
            "http",
            "https",
        ):

            return (
                False,
                "Seules les URL HTTP "
                "et HTTPS sont autorisées.",
            )

        hostname = (
            parsed.hostname
        )

        if not hostname:

            return (
                False,
                "Nom d'hôte invalide.",
            )

        addresses = (
            socket.getaddrinfo(
                hostname,
                None,
            )
        )

        for address in addresses:

            ip_string = (
                address[4][0]
            )

            ip = (
                ipaddress.ip_address(
                    ip_string
                )
            )

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):

                return (
                    False,
                    "Navigation refusée "
                    "vers une adresse "
                    "locale ou privée.",
                )

        return (
            True,
            "",
        )

    except Exception as error:

        return (
            False,
            "Impossible de valider "
            f"l'URL : {error}",
        )
