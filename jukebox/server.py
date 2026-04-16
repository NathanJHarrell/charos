"""
Jukebox — CHAROS YouTube Music HTTP backend
FastAPI + ytmusicapi, port 4319

The family jukebox. TC, Vesper, Cora, and Nathan can see what's playing,
search music, curate playlists, and get recommendations.
"""

import time
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ytmusicapi import YTMusic

AUTH_PATH = Path(__file__).parent / "auth" / "headers_auth.json"

# Simple in-memory cache
_cache: dict[str, tuple[float, any]] = {}
_cache_lock = threading.Lock()

# Rate limiter: max 1 req/sec to YouTube Music
_last_api_call = 0.0
_rate_lock = threading.Lock()


def _rate_limit():
    """Enforce 1 request/sec to YouTube Music API."""
    global _last_api_call
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_api_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_api_call = time.monotonic()


def _get_cached(key: str, ttl: float) -> any:
    with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if time.time() - ts < ttl:
                return val
    return None


def _set_cached(key: str, val: any):
    with _cache_lock:
        _cache[key] = (time.time(), val)


def _get_ytmusic() -> YTMusic:
    if not AUTH_PATH.exists():
        raise HTTPException(status_code=503, detail="YouTube Music not authenticated. Run: ytmusicapi browser --file auth/headers_auth.json")
    return YTMusic(str(AUTH_PATH))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="jukebox", lifespan=lifespan)


# --- Models ---

class LikeSong(BaseModel):
    video_id: str


class AddToPlaylist(BaseModel):
    video_id: str


class CreatePlaylist(BaseModel):
    title: str
    description: str = ""
    video_ids: list[str] = []


# --- Helpers ---

def _format_track(item: dict) -> dict:
    """Normalize a track/song item from ytmusicapi into a clean dict."""
    artists = ", ".join(a.get("name", "?") for a in item.get("artists", []) if isinstance(a, dict))
    return {
        "video_id": item.get("videoId", ""),
        "title": item.get("title", "Unknown"),
        "artists": artists,
        "album": item.get("album", {}).get("name", "") if isinstance(item.get("album"), dict) else "",
        "duration": item.get("duration", ""),
        "thumbnail": (item.get("thumbnails", [{}])[-1].get("url", "") if item.get("thumbnails") else ""),
    }


# --- Routes ---

@app.get("/health")
def health():
    auth_ok = AUTH_PATH.exists()
    return {"status": "ok", "authenticated": auth_ok}


@app.get("/now-playing")
def now_playing():
    """Most recent track from history — our 'now playing' proxy."""
    cached = _get_cached("now-playing", 30)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    history = yt.get_history()
    if not history:
        return {"playing": False}

    track = _format_track(history[0])
    track["playing"] = True
    _set_cached("now-playing", track)
    return track


@app.get("/history")
def get_history(limit: int = Query(default=20, le=100)):
    """Recent play history."""
    cached = _get_cached(f"history-{limit}", 30)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    history = yt.get_history()
    tracks = [_format_track(t) for t in history[:limit]]
    _set_cached(f"history-{limit}", tracks)
    return tracks


@app.get("/search")
def search(q: str = Query(...), type: str = Query(default="songs")):
    """Search YouTube Music."""
    valid_types = {"songs", "albums", "artists", "playlists", "videos"}
    if type not in valid_types:
        raise HTTPException(400, f"type must be one of: {valid_types}")

    cache_key = f"search-{q}-{type}"
    cached = _get_cached(cache_key, 300)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    results = yt.search(q, filter=type)

    if type == "songs":
        formatted = [_format_track(r) for r in results[:20]]
    elif type == "artists":
        formatted = [{"id": r.get("browseId", ""), "name": r.get("artist", ""), "subscribers": r.get("subscribers", "")} for r in results[:20]]
    elif type == "albums":
        formatted = [{
            "id": r.get("browseId", ""),
            "title": r.get("title", ""),
            "artists": ", ".join(a.get("name", "") for a in r.get("artists", []) if isinstance(a, dict)),
            "year": r.get("year", ""),
        } for r in results[:20]]
    elif type == "playlists":
        formatted = [{"id": r.get("browseId", ""), "title": r.get("title", ""), "author": r.get("author", "")} for r in results[:20]]
    else:
        formatted = results[:20]

    _set_cached(cache_key, formatted)
    return formatted


