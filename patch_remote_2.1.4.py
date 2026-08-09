from pathlib import Path

p = Path("uc_intg_heos/remote.py")
s = p.read_text(encoding="utf-8")

# Imports
s = s.replace(
    "import time\nfrom typing import Any\n",
    "import time\nimport asyncio\nimport urllib.parse\nimport urllib.request\nfrom typing import Any\n",
    1,
)

# Remote 3 physical button mapping
start = s.index("        button_mapping = [")
end = s.index("        super().__init__(", start)
button_mapping = """        button_mapping = [
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
s = s[:start] + button_mapping + s[end:]

# Command list
old = """            "VOLUME_UP",
            "VOLUME_DOWN",
            "MUTE_TOGGLE",
        ]
"""
new = """            "VOLUME_UP",
            "VOLUME_DOWN",
            "MUTE_TOGGLE",
            "SUBWOOFER1_LEVEL_UP",
            "SUBWOOFER1_LEVEL_DOWN",
            "POWER_OFF",
        ]
"""
if old not in s:
    raise SystemExit("Command list not found")
s = s.replace(old, new, 1)

# Custom command handler
old = """                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case cmd if cmd.startswith("FAVORITE_"):
"""
new = """                    case "MUTE_TOGGLE":
                        await player.toggle_mute()
                    case "POWER_OFF":
                        await self._send_denon_command(player, "PWSTANDBY")
                    case "SUBWOOFER1_LEVEL_UP":
                        await self._send_denon_command(player, "CVSW1 UP")
                    case "SUBWOOFER1_LEVEL_DOWN":
                        await self._send_denon_command(player, "CVSW1 DOWN")
                    case cmd if cmd.startswith("FAVORITE_"):
"""
if old not in s:
    raise SystemExit("Handler insertion point not found")
s = s.replace(old, new, 1)

# Direct Denon HTTP helper
marker = "    async def _handle_command(\n"
helper = """    async def _send_denon_command(self, player: HeosPlayer, command: str) -> None:
        # Denon X4400H-class receivers accept direct commands on HTTP port 8080.
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
    raise SystemExit("Handler marker not found")
s = s.replace(marker, helper + marker, 1)

p.write_text(s, encoding="utf-8")
ast.parse(s)
