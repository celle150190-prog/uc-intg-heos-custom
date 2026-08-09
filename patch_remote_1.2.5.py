from pathlib import Path
import ast

p = Path("uc_intg_heos/remote.py")
s = p.read_text(encoding="utf-8")

old_buttons = '''        button_mapping = [
            create_btn_mapping(Buttons.PLAY, short="PLAY"),
            create_btn_mapping(Buttons.STOP, short="STOP"),
            create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            create_btn_mapping(Buttons.NEXT, short="NEXT"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
        ]
'''
new_buttons = '''        button_mapping = [
            create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
            create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            create_btn_mapping(Buttons.NEXT, short="NEXT"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
            create_btn_mapping(Buttons.CHANNEL_UP, short="SUBWOOFER1_LEVEL_UP"),
            create_btn_mapping(Buttons.CHANNEL_DOWN, short="SUBWOOFER1_LEVEL_DOWN"),
            create_btn_mapping(Buttons.POWER, short="POWER_OFF"),
        ]
'''
if old_buttons not in s:
    raise SystemExit("Original v2.1.2 button mapping not found")
s = s.replace(old_buttons, new_buttons, 1)

old_init = """        self._last_cmd_time = 0.0
        self._cmd_lock = asyncio.Lock()
"""
new_init = """        self._last_cmd_time = 0.0
        self._cmd_lock = asyncio.Lock()
        self._current_favorite_id: int | None = None
"""
if old_init not in s:
    raise SystemExit("Remote state initialization not found")
s = s.replace(old_init, new_init, 1)

start = s.index("    def _build_commands(self, device: HeosDevice) -> list[str]:")
end = s.index("    def _build_ui_pages(", start)
new_commands = '''    def _build_commands(self, device: HeosDevice) -> list[str]:
        cmds = [
            "PLAY_PAUSE",
            "NEXT",
            "PREVIOUS",
            "VOLUME_UP",
            "VOLUME_DOWN",
            "MUTE_TOGGLE",
        ]

        if self._is_avr:
            cmds.extend([
                "SUBWOOFER1_LEVEL_UP",
                "SUBWOOFER1_LEVEL_DOWN",
                "POWER_OFF",
            ])

        for favorite_id in device.favorites:
            cmds.append(f"FAVORITE_{favorite_id}")

        return cmds

'''
s = s[:start] + new_commands + s[end:]

start = s.index("    def _build_ui_pages(")
end = s.index("    async def _handle_command(", start)

new_ui = '''    def _build_ui_pages(self, player_name: str, device: HeosDevice) -> list[UiPage]:
        pages = []

        page1 = UiPage("playback", f"{player_name} HEOS", grid=Size(4, 6))
        page1.add(create_ui_text("HEOS", 0, 0, Size(4, 1)))

        # Previous / Play-Pause / Next
        page1.add(create_ui_icon("uc:prev", 0, 1, cmd="PREVIOUS"))
        page1.add(create_ui_icon("uc:play", 1, 1, cmd="PLAY_PAUSE"))
        page1.add(create_ui_icon("uc:next", 2, 1, cmd="NEXT"))

        # Volume- / Mute / Volume+
        page1.add(create_ui_icon("uc:down-arrow-bold", 0, 2, cmd="VOLUME_DOWN"))
        page1.add(create_ui_icon("uc:mute", 1, 2, cmd="MUTE_TOGGLE"))
        page1.add(create_ui_icon("uc:up-arrow-bold", 2, 2, cmd="VOLUME_UP"))
        pages.append(page1)

        # HEOS favorites only; no Denon input sources.
        favorites = list(device.favorites.items())
        page_size = 20
        for page_number, offset in enumerate(range(0, len(favorites), page_size), start=1):
            chunk = favorites[offset:offset + page_size]
            page_id = "favorites" if page_number == 1 else f"favorites_{page_number}"
            title = "Favoriten" if page_number == 1 else f"Favoriten {page_number}"
            page = UiPage(page_id, f"{player_name} {title}", grid=Size(4, 6))
            page.add(create_ui_text("Favoriten", 0, 0, Size(4, 1)))
            for index, (favorite_id, favorite) in enumerate(chunk):
                row = index // 4 + 1
                col = index % 4
                label = str(favorite.name)[:20]
                page.add(create_ui_text(label, col, row, Size(1, 1), cmd=f"FAVORITE_{favorite_id}"))
            pages.append(page)

        return pages

'''
s = s[:start] + new_ui + s[end:]

