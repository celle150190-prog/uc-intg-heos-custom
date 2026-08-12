from pathlib import Path
import ast

p = Path("uc_intg_heos/media_player.py")
s = p.read_text(encoding="utf-8")

old = '                case Commands.CHANNEL_UP:\n                    if not self._is_avr:\n                        return StatusCodes.NOT_IMPLEMENTED\n                    await self._send_denon_command("PSSWL UP")\n\n                case Commands.CHANNEL_DOWN:\n                    if not self._is_avr:\n                        return StatusCodes.NOT_IMPLEMENTED\n                    await self._send_denon_command("PSSWL DOWN")\n'
new = '                case Commands.CHANNEL_UP | "CHANNEL_UP" | "channel_up":\n                    if not self._is_avr:\n                        return StatusCodes.NOT_IMPLEMENTED\n                    await self._send_denon_command("PSSWL UP")\n\n                case Commands.CHANNEL_DOWN | "CHANNEL_DOWN" | "channel_down":\n                    if not self._is_avr:\n                        return StatusCodes.NOT_IMPLEMENTED\n                    await self._send_denon_command("PSSWL DOWN")\n'

if old not in s:
    raise SystemExit(
        "Existing CHANNEL_UP/CHANNEL_DOWN handlers were not found. "
        "No changes were made."
    )

s = s.replace(old, new, 1)

# POWER is handled by the Activity now and is therefore removed only
# from the custom media-player simple command list.
power_block = """                    "SUBWOOFER1_LEVEL_DOWN",
                    "POWER_OFF",
"""
replacement_block = """                    "SUBWOOFER1_LEVEL_DOWN",
"""
if power_block in s:
    s = s.replace(power_block, replacement_block, 1)

ast.parse(s)
p.write_text(s, encoding="utf-8")

print("patch_media_player_1.2.11.py: patch applied and Python syntax validated")
print("CH+ accepts CHANNEL_UP / channel_up")
print("CH- accepts CHANNEL_DOWN / channel_down")
print("POWER_OFF removed from custom media-player simple commands")
print("Existing volume/favorites/cover-art/browse-media code untouched")
