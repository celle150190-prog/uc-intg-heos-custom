from pathlib import Path
import ast

p = Path("uc_intg_heos/media_player.py")
s = p.read_text(encoding="utf-8")

old_features = """FEATURES = [
    Features.ON_OFF,
    Features.PLAY_PAUSE,
    Features.STOP,
    Features.NEXT,
    Features.PREVIOUS,
    Features.VOLUME,
    Features.VOLUME_UP_DOWN,
    Features.MUTE_TOGGLE,
    Features.MUTE,
    Features.UNMUTE,
    Features.REPEAT,
    Features.SHUFFLE,
    Features.SELECT_SOURCE,
    Features.MEDIA_DURATION,
    Features.MEDIA_POSITION,
    Features.MEDIA_TITLE,
    Features.MEDIA_ARTIST,
    Features.MEDIA_ALBUM,
    Features.MEDIA_IMAGE_URL,
    Features.MEDIA_TYPE,
    Features.BROWSE_MEDIA,
    Features.PLAY_MEDIA,
]
"""
new_features = """FEATURES = [
    Features.ON_OFF,
    Features.PLAY_PAUSE,
    Features.STOP,
    Features.NEXT,
    Features.PREVIOUS,
    Features.VOLUME,
    Features.VOLUME_UP_DOWN,
    Features.MUTE_TOGGLE,
    Features.MUTE,
    Features.UNMUTE,
    Features.REPEAT,
    Features.SHUFFLE,
    Features.SELECT_SOURCE,
    Features.MEDIA_DURATION,
    Features.MEDIA_POSITION,
    Features.MEDIA_TITLE,
    Features.MEDIA_ARTIST,
    Features.MEDIA_ALBUM,
    Features.MEDIA_IMAGE_URL,
    Features.MEDIA_TYPE,
    Features.BROWSE_MEDIA,
    Features.PLAY_MEDIA,
    Features.CHANNEL_SWITCHER,
]
"""
if old_features not in s:
    raise SystemExit("Original FEATURES block not found")
s = s.replace(old_features, new_features, 1)

old_constructor = """            {
                Attributes.STATE: States.UNKNOWN,
                Attributes.VOLUME: 0,
                Attributes.MUTED: False,
                Attributes.MEDIA_DURATION: 0,
                Attributes.MEDIA_POSITION: 0,
                Attributes.MEDIA_TITLE: "",
                Attributes.MEDIA_ARTIST: "",
                Attributes.MEDIA_ALBUM: "",
                Attributes.MEDIA_IMAGE_URL: "",
                Attributes.SOURCE: "",
                Attributes.SOURCE_LIST: [],
                Attributes.REPEAT: RepeatMode.OFF,
                Attributes.SHUFFLE: False,
            },
            device_class=dev_class,
            cmd_handler=self._handle_command,
"""
new_constructor = """            {
                Attributes.STATE: States.UNKNOWN,
                Attributes.VOLUME: 0,
                Attributes.MUTED: False,
                Attributes.MEDIA_DURATION: 0,
                Attributes.MEDIA_POSITION: 0,
                Attributes.MEDIA_TITLE: "",
                Attributes.MEDIA_ARTIST: "",
                Attributes.MEDIA_ALBUM: "",
                Attributes.MEDIA_IMAGE_URL: "",
                Attributes.SOURCE: "",
                Attributes.SOURCE_LIST: [],
            },
            device_class=dev_class,
            options={
                "simple_commands": [
                    "SUBWOOFER1_LEVEL_UP",
                    "SUBWOOFER1_LEVEL_DOWN",
                    "POWER_OFF",
                ],
                "volume_steps": 100,
            },
            cmd_handler=self._handle_command,
"""
if old_constructor not in s:
    raise SystemExit("Media Player constructor block not found")
s = s.replace(old_constructor, new_constructor, 1)

old_init = """        self._device = device
        self._player = player
        self._player_id = player.player_id
"""
new_init = """        self._device = device
        self._player = player
        self._player_id = player.player_id
        self._current_favorite_id: int | None = None
        self._favorites_refresh_at = 0.0
"""
if old_init not in s:
    raise SystemExit("Media player initialization block not found")
s = s.replace(old_init, new_init, 1)

