from pathlib import Path

p = Path("upstream/uc_intg_heos/media_player.py")
s = p.read_text(encoding="utf-8")


def replace(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"Patch anchor not found:\n{old}")
    s = s.replace(old, new, 1)


# Denon AVR commands are used for AVR master volume and channel-level controls.
replace(
    "import asyncio\nimport logging\nfrom typing import Any\n",
    "import asyncio\nimport logging\nimport urllib.error\nimport urllib.parse\nimport urllib.request\nfrom typing import Any\n",
)

# Expose Channel +/- in the media UI. The existing Volume Up/Down feature remains intact.
replace(
    "    Features.NEXT,\n    Features.PREVIOUS,\n",
    "    Features.NEXT,\n    Features.PREVIOUS,\n    Features.CHANNEL_SWITCHER,\n",
)

# Add a logical HEOS source for Denon/Marantz AVR activities without changing the
# existing HEOS music-source/favorite list.
replace(
    "        attrs[Attributes.SOURCE_LIST] = self._device.get_source_list(self._player_id)\n",
    "        source_list = list(self._device.get_source_list(self._player_id))\n"
    "        if self._is_avr and \"HEOS\" not in source_list:\n"
    "            source_list.append(\"HEOS\")\n"
    "        attrs[Attributes.SOURCE_LIST] = source_list\n",
)

# Replace media-player next/previous and volume/channel handling.
replace(
    "                case Commands.NEXT:\n                    await player.play_next()\n\n                case Commands.PREVIOUS:\n                    await player.play_previous()\n",
    "                case Commands.NEXT:\n                    await self._play_favorite_relative(1)\n\n"
    "                case Commands.PREVIOUS:\n                    await self._play_favorite_relative(-1)\n\n"
    "                case Commands.CHANNEL_UP:\n"
    "                    if not self._is_avr:\n"
    "                        return StatusCodes.NOT_IMPLEMENTED\n"
    "                    await self._send_denon_command(\"CVSW UP\")\n\n"
    "                case Commands.CHANNEL_DOWN:\n"
    "                    if not self._is_avr:\n"
    "                        return StatusCodes.NOT_IMPLEMENTED\n"
    "                    await self._send_denon_command(\"CVSW DOWN\")\n",
)

# For AVR media UI volume controls use Denon's master-volume protocol directly.
# Two Denon MV steps make one 1 dB adjustment on this AVR generation.
replace(
    "                case Commands.VOLUME_UP:\n                    await player.volume_up(params.get(\"step\", 5))\n\n                case Commands.VOLUME_DOWN:\n                    await player.volume_down(params.get(\"step\", 5))\n",
    "                case Commands.VOLUME_UP:\n                    if self._is_avr:\n                        await self._send_denon_volume_step(1)\n                    else:\n                        await player.volume_up(1)\n\n"
    "                case Commands.VOLUME_DOWN:\n                    if self._is_avr:\n                        await self._send_denon_volume_step(-1)\n                    else:\n                        await player.volume_down(1)\n",
)

# Selecting HEOS in an activity must switch the actual Denon AVR input to HEOS Music.
# Denon's IP protocol identifies HEOS Music as the NET source (SINET).
replace(
    "                    if not source:\n                        return StatusCodes.BAD_REQUEST\n                    found = await self._device.play_source_by_name(self._player_id, source)\n",
    "                    if not source:\n                        return StatusCodes.BAD_REQUEST\n                    if source == \"HEOS\" and self._is_avr:\n                        await self._send_denon_command(\"SINET\")\n                        await asyncio.sleep(0.2)\n                        await player.play()\n                        return StatusCodes.OK\n                    found = await self._device.play_source_by_name(self._player_id, source)\n",
)

