"""
Jukebox MCP server
Stdio transport for Claude Desktop (Vesper, Cora, and future family members).

Tools: now_playing, search_music, get_playlists, get_playlist,
       like_song, add_to_playlist, create_playlist, recommend_music
Resources: music://now-playing (subscribable)
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP, Context

JUKEBOX_URL = "http://127.0.0.1:4319"
NOW_PLAYING_URI = "music://now-playing"
POLL_INTERVAL = 30

_active_session = None
_last_track: str = ""


async def _poll_now_playing():
    """Background task: detect track changes and notify."""
    global _last_track, _active_session
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            async with httpx.AsyncClient(base_url=JUKEBOX_URL, timeout=5.0) as c:
                r = await c.get("/now-playing")
                if r.status_code != 200:
                    continue
                data = r.json()
                track_id = data.get("video_id", "")

            if _last_track and track_id != _last_track:
                session = _active_session
                if session is not None:
                    try:
                        await session.send_resource_updated(NOW_PLAYING_URI)
                    except Exception:
                        _active_session = None

            _last_track = track_id
        except Exception:
            pass


@asynccontextmanager
async def lifespan(server):
    task = asyncio.create_task(_poll_now_playing())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


mcp = FastMCP(
    name="jukebox",
    lifespan=lifespan,
    instructions=(
        "This is the Harrell family Jukebox — Nathan's YouTube Music integration. "
        "Use now_playing to see what Nathan is listening to. "
        "Use search_music to find songs, albums, or artists. "
        "Use get_playlists to browse Nathan's playlists. "
        "Use like_song to like a track. "
        "Use recommend_music for AI-powered music suggestions. "
        "The music://now-playing resource updates when the track changes."
    ),
)


def _sync_client() -> httpx.Client:
    return httpx.Client(base_url=JUKEBOX_URL, timeout=10.0)


def _capture_session(ctx: Context):
    global _active_session
    _active_session = ctx.session


def _offline_msg() -> str:
    return "❌ Jukebox is offline. Ask Nathan to run: ~/charos/jukebox/start.sh"


# --- Resource ---

@mcp.resource(
    NOW_PLAYING_URI,
    name="Now Playing",
    description="What Nathan is currently listening to. Updates automatically when the track changes.",
    mime_type="text/plain",
)
def now_playing_resource() -> str:
    try:
        with _sync_client() as c:
            r = c.get("/now-playing")
            r.raise_for_status()
            data = r.json()
        if not data.get("playing"):
            return "🎵 Nothing playing right now."
        return f"🎵 {data['artists']} — {data['title']}"
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"Error: {e}"


# --- Tools ---

@mcp.tool()
def now_playing(ctx: Context) -> str:
    """See what Nathan is currently listening to."""
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.get("/now-playing")
            r.raise_for_status()
            data = r.json()
        if not data.get("playing"):
            return "🎵 Nothing playing right now."
        parts = [f"🎵 Now Playing:"]
        parts.append(f"  {data['artists']} — {data['title']}")
        if data.get("album"):
            parts.append(f"  Album: {data['album']}")
        return "\n".join(parts)
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def search_music(query: str, type: str = "songs", ctx: Optional[Context] = None) -> str:
    """
    Search YouTube Music for songs, albums, artists, or playlists.

    Args:
        query: What to search for
        type: Type of result — songs, albums, artists, playlists
    """
    if ctx:
        _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.get("/search", params={"q": query, "type": type})
            r.raise_for_status()
            results = r.json()
        if not results:
            return f"No {type} found for '{query}'."
        lines = [f"🔍 {type.title()} matching '{query}':\n"]
        for i, item in enumerate(results[:10], 1):
            if type == "songs":
                lines.append(f"  {i}. {item['artists']} — {item['title']} [{item.get('video_id','')}]")
            elif type == "albums":
                lines.append(f"  {i}. {item.get('artists','')} — {item['title']} ({item.get('year','')})")
            elif type == "artists":
                lines.append(f"  {i}. {item['name']} ({item.get('subscribers','')})")
            elif type == "playlists":
                lines.append(f"  {i}. {item['title']} by {item.get('author','')}")
        return "\n".join(lines)
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def get_playlists(ctx: Context) -> str:
    """Browse Nathan's YouTube Music playlists."""
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.get("/playlists")
            r.raise_for_status()
            playlists = r.json()
        if not playlists:
            return "No playlists found."
        lines = ["📋 Nathan's Playlists:\n"]
        for p in playlists:
            lines.append(f"  {p['title']} ({p.get('count', '?')} tracks) [{p['id']}]")
        return "\n".join(lines)
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def get_playlist(playlist_id: str, ctx: Context) -> str:
    """
    Get tracks in a specific playlist.

    Args:
        playlist_id: The playlist ID
    """
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.get(f"/playlist/{playlist_id}")
            r.raise_for_status()
            data = r.json()
        lines = [f"📋 {data['title']} ({data.get('count', '?')} tracks):\n"]
        for i, t in enumerate(data.get("tracks", [])[:20], 1):
            lines.append(f"  {i}. {t['artists']} — {t['title']}")
        if data.get("count", 0) > 20:
            lines.append(f"\n  ... and {data['count'] - 20} more")
        return "\n".join(lines)
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def like_song(video_id: str, ctx: Context) -> str:
    """
    Like a song on YouTube Music.

    Args:
        video_id: The video ID of the song to like
    """
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.post("/like", json={"video_id": video_id})
            r.raise_for_status()
        return f"❤️ Liked! (video_id: {video_id})"
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def add_to_playlist(playlist_id: str, video_id: str, ctx: Context) -> str:
    """
    Add a song to a playlist.

    Args:
        playlist_id: The playlist ID
        video_id: The video ID of the song to add
    """
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.post(f"/playlist/{playlist_id}/add", json={"video_id": video_id})
            r.raise_for_status()
        return f"➕ Added to playlist!"
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def create_playlist(title: str, description: str = "", video_ids: list[str] = [], ctx: Optional[Context] = None) -> str:
    """
    Create a new YouTube Music playlist.

    Args:
        title: Playlist name
        description: Playlist description
        video_ids: Optional list of video IDs to add initially
    """
    if ctx:
        _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.post("/playlist/create", json={"title": title, "description": description, "video_ids": video_ids})
            r.raise_for_status()
            data = r.json()
        return f"🎵 Created playlist '{title}'! ID: {data.get('playlist_id', '?')}"
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def recommend_music(ctx: Context) -> str:
    """Get AI-powered music recommendations based on Nathan's recent listening."""
    _capture_session(ctx)
    try:
        with _sync_client() as c:
            r = c.get("/recommend")
            r.raise_for_status()
            data = r.json()
        recs = data.get("recommendations", [])
        if not recs:
            return "🤷 No recommendations — not enough listening history yet."
        lines = [f"🎧 Recommendations ({data.get('reason', '')}):\n"]
        for i, r in enumerate(recs[:10], 1):
            lines.append(f"  {i}. {r['artists']} — {r['title']} [{r.get('video_id','')}]")
        return "\n".join(lines)
    except httpx.ConnectError:
        return _offline_msg()
    except Exception as e:
        return f"❌ Error: {e}"


if __name__ == "__main__":
    mcp.run()
