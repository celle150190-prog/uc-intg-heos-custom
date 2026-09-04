#!/usr/bin/env python3
"""Add visual Favorite transport controls after the stable custom.24 patch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CUSTOM_PACKAGE_REVISION = "25"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one Favorite-UI anchor in {path}, found {count}."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_device(path: Path) -> None:
    replace_once(
        path,
        "        self._last_update_time: float = 0.0\n",
        "        self._last_update_time: float = 0.0\n"
        "        # Remember a favorite selected through this integration. This is\n"
        "        # only a fallback; normal navigation resolves the current HEOS item.\n"
        "        self._last_favorite_index: dict[int, int] = {}\n",
    )
    replace_once(
        path,
        "    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:\n",
        "    @staticmethod\n"
        "    def _favorite_identity(value: str | None) -> str:\n"
        "        return " ".join(value.casefold().split()) if value else ""\n\n"
        "    async def _play_favorite(self, player_id: int, favorite_index: int) -> bool:\n"
        "        player = self._players.get(player_id)\n"
        "        if not player or favorite_index not in self._favorites:\n"
        "            return False\n"
        "        await player.play_preset_station(favorite_index)\n"
        "        self._last_favorite_index[player_id] = favorite_index\n"
        "        return True\n\n"
        "    async def play_adjacent_favorite(self, player_id: int, direction: int) -> bool:\n"
        "        """Play the favorite immediately before or after the current favorite."""\n"
        "        player = self._players.get(player_id)\n"
        "        ordered_favorites = sorted(self._favorites.items())\n"
        "        if not player or not ordered_favorites or direction not in {-1, 1}:\n"
        "            return False\n\n"
        "        now = player.now_playing_media\n"
        "        current_values = {\n"
        "            self._favorite_identity(value)\n"
        "            for value in (now.station, now.song, now.media_id, now.album_id)\n"
        "            if self._favorite_identity(value)\n"
        "        }\n"
        "        current_position = next(\n"
        "            (\n"
        "                position\n"
        "                for position, (_, favorite) in enumerate(ordered_favorites)\n"
        "                if current_values.intersection(\n"
        "                    {\n"
        "                        self._favorite_identity(value)\n"
        "                        for value in (favorite.name, favorite.media_id, favorite.album_id)\n"
        "                        if self._favorite_identity(value)\n"
        "                    }\n"
        "                )\n"
        "            ),\n"
        "            None,\n"
        "        )\n"
        "        if current_position is None:\n"
        "            current_position = next(\n"
        "                (\n"
        "                    position\n"
        "                    for position, (favorite_index, _) in enumerate(ordered_favorites)\n"
        "                    if favorite_index == self._last_favorite_index.get(player_id)\n"
        "                ),\n"
        "                None,\n"
        "            )\n"
        "        if current_position is None:\n"
        "            _LOG.info("[%s] Favorite navigation ignored: current item is not a HEOS favorite", self.log_id)\n"
        "            return False\n\n"
        "        next_position = (current_position + direction) % len(ordered_favorites)\n"
        "        return await self._play_favorite(player_id, ordered_favorites[next_position][0])\n\n"
        "    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:\n",
    )
    replace_once(
        path,
        "                if player:\n"
        "                    await player.play_preset_station(fav_idx)\n"
        "                    return True\n",
        "                if await self._play_favorite(player_id, fav_idx):\n"
        "                    return True\n",
    )
    replace_once(
        path,
        "        if media_id.startswith("favorite_"):\n"
        "            idx = int(media_id.split("_", 1)[1])\n"
        "            await player.play_preset_station(idx)\n"
        "            return True\n",
        "        if media_id.startswith("favorite_"):\n"
        "            idx = int(media_id.split("_", 1)[1])\n"
        "            return await self._play_favorite(player_id, idx)\n",
    )


def patch_remote(path: Path) -> None:
    replace_once(
        path,
        "        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))\n",
        "        if self._is_avr:\n"
        "            favorite_page = UiPage("favorites", f"{player_name} Favorites", grid=Size(6, 2))\n"
        "            # The Remote renders these as three large symbol buttons.\n"
        "            favorite_page.add(create_ui_icon("uc:prev", 0, 0, Size(2, 2), cmd="FAVORITE_PREVIOUS"))\n"
        "            favorite_page.add(create_ui_icon("uc:play", 2, 0, Size(2, 2), cmd="PLAY_PAUSE"))\n"
        "            favorite_page.add(create_ui_icon("uc:next", 4, 0, Size(2, 2), cmd="FAVORITE_NEXT"))\n"
        "            pages.append(favorite_page)\n\n"
        "        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))\n",
    )
    replace_once(
        path,
        "                    "SUBWOOFER_1_LEVEL_DOWN",\n"
        "                ]\n",
        "                    "SUBWOOFER_1_LEVEL_DOWN",\n"
        "                    "FAVORITE_PREVIOUS",\n"
        "                    "FAVORITE_NEXT",\n"
        "                ]\n",
    )
    replace_once(
        path,
        "                    case "NEXT":\n"
        "                        await player.play_next()\n"
        "                    case "PREVIOUS":\n"
        "                        await player.play_previous()\n",
        "                    case "NEXT":\n"
        "                        await player.play_next()\n"
        "                    case "PREVIOUS":\n"
        "                        await player.play_previous()\n"
        "                    case "FAVORITE_NEXT":\n"
        "                        if not await self._device.play_adjacent_favorite(self._player_id, 1):\n"
        "                            return StatusCodes.BAD_REQUEST\n"
        "                    case "FAVORITE_PREVIOUS":\n"
        "                        if not await self._device.play_adjacent_favorite(self._player_id, -1):\n"
        "                            return StatusCodes.BAD_REQUEST\n",
    )


def patch_driver(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = str(data["version"]).split("-custom.", maxsplit=1)[0]
    data["driver_id"] = f"heos_c{version.replace('.', '')}_{CUSTOM_PACKAGE_REVISION}"
    data["version"] = f"{version}-custom.{CUSTOM_PACKAGE_REVISION}"
    data.setdefault("description", {})["en"] = (
        "HEOS integration with Custom Denon AVR controls, 1 dB master volume, "
        "Subwoofer 1 controls, and visual favorite-station transport."
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path, help="Already customized source root")
    args = parser.parse_args()
    repo = args.repo.resolve()
    patch_device(repo / "uc_intg_heos" / "device.py")
    patch_remote(repo / "uc_intg_heos" / "remote.py")
    patch_driver(repo / "driver.json")


if __name__ == "__main__":
    main()