# Safer favorite browsing: honor the Remote's requested page/limit instead of returning
# the complete favorite collection in one response. This avoids UI freezes with large
# favorite lists while retaining artwork URLs.
old_browse = '''            if not media_id or media_id == "root":\n                raw_items = await self._device.browse_root()\n            elif media_id == "favorites":\n                raw_items = await self._device.browse_favorites()\n            elif media_id == "inputs":\n'''
new_browse = '''            if not media_id or media_id == "root":\n                raw_items = await self._device.browse_root()\n            elif media_id == "favorites":\n                favorites = list(self._device.favorites.items())\n                page = max(1, getattr(options.paging, "page", 1))\n                limit = max(1, min(getattr(options.paging, "limit", 10), 100))\n                start = (page - 1) * limit\n                raw_items = [\n                    {\n                        "media_id": f"favorite_{idx}",\n                        "title": fav.name,\n                        "thumbnail": fav.image_url or None,\n                        "can_browse": False,\n                        "can_play": True,\n                        "media_class": "radio",\n                    }\n                    for idx, fav in favorites[start : start + limit]\n                ]\n            elif media_id == "inputs":\n'''
replace(old_browse, new_browse)

# Return the requested page metadata for favorites. For other browse paths keep the
# upstream behavior unchanged.
old_result = '''            return BrowseResults(\n                media=root_item,\n                pagination=Pagination(page=1, limit=len(browse_items), count=len(browse_items)),\n            )\n'''
new_result = '''            if media_id == "favorites":\n                total = len(self._device.favorites)\n                page = max(1, getattr(options.paging, "page", 1))\n                limit = max(1, min(getattr(options.paging, "limit", 10), 100))\n                pagination = Pagination(page=page, limit=len(browse_items), count=total)\n            else:\n                pagination = Pagination(page=1, limit=len(browse_items), count=len(browse_items))\n            return BrowseResults(media=root_item, pagination=pagination)\n'''
replace(old_result, new_result)

# Helpers are inserted immediately before create_media_players().
insert_at = s.index("\ndef create_media_players(")
helpers = r'''
    async def _play_favorite_relative(self, delta: int) -> None:
        """Play the next/previous saved HEOS favorite in the HEOS preset order."""
        favorites = list(self._device.favorites.items())
        if not favorites:
            raise HeosError("No HEOS favorites available")

        now = self._player.now_playing_media
        current_index = None
        if now:
            current_media_id = getattr(now, "media_id", None)
            current_name = getattr(now, "station", None) or getattr(now, "song", None)
            for pos, (_favorite_id, favorite) in enumerate(favorites):
                favorite_media_id = getattr(favorite, "media_id", None)
                favorite_name = getattr(favorite, "name", None)
                if current_media_id and favorite_media_id and current_media_id == favorite_media_id:
                    current_index = pos
                    break
                if current_name and favorite_name and current_name == favorite_name:
                    current_index = pos
                    break

        if current_index is None:
            target_index = 0 if delta > 0 else len(favorites) - 1
        else:
            target_index = (current_index + delta) % len(favorites)

        favorite_id = favorites[target_index][0]
        await self._player.play_preset_station(favorite_id)

    async def _send_denon_command(self, command: str) -> None:
        """Send a Denon IP command through its HTTP direct-control endpoint."""
        encoded = urllib.parse.quote(command, safe="")
        last_error: Exception | None = None
        for port in (8080, 80):
            url = f"http://{self._device.address}:{port}/goform/formiPhoneAppDirect.xml?{encoded}"
            try:
                def _request() -> None:
                    with urllib.request.urlopen(url, timeout=2.0) as response:
                        response.read(128)
                await asyncio.to_thread(_request)
                return
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last_error = err
        raise HeosError(f"Denon command failed ({command}): {last_error}")

    async def _send_denon_volume_step(self, direction: int) -> None:
        """Adjust AVR master volume by exactly 1 dB (two 0.5 dB Denon steps)."""
        command = "MVUP" if direction > 0 else "MVDOWN"
        await self._send_denon_command(command)
        await asyncio.sleep(0.08)
        await self._send_denon_command(command)
'''
s = s[:insert_at] + helpers + s[insert_at:]
p.write_text(s, encoding="utf-8")
