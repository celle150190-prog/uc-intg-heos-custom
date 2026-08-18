#!/usr/bin/env python3
"""Patch HEOS v2.1.2 remote.py so PREV/NEXT start from the currently playing favorite."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REMOTE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("uc_intg_heos/remote.py")

text = REMOTE.read_text(encoding="utf-8")

pattern = re.compile(
    r"    @staticmethod\n"
    r"    def _favorite_position\(value: Any\) -> int \| None:\n"
    r".*?"
    r"    async def _handle_command\(",
    re.DOTALL,
)

replacement = '''    @staticmethod
    def _normalize_favorite_text(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).strip().casefold().split())

    async def _change_favorite(self, player: HeosPlayer, direction: int) -> None:
        heos = self._device.heos
        if not heos:
            raise HeosError("HEOS not connected")

        favorites = await heos.get_favorites()
        entries = self._favorite_entries(favorites)
        if not entries:
            raise HeosError("No HEOS favorites available")

        indices = [index for index, _ in entries]
        current_media = getattr(player, "now_playing_media", None)
        current_media_id = str(getattr(current_media, "media_id", "") or "")
        current_station = self._normalize_favorite_text(
            getattr(current_media, "station", None)
        )
        current_song = self._normalize_favorite_text(
            getattr(current_media, "song", None)
        )

        current_index: int | None = None

        # First prefer the exact HEOS media_id of the currently playing station.
        if current_media_id:
            for index, favorite in entries:
                favorite_media_id = str(getattr(favorite, "media_id", "") or "")
                if favorite_media_id and favorite_media_id == current_media_id:
                    current_index = index
                    break

        # HEOS devices can report a station name instead of the preset media_id.
        # Use the favorite name as a reliable fallback.
        if current_index is None and (current_station or current_song):
            for index, favorite in entries:
                favorite_name = self._normalize_favorite_text(
                    getattr(favorite, "name", None)
                )
                if favorite_name and favorite_name in {current_station, current_song}:
                    current_index = index
                    break

        # Keep continuity when the previous command selected a favorite but the
        # receiver has not reported the new now-playing metadata yet.
        if current_index is None and self._favorite_index in indices:
            current_index = self._favorite_index

        if current_index is None:
            target_pos = 0 if direction > 0 else len(indices) - 1
        else:
            target_pos = (indices.index(current_index) + direction) % len(indices)

        self._favorite_index = indices[target_pos]
        _LOG.debug(
            "[%s] Favorite navigation: current=%s target=%s direction=%s",
            self._player_id,
            current_index,
            self._favorite_index,
            direction,
        )
        await player.play_preset_station(self._favorite_index)

    async def _handle_command(
'''

new_text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit("Could not find the existing favorite-navigation block")

REMOTE.write_text(new_text, encoding="utf-8", newline="\n")

# Required invariants for the custom build.
result = REMOTE.read_text(encoding="utf-8")
for needle in (
    "_normalize_favorite_text",
    "current_media.media_id",
    "current_media, ",
    "play_preset_station",
):
    if needle not in result:
        raise SystemExit(f"Missing expected marker after patch: {needle}")

print(f"Updated favorite navigation in {REMOTE}")
