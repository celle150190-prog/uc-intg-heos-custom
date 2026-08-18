from pathlib import Path

p = Path("upstream/uc_intg_heos/media_player.py")
s = p.read_text(encoding="utf-8")


def replace(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"Patch anchor not found:\n{old}")
    s = s.replace(old, new, 1)


# Only media_player.py is modified. The patch deliberately leaves the remote
# entity and the rest of the HEOS integration untouched.
replace(
    "import asyncio\nimport logging\nfrom typing import Any\n",
    "import asyncio\nimport logging\nimport urllib.error\nimport urllib.parse\nimport urllib.request\nfrom typing import Any\n",
)

replace(
    "    Features.NEXT,\n    Features.PREVIOUS,\n",
    "    Features.NEXT,\n    Features.PREVIOUS,\n    Features.CHANNEL_SWITCHER,\n",
)

replace(
    "        attrs[Attributes.SOURCE_LIST] = self._device.get_source_list(self._player_id)\n",
    "        source_list = list(self._device.get_source_list(self._player_id))\n"
    "        # HEOS is an AVR input/source and is exposed here so the Core\n"
    "        # activity editor can select AVR -> HEOS on this media entity.\n"
    "        if self._is_avr and \"HEOS\" not in source_list:\n"
    "            source_list.append(\"HEOS\")\n"
    "        attrs[Attributes.SOURCE_LIST] = source_list\n",
)

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

replace(
    "                case Commands.VOLUME_UP:\n                    await player.volume_up(params.get(\"step\", 5))\n\n                case Commands.VOLUME_DOWN:\n                    await player.volume_down(params.get(\"step\", 5))\n",
    "                case Commands.VOLUME_UP:\n                    await player.volume_up(1)\n\n                case Commands.VOLUME_DOWN:\n                    await player.volume_down(1)\n",
)

replace(
    "                    if not source:\n                        return StatusCodes.BAD_REQUEST\n                    found = await self._device.play_source_by_name(self._player_id, source)\n",
    "                    if not source:\n                        return StatusCodes.BAD_REQUEST\n                    if source == \"HEOS\" and self._is_avr:\n                        # First switch the Denon/Marantz AVR to its HEOS input,\n                        # then start/resume the HEOS player. This is what makes\n                        # AVR -> HEOS usable as a source in activities.\n                        await self._send_denon_command(\"MSHEOS\")\n                        await player.play()\n                        return StatusCodes.OK\n                    found = await self._device.play_source_by_name(self._player_id, source)\n",
)

insert_at = s.index("\ndef create_media_players(")
helpers = '''\n    async def _play_favorite_relative(self, delta: int) -> None:\n        """Play the next/previous saved HEOS favorite in HEOS preset order."""\n        favorites = list(self._device.favorites.items())\n        if not favorites:\n            raise HeosError("No HEOS favorites available")\n\n        player = self._device.get_player(self._player_id)\n        if not player:\n            raise HeosError("HEOS player unavailable")\n\n        current_index = None\n        now = player.now_playing_media\n        if now:\n            current_media_id = getattr(now, "media_id", None)\n            current_title = getattr(now, "station", None) or getattr(now, "song", None)\n            for index, (_, favorite) in enumerate(favorites):\n                favorite_media_id = getattr(favorite, "media_id", None)\n                favorite_name = getattr(favorite, "name", None)\n                if current_media_id is not None and favorite_media_id is not None and current_media_id == favorite_media_id:\n                    current_index = index\n                    break\n                if current_title and favorite_name and current_title == favorite_name:\n                    current_index = index\n                    break\n\n        # Wrap at the beginning/end of the saved-favorite list. If playback is\n        # not currently one of the favorites, NEXT starts at the first favorite\n        # and PREVIOUS starts at the last favorite.\n        if current_index is None:\n            target_index = 0 if delta > 0 else len(favorites) - 1\n        else:\n            target_index = (current_index + delta) % len(favorites)\n\n        favorite_id = favorites[target_index][0]\n        await player.play_preset_station(favorite_id)\n\n    async def _send_denon_command(self, command: str) -> None:\n        """Send a Denon/Marantz IP command through the receiver HTTP endpoint."""\n        encoded = urllib.parse.quote(command, safe="")\n        last_error: Exception | None = None\n\n        # Denon receivers from the X-series use port 8080; port 80 keeps\n        # compatibility with older models. Try 8080 first.\n        for port in (8080, 80):\n            url = (\n                f"http://{self._device.address}:{port}/"\n                f"goform/formiPhoneAppDirect.xml?{encoded}"\n            )\n            try:\n                def _request() -> None:\n                    with urllib.request.urlopen(url, timeout=2.5) as response:\n                        response.read(64)\n\n                await asyncio.to_thread(_request)\n                return\n            except (urllib.error.URLError, TimeoutError, OSError) as err:\n                last_error = err\n\n        raise HeosError(f"Denon command failed: {command}: {last_error}")\n'''
s = s[:insert_at] + helpers + s[insert_at:]
p.write_text(s, encoding="utf-8")
