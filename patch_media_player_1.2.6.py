from pathlib import Path
import ast

p = Path("uc_intg_heos/media_player.py")
s = p.read_text(encoding="utf-8")

old_init = """        self._device = device
        self._player = player
        self._player_id = player.player_id
"""
new_init = """        self._device = device
        self._player = player
        self._player_id = player.player_id
        self._current_favorite_id: int | None = None
"""
if old_init not in s:
    raise SystemExit("Media player initialization block not found")
s = s.replace(old_init, new_init, 1)

anchor = "    async def sync_state(self) -> None:\n"
helper = """    def _match_current_favorite(self, player: HeosPlayer):
        """ + repr("Return the favorite matching the current station/title, if any.") + """
        now = player.now_playing_media
        if not now:
            return None

        candidates = [
            str(now.station or "").strip(),
            str(now.song or "").strip(),
        ]
        candidates = [value.casefold() for value in candidates if value]

        for favorite_id, favorite in self._device.favorites.items():
            name = str(favorite.name or "").strip().casefold()
            if not name:
                continue
            if any(name == value or name in value or value in name for value in candidates):
                return favorite_id, favorite

        return None

    async def _play_favorite_relative(self, player: HeosPlayer, direction: int) -> None:
        """ + repr("Play the next/previous HEOS favorite.") + """
        favorites = list(self._device.favorites.items())
        if not favorites:
            raise HeosError("No HEOS favorites available")

        favorite_ids = [favorite_id for favorite_id, _ in favorites]
        if self._current_favorite_id in favorite_ids:
            current_index = favorite_ids.index(self._current_favorite_id)
        else:
            matched = self._match_current_favorite(player)
            if matched:
                self._current_favorite_id = matched[0]
                current_index = favorite_ids.index(matched[0])
            else:
                current_index = 0 if direction > 0 else len(favorites) - 1

        next_index = (current_index + direction) % len(favorites)
        favorite_id = favorite_ids[next_index]
        await player.play_preset_station(favorite_id)
        self._current_favorite_id = favorite_id

"""
if anchor not in s:
    raise SystemExit("sync_state anchor not found")
s = s.replace(anchor, helper + anchor, 1)

old_source = "        attrs[Attributes.SOURCE_LIST] = self._device.get_source_list(self._player_id)\n"
new_source = "        attrs[Attributes.SOURCE_LIST] = [favorite.name for favorite in self._device.favorites.values()]\n"
if old_source not in s:
    raise SystemExit("Source list assignment not found")
s = s.replace(old_source, new_source, 1)

old_image = """            attrs[Attributes.MEDIA_IMAGE_URL] = now.image_url or ""
            attrs[Attributes.MEDIA_DURATION] = now.duration or 0
"""
new_image = """            matched_favorite = self._match_current_favorite(player)
            if matched_favorite:
                self._current_favorite_id = matched_favorite[0]

            favorite_image = (
                matched_favorite[1].image_url
                if matched_favorite and matched_favorite[1].image_url
                else ""
            )
            attrs[Attributes.MEDIA_IMAGE_URL] = now.image_url or favorite_image
            attrs[Attributes.MEDIA_DURATION] = now.duration or 0
"""
if old_image not in s:
    raise SystemExit("Media image assignment not found")
s = s.replace(old_image, new_image, 1)

old_np = """                case Commands.NEXT:
                    await player.play_next()

                case Commands.PREVIOUS:
                    await player.play_previous()
"""
new_np = """                case Commands.NEXT:
                    await self._play_favorite_relative(player, +1)

                case Commands.PREVIOUS:
                    await self._play_favorite_relative(player, -1)
"""
if old_np not in s:
    raise SystemExit("Media NEXT/PREVIOUS handlers not found")
s = s.replace(old_np, new_np, 1)

old_select = """                case Commands.SELECT_SOURCE:
                    source = params.get("source", "")
                    if not source:
                        return StatusCodes.BAD_REQUEST
                    found = await self._device.play_source_by_name(self._player_id, source)
                    if not found:
                        _LOG.warning("Source not found: %s", source)
                        return StatusCodes.BAD_REQUEST
"""
new_select = """                case Commands.SELECT_SOURCE:
                    source = params.get("source", "")
                    if not source:
                        return StatusCodes.BAD_REQUEST
                                        favorite_id = None
                    for candidate_id, favorite in self._device.favorites.items():
                        if favorite.name == source:
                            favorite_id = candidate_id
                            break
                    found = await self._device.play_source_by_name(self._player_id, source)
                    if not found:
                        _LOG.warning("Source not found: %s", source)
                        return StatusCodes.BAD_REQUEST
                    if favorite_id is not None:
                        self._current_favorite_id = favorite_id
"""
if old_select not in s:
    raise SystemExit("SELECT_SOURCE handler not found")
s = s.replace(old_select, new_select, 1)

ast.parse(s)
p.write_text(s, encoding="utf-8")
print("patch_media_player_1.2.6.py erstellt und syntaktisch validiert.")