anchor = "    async def sync_state(self) -> None:\n"
helpers = r"""    async def _refresh_favorites_if_due(self) -> None:
        # Refresh HEOS account favorites without reconnecting.
        now = asyncio.get_running_loop().time()
        if now < self._favorites_refresh_at:
            return

        heos = self._device.heos
        if not heos:
            return

        try:
            try:
                favorites = await heos.get_favorites(refresh=True)
            except TypeError:
                favorites = await heos.get_favorites()
        except HeosError as err:
            _LOG.debug(
                "[%s] Favorite refresh failed: %s",
                self._player_id,
                err,
            )
            self._favorites_refresh_at = now + 10.0
            return

        self._device._favorites = favorites
        self._device._build_source_lists()
        self._favorites_refresh_at = now + 10.0

    def _match_current_favorite(self, player: HeosPlayer):
        now = player.now_playing_media
        if not now:
            return None

        candidates = {
            str(now.station or "").strip().casefold(),
            str(now.song or "").strip().casefold(),
        }
        candidates.discard("")

        for favorite_id, favorite in self._device.favorites.items():
            name = str(favorite.name or "").strip().casefold()
            if name and any(
                name == value or name in value or value in name
                for value in candidates
            ):
                return favorite_id, favorite

        return None

    async def _play_favorite_relative(
        self, player: HeosPlayer, direction: int
    ) -> None:
        await self._refresh_favorites_if_due()

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

    async def _change_volume_1step(
        self, player: HeosPlayer, delta: int
    ) -> None:
        current_volume = player.volume
        if current_volume is None:
            raise HeosError("Current HEOS volume is unavailable")

        new_volume = max(0, min(100, int(current_volume) + delta))
        await player.set_volume(new_volume)

    async def _send_denon_command(self, command: str) -> None:
        avr_ip = getattr(self._player, "ip_address", None)
        if not avr_ip:
            raise HeosError("HEOS AVR player has no IP address")

        writer = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(avr_ip, 23),
                timeout=2.0,
            )
            writer.write((command + chr(13)).encode("ascii"))
            await writer.drain()
            _LOG.debug(
                "[%s] Denon TCP command sent to %s: %s",
                self._player_id,
                avr_ip,
                command,
            )
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

"""
if anchor not in s:
    raise SystemExit("sync_state anchor not found")
s = s.replace(anchor, helpers + anchor, 1)

old_source = "        attrs[Attributes.SOURCE_LIST] = self._device.get_source_list(self._player_id)\n"
new_source = """        await self._refresh_favorites_if_due()
        attrs[Attributes.SOURCE_LIST] = [
            favorite.name for favorite in self._device.favorites.values()
        ]
"""
if old_source not in s:
    raise SystemExit("SOURCE_LIST assignment not found")
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
            attrs[Attributes.MEDIA_IMAGE_URL] = (
                now.image_url or favorite_image
            )
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
    raise SystemExit("NEXT/PREVIOUS handlers not found")
s = s.replace(old_np, new_np, 1)

old_volume = """                case Commands.VOLUME_UP:
                    await player.volume_up(params.get("step", 5))

                case Commands.VOLUME_DOWN:
                    await player.volume_down(params.get("step", 5))
"""
new_volume = """                case Commands.VOLUME_UP:
                    await self._change_volume_1step(player, +1)

                case Commands.VOLUME_DOWN:
                    await self._change_volume_1step(player, -1)
"""
if old_volume not in s:
    raise SystemExit("Volume handlers not found")
s = s.replace(old_volume, new_volume, 1)

old_off = """                case Commands.OFF:
                    if self._is_avr:
                        try:
                            await player.set_volume(0)
                            await asyncio.sleep(0.3)
                            await player.stop()
                        except Exception:
                            await player.stop()
                    else:
                        await player.stop()
"""
new_off = """                case Commands.OFF:
                    if self._is_avr:
                        await self._send_denon_command("PWSTANDBY")
                    else:
                        await player.stop()
"""
if old_off not in s:
    raise SystemExit("OFF handler not found")
s = s.replace(old_off, new_off, 1)

needle_channel = """                case Commands.MUTE_TOGGLE:
                    await player.toggle_mute()
"""
replacement_channel = """                case Commands.MUTE_TOGGLE:
                    await player.toggle_mute()

                case Commands.CHANNEL_UP:
                    if not self._is_avr:
                        return StatusCodes.NOT_IMPLEMENTED
                    await self._send_denon_command("PSSWL UP")

                case Commands.CHANNEL_DOWN:
                    if not self._is_avr:
                        return StatusCodes.NOT_IMPLEMENTED
                    await self._send_denon_command("PSSWL DOWN")
"""
if needle_channel not in s:
    raise SystemExit("MUTE handler insertion point not found")
s = s.replace(needle_channel, replacement_channel, 1)

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

                    await self._refresh_favorites_if_due()
                    favorite_id = next(
                        (
                            favorite_id
                            for favorite_id, favorite in self._device.favorites.items()
                            if favorite.name == source
                        ),
                        None,
                    )
                    if favorite_id is None:
                        _LOG.warning("HEOS favorite not found: %s", source)
                        return StatusCodes.BAD_REQUEST

                    await player.play_preset_station(favorite_id)
                    self._current_favorite_id = favorite_id
"""
if old_select not in s:
    raise SystemExit("SELECT_SOURCE handler not found")
s = s.replace(old_select, new_select, 1)

# ---------------------------------------------------------------------------
# 7. Make Browse Media open the live HEOS favorites directly.
#    The original HEOS 2.1.2 browse() implementation is retained; only its
#    root routing is changed. Favorites are refreshed before opening Browse.
# ---------------------------------------------------------------------------
old_browse = """            if not media_id or media_id == \"root\":
                raw_items = await self._device.browse_root()
            elif media_id == \"favorites\":
                raw_items = await self._device.browse_favorites()
"""
new_browse = """            if not media_id or media_id == \"root\":
                await self._refresh_favorites_if_due()
                raw_items = await self._device.browse_favorites()
            elif media_id == \"favorites\":
                await self._refresh_favorites_if_due()
                raw_items = await self._device.browse_favorites()
"""
if old_browse not in s:
    raise SystemExit("Original browse root block not found")
s = s.replace(old_browse, new_browse, 1)

ast.parse(s)
p.write_text(s, encoding="utf-8")
print("patch_media_player_1.2.9.py: patch applied and Python syntax validated")