@app.get("/playlists")
def get_playlists():
    """User's playlists."""
    cached = _get_cached("playlists", 600)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    playlists = yt.get_library_playlists(limit=50)
    formatted = [{
        "id": p.get("playlistId", ""),
        "title": p.get("title", ""),
        "count": p.get("count", 0),
    } for p in playlists]
    _set_cached("playlists", formatted)
    return formatted


@app.get("/playlist/{playlist_id}")
def get_playlist(playlist_id: str):
    """Tracks in a playlist."""
    cache_key = f"playlist-{playlist_id}"
    cached = _get_cached(cache_key, 600)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    playlist = yt.get_playlist(playlist_id, limit=200)
    result = {
        "title": playlist.get("title", ""),
        "description": playlist.get("description", ""),
        "count": playlist.get("trackCount", 0),
        "tracks": [_format_track(t) for t in playlist.get("tracks", [])],
    }
    _set_cached(cache_key, result)
    return result


@app.get("/library/songs")
def get_library_songs():
    """Liked songs."""
    cached = _get_cached("library-songs", 600)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    songs = yt.get_library_songs(limit=100)
    formatted = [_format_track(s) for s in songs]
    _set_cached("library-songs", formatted)
    return formatted


@app.get("/library/albums")
def get_library_albums():
    """Saved albums."""
    cached = _get_cached("library-albums", 600)
    if cached is not None:
        return cached

    _rate_limit()
    yt = _get_ytmusic()
    albums = yt.get_library_albums(limit=100)
    formatted = [{
        "id": a.get("browseId", ""),
        "title": a.get("title", ""),
        "artists": ", ".join(ar.get("name", "") for ar in a.get("artists", []) if isinstance(ar, dict)),
        "year": a.get("year", ""),
    } for a in albums]
    _set_cached("library-albums", formatted)
    return formatted


# --- Curation ---

@app.post("/like")
def like_song(body: LikeSong):
    """Like a song."""
    _rate_limit()
    yt = _get_ytmusic()
    yt.rate_song(body.video_id, "LIKE")
    # Invalidate library cache
    with _cache_lock:
        _cache.pop("library-songs", None)
    return {"ok": True, "video_id": body.video_id}


@app.post("/playlist/{playlist_id}/add")
def add_to_playlist(playlist_id: str, body: AddToPlaylist):
    """Add a track to a playlist."""
    _rate_limit()
    yt = _get_ytmusic()
    yt.add_playlist_items(playlist_id, [body.video_id])
    # Invalidate playlist cache
    with _cache_lock:
        _cache.pop(f"playlist-{playlist_id}", None)
    return {"ok": True, "playlist_id": playlist_id, "video_id": body.video_id}


@app.post("/playlist/create")
def create_playlist(body: CreatePlaylist):
    """Create a new playlist."""
    _rate_limit()
    yt = _get_ytmusic()
    playlist_id = yt.create_playlist(body.title, body.description, video_ids=body.video_ids or None)
    # Invalidate playlists cache
    with _cache_lock:
        _cache.pop("playlists", None)
    return {"ok": True, "playlist_id": playlist_id}


@app.get("/recommend")
def recommend():
    """Analyze recent history and suggest similar music."""
    _rate_limit()
    yt = _get_ytmusic()
    history = yt.get_history()
    if not history:
        return {"recommendations": [], "reason": "No listening history"}

    # Get unique artists from recent history
    recent_artists = set()
    recent_titles = set()
    for track in history[:10]:
        for artist in track.get("artists", []):
            if isinstance(artist, dict) and artist.get("name"):
                recent_artists.add(artist["name"])
        if track.get("title"):
            recent_titles.add(track["title"])

    # Search for related music
    recommendations = []
    seen_ids = set()
    for artist in list(recent_artists)[:3]:
        _rate_limit()
        results = yt.search(f"{artist} similar", filter="songs")
        for r in results[:5]:
            vid = r.get("videoId", "")
            title = r.get("title", "")
            if vid and vid not in seen_ids and title not in recent_titles:
                seen_ids.add(vid)
                recommendations.append(_format_track(r))
        if len(recommendations) >= 15:
            break

    return {
        "recommendations": recommendations[:15],
        "based_on_artists": list(recent_artists)[:5],
        "reason": f"Based on your recent listening: {', '.join(list(recent_artists)[:3])}",
    }
