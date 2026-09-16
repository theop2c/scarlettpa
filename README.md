# Scarlett

Assistant vocal maison en français, tournant en local sur Raspberry Pi 5, avec conversation temps réel via OpenAI Realtime, recherche web et navigation intelligente multi-pages.

Version actuelle : **V3.2**

## Fonctionnalités

- **Wake word local** — détection « Hey Jarvis » 100 % locale via modèles ONNX (openWakeWord), aucun audio envoyé au cloud en veille
- **Conversation vocale** — dialogue naturel en français via l'API OpenAI Realtime (`gpt-realtime-2.1-mini`)
- **Recherche web** (`search_web`) — réponses à jour via un modèle avec accès web
- **Navigation URL** (`browse_url`) — lecture d'une page précise via Chromium headless (Playwright)
- **Navigation multi-pages** (`browse_site`) — exploration d'un site sur plusieurs pages (jusqu'à 2 niveaux de profondeur) avec sélection intelligente des liens internes à suivre
- **Contrôle du volume** (`set_volume` / `get_volume`) — pourcentage précis, augmenter/diminuer, mute/unmute, maximum, avec persistance du niveau entre les redémarrages
- **Spotify** (`spotify_play` / `spotify_control` / `spotify_info`) — « mets Get Lucky de Daft Punk » : morceau, artiste, album ou playlist, pause/reprise, suivant/précédent, volume de la musique, morceau en cours ; le Pi est l'enceinte Spotify Connect « Scarlett » (raspotify), et la voix de Scarlett se mixe par-dessus la musique (ALSA dmix)

## Matériel

- Raspberry Pi 5 (`scarlett-bureau`)
- Micro RØDE NT-USB Mini
- Enceinte USB

## Pipeline

```
« Hey Jarvis »
   ↓
wake word local (ONNX)
   ↓
bip de confirmation
   ↓
session OpenAI Realtime
   ↓
compréhension de la demande
   ↓
tool éventuel
   ├── search_web
   ├── browse_url
   ├── browse_site
   ├── set_volume
   └── get_volume
   ↓
réponse vocale
   ↓
retour en veille
```

### Navigation intelligente (browse_site)

```
« Explore ce site et trouve les conditions »

homepage
   ↓
extraction des liens
   ↓
sélection intelligente des liens (LLM)
   ↓
visite de plusieurs pages
   ↓
jusqu'à 2 niveaux de profondeur
   ↓
synthèse vocale
```

## Structure du projet

```
scarlett/
├── app.py                  # Point d'entrée
├── config.py               # Configuration centralisée (.env + valeurs par défaut)
├── .env                    # Secrets et overrides (non versionné)
├── requirements.txt
│
├── audio/
│   ├── player.py           # Lecture audio, bip
│   └── volume.py           # Volume logiciel + persistance
│
├── wakeword/
│   ├── engine.py           # Détection du wake word
│   └── models/             # Modèles ONNX (non versionnés)
│
├── realtime/
│   ├── client.py           # Client OpenAI Realtime
│   ├── session.py          # Boucle de conversation
│   ├── tool_definitions.py # Schémas des tools exposés au modèle
│   └── tools_router.py     # Routage des appels de tools
│
├── tools/
│   ├── web_search.py       # Recherche web
│   ├── browser.py          # Navigation d'une URL (Playwright/Chromium)
│   ├── site_browser.py     # Exploration multi-pages d'un site
│   └── link_selector.py    # Sélection intelligente des liens à suivre
│
├── prompts/
│   └── scarlett.txt        # Prompt système de Scarlett
│
├── utils/
│   └── security.py         # Garde-fous réseau (validation d'URL, IP privées…)
│
└── state/
    └── volume.json         # État persistant du volume (non versionné)
```

## Installation

