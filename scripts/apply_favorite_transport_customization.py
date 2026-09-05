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
        raise RuntimeError(f"Expected exactly one Favorite-UI anchor in {path}, found {count}.")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_device(path: Path) -> None:
    replace_once(
        path,
        '''        self._last_update_time: float = 0.0
''',
        '''        self._last_update_time: float = 0.0
        # Remember a favorite selected through this integration. This is
        # only a fallback; normal navigation resolves the current HEOS item.
        self._last_favorite_index: dict[int, int] = {}
''',
    )
    replace_once(
        path,
        '''    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:
''',
        '''    @staticmethod
    def _favorite_identity(value: str | None) -> str:
        return " ".join(value.casefold().split()) if value else ""

    async def _play_favorite(self, player_id: int, favorite_index: int) -> bool:
        player = self._players.get(player_id)
        if not player or favorite_index not in self._favorites:
            return False
        await player.play_preset_station(favorite_index)
        self._last_favorite_index[player_id] = favorite_index
        return True

    async def play_adjacent_favorite(self, player_id: int, direction: int) -> bool:
        """Play the favorite immediately before or after the current favorite."""
        player = self._players.get(player_id)
        ordered_favorites = sorted(self._favorites.items())
        if not player or not ordered_favorites or direction not in {-1, 1}:
            return False

        now = player.now_playing_media
        current_values = {
            self._favorite_identity(value)
            for value in (now.station, now.song, now.media_id, now.album_id)
            if self._favorite_identity(value)
        }
        current_position = next(
            (
                position
                for position, (_, favorite) in enumerate(ordered_favorites)
                if current_values.intersection(
                    {
                        self._favorite_identity(value)
                        for value in (favorite.name, favorite.media_id, favorite.album_id)
                        if self._favorite_identity(value)
                    }
                )
            ),
            None,
        )
        if current_position is None:
            current_position = next(
                (
                    position
                    for position, (favorite_index, _) in enumerate(ordered_favorites)
                    if favorite_index == self._last_favorite_index.get(player_id)
                ),
                None,
            )
        if current_position is None:
            _LOG.info("[%s] Favorite navigation ignored: current item is not a HEOS favorite", self.log_id)
            return False

        next_position = (current_position + direction) % len(ordered_favorites)
        return await self._play_favorite(player_id, ordered_favorites[next_position][0])

    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:
''',
    )
    replace_once(
        path,
        '''                if player:
                    await player.play_preset_station(fav_idx)
                    return True
''',
        '''                if await self._play_favorite(player_id, fav_idx):
                    return True
''',
    )
    replace_once(
        path,
        '''        if media_id.startswith("favorite_"):
            idx = int(media_id.split("_", 1)[1])
            await player.play_preset_station(idx)
            return True
''',
        '''        if media_id.startswith("favorite_"):
            idx = int(media_id.split("_", 1)[1])
            return await self._play_favorite(player_id, idx)
''',
    )


def patch_remote(path: Path) -> None:
    replace_once(
        path,
        '''        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))
''',
        '''        if self._is_avr:
            favorite_page = UiPage("favorites", f"{player_name} Favorites", grid=Size(6, 2))
            favorite_page.add(create_ui_icon("uc:prev", 0, 0, Size(2, 2), cmd="FAVORITE_PREVIOUS"))
            favorite_page.add(create_ui_icon("uc:play", 2, 0, Size(2, 2), cmd="PLAY_PAUSE"))
            favorite_page.add(create_ui_icon("uc:next", 4, 0, Size(2, 2), cmd="FAVORITE_NEXT"))
            pages.append(favorite_page)

        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))
''',
    )
    replace_once(
        path,
        '''                    "SUBWOOFER_1_LEVEL_DOWN",
                ]
''',
        '''                    "SUBWOOFER_1_LEVEL_DOWN",
                    "FAVORITE_PREVIOUS",
                    "FAVORITE_NEXT",
                ]
''',
    )
    replace_once(
        path,
        '''                    case "NEXT":
                        await player.play_next()
                    case "PREVIOUS":
                        await player.play_previous()
''',
        '''                    case "NEXT":
                        await player.play_next()
                    case "PREVIOUS":
                        await player.play_previous()
                    case "FAVORITE_NEXT":
                        if not await self._device.play_adjacent_favorite(self._player_id, 1):
                            return StatusCodes.BAD_REQUEST
                    case "FAVORITE_PREVIOUS":
                        if not await self._device.play_adjacent_favorite(self._player_id, -1):
                            return StatusCodes.BAD_REQUEST
''',
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
