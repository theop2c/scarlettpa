TOOLS = [

    # ========================================================
    # WEB SEARCH
    # ========================================================

    {
        "type": "function",

        "name": "search_web",

        "description": (
            "Recherche des informations sur Internet. "
            "À utiliser pour les informations récentes, "
            "actualités, résultats, prix, horaires, "
            "événements ou informations susceptibles "
            "d'avoir changé."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "query": {

                    "type": "string",

                    "description": (
                        "La recherche précise "
                        "à effectuer sur Internet."
                    ),
                },
            },

            "required": [
                "query",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # BROWSE URL
    # ========================================================

    {
        "type": "function",

        "name": "browse_url",

        "description": (
            "Ouvre réellement une page web précise "
            "avec Chromium et lit son contenu visible."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "url": {

                    "type": "string",

                    "description": (
                        "URL ou domaine "
                        "de la page à visiter."
                    ),
                },

                "question": {

                    "type": "string",

                    "description": (
                        "Ce que l'utilisateur "
                        "souhaite savoir "
                        "sur cette page."
                    ),
                },
            },

            "required": [
                "url",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # BROWSE SITE
    # ========================================================

    {
        "type": "function",

        "name": "browse_site",

        "description": (
            "Explore intelligemment plusieurs pages "
            "internes d'un même site pour trouver "
            "une information précise."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "url": {

                    "type": "string",

                    "description": (
                        "URL ou domaine "
                        "du site à explorer."
                    ),
                },

                "question": {

                    "type": "string",

                    "description": (
                        "Information précise "
                        "à rechercher dans le site."
                    ),
                },
            },

            "required": [
                "url",
                "question",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # SET VOLUME
    # ========================================================

    {
        "type": "function",

        "name": "set_volume",

        "description": (
            "Volume général de l'enceinte : "
            "s'applique à tout ce qui sort "
            "(voix de Scarlett, musique Spotify, "
            "radio). Utiliser pour monter, "
            "baisser, couper, réactiver ou "
            "définir le son global."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "action": {

                    "type": "string",

                    "enum": [
                        "set",
                        "increase",
                        "decrease",
                        "mute",
                        "unmute",
                        "max",
                    ],

                    "description": (
                        "Action à appliquer au volume."
                    ),
                },

                "value": {

                    "type": "integer",

                    "minimum": 0,
                    "maximum": 100,

                    "description": (
                        "Pour 'set', pourcentage cible. "
                        "Pour 'increase' ou 'decrease', "
                        "nombre de points de volume. "
                        "Si aucune valeur n'est donnée "
                        "pour augmenter ou diminuer, "
                        "utiliser 10."
                    ),
                },
            },

            "required": [
                "action",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # GET VOLUME
    # ========================================================

    {
        "type": "function",

        "name": "get_volume",

        "description": (
            "Retourne le volume actuel de Scarlett "
            "et indique si le son est coupé."
        ),

        "parameters": {

            "type": "object",

            "properties": {},

            "required": [],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # SPOTIFY PLAY
    # ========================================================

    {
        "type": "function",

        "name": "spotify_play",

        "description": (
            "Lance de la musique sur Spotify : "
            "un morceau, un artiste, un album "
            "ou une playlist."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "query": {

                    "type": "string",

                    "description": (
                        "Ce qu'il faut jouer : "
                        "titre du morceau avec artiste "
                        "si connu, nom d'artiste, "
                        "d'album ou de playlist."
                    ),
                },

                "type": {

                    "type": "string",

                    "enum": [
                        "track",
                        "artist",
                        "album",
                        "playlist",
                    ],

                    "description": (
                        "Nature de la demande. "
                        "Par défaut : track."
                    ),
                },
            },

            "required": [
                "query",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # SPOTIFY CONTROL
    # ========================================================

    {
        "type": "function",

        "name": "spotify_control",

        "description": (
            "Contrôle la lecture Spotify en cours : "
            "pause, reprise, morceau suivant ou "
            "précédent, et volume de la musique. "
            "Pour le volume de la voix de Scarlett, "
            "utiliser set_volume."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "action": {

                    "type": "string",

                    "enum": [
                        "pause",
                        "resume",
                        "next",
                        "previous",
                        "volume",
                    ],

                    "description": (
                        "Action à appliquer "
                        "à la lecture Spotify."
                    ),
                },

                "value": {

                    "type": "integer",

                    "minimum": 0,
                    "maximum": 100,

                    "description": (
                        "Pour 'volume' : pourcentage "
                        "cible de la musique."
                    ),
                },
            },

            "required": [
                "action",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # RADIO
    # ========================================================

    {
        "type": "function",

        "name": "radio",

        "description": (
            "Écoute de la radio française en "
            "direct : FIP, France Inter, France "
            "Info, France Musique, France "
            "Culture, Nova, Skyrock, NRJ, Fun "
            "Radio, RTL, RMC, BFM Business, "
            "Europe 1. Permet aussi de couper "
            "la radio, régler son volume ou "
            "connaître le titre en cours."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "action": {

                    "type": "string",

                    "enum": [
                        "play",
                        "stop",
                        "volume",
                        "current",
                    ],

                    "description": (
                        "play : lancer une station. "
                        "stop : couper la radio. "
                        "volume : régler le volume "
                        "de la radio. "
                        "current : titre en cours."
                    ),
                },

                "station": {

                    "type": "string",

                    "description": (
                        "Pour 'play' : nom de la "
                        "station demandée."
                    ),
                },

                "value": {

                    "type": "integer",

                    "minimum": 0,
                    "maximum": 100,

                    "description": (
                        "Pour 'volume' : pourcentage "
                        "cible."
                    ),
                },
            },

            "required": [
                "action",
            ],

            "additionalProperties":
                False,
        },
    },


    # ========================================================
    # SPOTIFY INFO
    # ========================================================

    {
        "type": "function",

        "name": "spotify_info",

        "description": (
            "Donne le morceau Spotify en cours "
            "de lecture, ou la liste des playlists "
            "de l'utilisateur."
        ),

        "parameters": {

            "type": "object",

            "properties": {

                "what": {

                    "type": "string",

                    "enum": [
                        "current_track",
                        "playlists",
                    ],

                    "description": (
                        "Information demandée."
                    ),
                },
            },

            "required": [
                "what",
            ],

            "additionalProperties":
                False,
        },
    },
]