```bash
git clone git@github.com:theop2c/scarlettpa.git ~/scarlett
cd ~/scarlett
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Modèles de wake word

Les modèles ONNX ne sont pas versionnés. Télécharger depuis [openWakeWord](https://github.com/dscripka/openWakeWord) et placer dans `wakeword/models/` :

- `melspectrogram.onnx`
- `embedding_model.onnx`
- `hey_jarvis_v0.1.onnx`

### Configuration

```bash
cp .env.example .env
```

Puis renseigner au minimum `OPENAI_API_KEY`. Les autres variables (périphériques audio, modèles, seuil de wake word, limites de navigation…) ont des valeurs par défaut raisonnables — voir [.env.example](.env.example) et [config.py](config.py).

Les index `INPUT_DEVICE` / `OUTPUT_DEVICE` correspondent aux périphériques listés par :

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### Spotify (V4)

Nécessite un compte Spotify **Premium**.

**a. Sortie audio partagée** — pour que la voix de Scarlett et la musique se mixent sur la même enceinte, créer `/etc/asound.conf` :

```
pcm.usb_dmix {
    type dmix
    ipc_key 20481
    ipc_perm 0666
    slave {
        pcm "hw:CARD=Device,DEV=0"
        format S16_LE
        rate 48000
        channels 2
        period_size 1024
        buffer_size 8192
    }
}
pcm.scarlett_out {
    type plug
    slave.pcm "usb_dmix"
}
pcm.raspotify_out {
    type plug
    slave.pcm "usb_dmix"
}
```

(`CARD=Device` = nom ALSA de l'enceinte USB, cf. `aplay -l`.) Puis dans `.env` : `OUTPUT_DEVICE=scarlett_out`.

**b. raspotify** — le Pi devient une enceinte Spotify Connect :

```bash
curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
```

Dans `/etc/raspotify/conf` :

```
LIBRESPOT_NAME="Scarlett"
LIBRESPOT_BACKEND="alsa"
LIBRESPOT_DEVICE="raspotify_out"
LIBRESPOT_BITRATE="320"
LIBRESPOT_VOLUME_CTRL="linear"
LIBRESPOT_INITIAL_VOLUME="70"
```

`VOLUME_CTRL=linear` est important : avec la courbe `log` par défaut, un volume Spotify de 50 % est quasi inaudible. Redémarrer avec `sudo systemctl restart raspotify`.

**c. API Web Spotify** — créer une app sur [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) (Redirect URI : `http://127.0.0.1:8888/callback`, Web API), renseigner `SPOTIFY_CLIENT_ID` et `SPOTIFY_CLIENT_SECRET` dans `.env`, puis s'authentifier une fois :

```bash
.venv/bin/python scripts/spotify_auth.py
```

**d. Première connexion** — l'enceinte « Scarlett » ne s'enregistre sur le compte qu'après avoir été sélectionnée une première fois depuis l'app Spotify (téléphone ou desktop, sur le même réseau) : lancer un morceau et choisir « Scarlett » dans le sélecteur d'appareils.

## Lancement

```bash
source .venv/bin/activate
python app.py
```

Dire « Hey Jarvis », attendre le bip, puis parler. La session se ferme après un délai d'inactivité (`CONVERSATION_TIMEOUT`, 20 s par défaut) et Scarlett retourne en veille.

## Roadmap

- ~~**V4** — Spotify~~ ✅
- **V4.1** — YouTube
- **V5** — vrai wake word « Hey Scarlett » (modèle local personnalisé)
- **V6** — conversation naturelle (barge-in, echo cancellation, interruptions)
- **V7** — mémoire locale (préférences, paramètres)
- **V8** — navigation web active (clics, formulaires, avec confirmations)
- **V9** — service systemd (lancement au boot, restart auto, logs)
- **V10** — Home Assistant (Philips Hue, radio, timers, automatisations)
- **V11** — satellites (Raspberry salon + chambre, le bureau reste le cerveau central)
- **V12** — architecture multi-modèles (realtime mini pour la conversation, modèle plus puissant pour les demandes complexes)
