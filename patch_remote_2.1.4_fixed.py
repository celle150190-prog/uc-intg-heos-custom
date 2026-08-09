from pathlib import Path

p = Path("uc_intg_heos/remote.py")
s = p.read_text(encoding="utf-8")

# We patch the ORIGINAL v2.1.2 remote.py directly.
# The previous patch expected an already-customized file, which is why the
# GitHub Action reported "Command list not found".

# 1) Imports: add HTTP support for the Denon AVR.
s = s.replace(
    "import asyncio\nimport logging\nimport time\nfrom typing import Any\n",
    "import asyncio\nimport logging\nimport time\nimport urllib.parse\nimport urllib.request\nfrom typing import Any\n",
    1,
)

# 2) Physical Remote 3 button mapping.
old_buttons = """        button_mapping = [
            create_btn_mapping(Buttons.PLAY, short="PLAY"),
            create_btn_mapping(Buttons.STOP, short="STOP"),
            create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            create_btn_mapping(Buttons.NEXT, short="NEXT"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
        ]
"""
new_buttons = """        button_mapping = [
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
"""
if old_buttons not in s:
    raise SystemExit("Original v2.1.2 button mapping not found")
s = s.replace(old_buttons, new_buttons, 1)

# 3) Replace the original command/UI section completely.
start = s.index("    def _build_commands(self, device: HeosDevice) -> list[str]:")
end = s.index("    async def _handle_command(", start)

new_ui = """    def _build_commands(self, device: HeosDevice) -> list[str]:
        cmds = [
            "PLAY_PAUSE",
            "NEXT",
            "PREVIOUS",
            "VOLUME_UP",
            "VOLUME_DOWN",
            "MUTE_TOGGLE",
            "SUBWOOFER1_LEVEL_UP",
            "SUBWOOFER1_LEVEL_DOWN",
            "POWER_OFF",
        ]

        # HEOS favorites are loaded dynamically by HeosDevice.
        for favorite_id in device.favorites:
            cmds.append(f"FAVORITE_{favorite_id}")

        return cmds

    def _build_ui_pages(self, player_name: str, device: HeosDevice) -> list[UiPage]:
        pages = []

        # Page 1: playback/volume only.
        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))
        page1.add(create_ui_text("HEOS", 0, 0, Size(4, 1)))
        page1.add(create_ui_icon("uc:prev", 0, 1, cmd="PREVIOUS"))
        page1.add(create_ui_icon("uc:play", 1, 1, cmd="PLAY_PAUSE"))
        page1.add(create_ui_icon("uc:next", 2, 1, cmd="NEXT"))
        page1.add(create_ui_icon("uc:up-arrow-bold", 0, 2, cmd="VOLUME_UP"))
        page1.add(create_ui_icon("uc:down-arrow-bold", 1, 2, cmd="VOLUME_DOWN"))
        page1.add(create_ui_icon("uc:mute", 2, 2, cmd="MUTE_TOGGLE"))
        pages.append(page1)

        # Page 2+: HEOS favorites only.
        favorites = list(device.favorites.items())
        page_size = 20

        for page_number, offset in enumerate(range(0, len(favorites), page_size), start=1):
            chunk = favorites[offset:offset + page_size]
            page_id = "favorites" if page_number == 1 else f"favorites_{page_number}"
            title = "Sender" if page_number == 1 else f"Sender {page_number}"

            page = UiPage(page_id, f"{player_name} {title}", grid=Size(4, 6))
            page.add(create_ui_text("HEOS Sender", 0, 0, Size(4, 1)))

            for index, (favorite_id, favorite) in enumerate(chunk):
                row = index // 4 + 1
                col = index % 4
                label = str(favorite.name)[:20]
                page.add(
                    create_ui_text(
                        label,
                        col,
                        row,
                        Size(1, 1),
                        cmd=f"FAVORITE_{favorite_id}",
                    )
                )

            pages.append(page)

        return pages

"""

s = s[:start] + new_ui + s[end:]

# 4) Add Denon command helper before _handle_command.
marker = "    async def _handle_command(\n"
helper = """    async def _send_denon_command(self, player: HeosPlayer, command: str) -> None:
        \"\"\"Send a direct command to the Denon AVR over HTTP.\"\"\"
        avr_ip = getattr(player, "ip_address", None)
        if not avr_ip:
            raise HeosError("HEOS player has no IP address")

        encoded = urllib.parse.quote(command + "\\r", safe="")
        url = (
            f"http://{avr_ip}:8080/goform/"
            f"formiPhoneAppDirect.xml?{encoded}"
        )

        def _request() -> None:
            with urllib.request.urlopen(url, timeout=2) as response:
                response.read(64)

        await asyncio.to_thread(_request)
        _LOG.debug("[%s] Denon command sent: %s", self._player_id, command)

"""
if marker not in s:
    raise SystemExit("Command handler marker not found")
s = s.replace(marker, helper + marker, 1)

# 5) Insert our new commands into the original match statement.
old_cases = """                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case "REPEAT_OFF":
"""
new_cases = """                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case "POWER_OFF":
                        await self._send_denon_command(player, "PWSTANDBY")
                    case "SUBWOOFER1_LEVEL_UP":
                        await self._send_denon_command(player, "CVSW1 UP")
                    case "SUBWOOFER1_LEVEL_DOWN":
                        await self._send_denon_command(player, "CVSW1 DOWN")
                    case cmd if cmd.startswith("FAVORITE_"):
                        try:
                            favorite_id = int(cmd.split("_", 1)[1])
                        except ValueError:
                            return StatusCodes.BAD_REQUEST
                        if favorite_id not in self._device.favorites:
                            return StatusCodes.BAD_REQUEST
                        await player.play_preset_station(favorite_id)
                    case "REPEAT_OFF":
"""
if old_cases not in s:
    raise SystemExit("Original MUTE_TOGGLE handler not found")
s = s.replace(old_cases, new_cases, 1)

p.write_text(s, encoding="utf-8")