marker = "    async def _handle_command(\n"
favorite_helper = """    async def _play_favorite_relative(
        self, player: HeosPlayer, direction: int
    ) -> None:
        'Play the next/previous HEOS favorite instead of a track.'
        favorites = list(self._device.favorites.items())
        if not favorites:
            raise HeosError("No HEOS favorites available")

        favorite_ids = [favorite_id for favorite_id, _ in favorites]

        if self._current_favorite_id in favorite_ids:
            current_index = favorite_ids.index(self._current_favorite_id)
        else:
            current_index = None
            media = getattr(player, "now_playing_media", None)
            station = getattr(media, "station", None)
            song = getattr(media, "song", None)
            current_values = {str(station or ""), str(song or "")}

            for index, (_, favorite) in enumerate(favorites):
                favorite_name = str(getattr(favorite, "name", ""))
                if favorite_name and favorite_name in current_values:
                    current_index = index
                    break

            if current_index is None:
                current_index = 0 if direction > 0 else len(favorites) - 1

        next_index = (current_index + direction) % len(favorites)
        favorite_id = favorite_ids[next_index]

        await player.play_preset_station(favorite_id)
        self._current_favorite_id = favorite_id

"""
helper = '''    async def _change_volume_1db(self, player: HeosPlayer, delta: int) -> None:
        """Change HEOS volume by exactly one dB."""
        current_volume = getattr(player, "volume", None)
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

'''
if marker not in s:
    raise SystemExit("Command handler marker not found")
s = s.replace(marker, favorite_helper + helper + marker, 1)

needle_next_previous = """                    case "NEXT":
                        await player.play_next()
                    case "PREVIOUS":
                        await player.play_previous()
"""
replacement_next_previous = """                    case "NEXT":
                        await self._play_favorite_relative(player, +1)
                    case "PREVIOUS":
                        await self._play_favorite_relative(player, -1)
"""
needle_volume = '''                    case "VOLUME_UP":
                        await player.volume_up(5)
                    case "VOLUME_DOWN":
                        await player.volume_down(5)
'''
replacement_volume = '''                    case "VOLUME_UP":
                        await self._change_volume_1db(player, +1)
                    case "VOLUME_DOWN":
                        await self._change_volume_1db(player, -1)
'''
if needle_volume not in s:
    raise SystemExit("5 dB volume handler not found in upstream remote.py")
s = s.replace(needle_volume, replacement_volume, 1)

needle = '''                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case "REPEAT_OFF":
'''
replacement = '''                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case "SUBWOOFER1_LEVEL_UP":
                        if not self._is_avr:
                            return StatusCodes.NOT_IMPLEMENTED
                        await self._send_denon_command("PSSWL UP")
                    case "SUBWOOFER1_LEVEL_DOWN":
                        if not self._is_avr:
                            return StatusCodes.NOT_IMPLEMENTED
                        await self._send_denon_command("PSSWL DOWN")
                    case "POWER_OFF":
                        if not self._is_avr:
                            return StatusCodes.NOT_IMPLEMENTED
                        await self._send_denon_command("PWSTANDBY")
                    case cmd if cmd.startswith("FAVORITE_"):
                        try:
                            favorite_id = int(cmd.split("_", 1)[1])
                        except ValueError:
                            return StatusCodes.BAD_REQUEST
                        if favorite_id not in self._device.favorites:
                            return StatusCodes.BAD_REQUEST
                        await player.play_preset_station(favorite_id)
                        self._current_favorite_id = favorite_id
                    case "REPEAT_OFF":
'''
if needle_next_previous not in s:
    raise SystemExit("Original NEXT/PREVIOUS handler not found")
s = s.replace(needle_next_previous, replacement_next_previous, 1)

if needle not in s:
    raise SystemExit("Original command handler insertion point not found")
s = s.replace(needle, replacement, 1)

ast.parse(s)
p.write_text(s, encoding="utf-8")
print("patch_remote_1.2.2.py: patch applied and Python syntax validated")
