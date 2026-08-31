#!/usr/bin/env python3
"""Apply the Custom Denon AVR Remote 3 patch to a pristine upstream tree.

The updater intentionally uses exact, single-match source anchors. A changed
upstream implementation therefore fails safely instead of silently publishing
an incomplete custom integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CUSTOM_REPOSITORY = "https://github.com/celle150190-prog/uc-intg-heos-custom"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one customization anchor in {path}, found {count}."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_device(path: Path) -> None:
    replace_once(path, "import logging\n", "import asyncio\nimport logging\n")
    replace_once(
        path,
        "_LOG = logging.getLogger(__name__)\n\n\nclass HeosDevice",
        "_LOG = logging.getLogger(__name__)\n\n"
        "AVR_CONTROL_PORT = 23\n"
        "AVR_CONTROL_TIMEOUT = 3.0\n\n\n"
        "class HeosDevice",
    )
    replace_once(
        path,
        "    def is_avr(self, player: HeosPlayer) -> bool:\n"
        "        model_lower = player.model.lower()\n"
        "        return any(kw in model_lower for kw in AVR_KEYWORDS)\n",
        "    def is_avr(self, player: HeosPlayer) -> bool:\n"
        "        model_lower = player.model.lower()\n"
        "        return any(kw in model_lower for kw in AVR_KEYWORDS)\n\n"
        "    async def send_avr_command(self, command: str) -> None:\n"
        "        \"\"\"Send a Denon/Marantz IP-control command to the AVR Telnet port.\"\"\"\n"
        "        writer: asyncio.StreamWriter | None = None\n"
        "        try:\n"
        "            _, writer = await asyncio.wait_for(\n"
        "                asyncio.open_connection(self.address, AVR_CONTROL_PORT),\n"
        "                timeout=AVR_CONTROL_TIMEOUT,\n"
        "            )\n"
        "            writer.write(f\"{command}\\r\".encode(\"ascii\"))\n"
        "            await asyncio.wait_for(writer.drain(), timeout=AVR_CONTROL_TIMEOUT)\n"
        "        finally:\n"
        "            if writer is not None:\n"
        "                writer.close()\n"
        "                try:\n"
        "                    await writer.wait_closed()\n"
        "                except (ConnectionError, OSError):\n"
        "                    pass\n\n"
        "    async def toggle_avr_power(self) -> None:\n"
        "        \"\"\"Toggle the AVR between on and standby using its actual power state.\"\"\"\n"
        "        writer: asyncio.StreamWriter | None = None\n"
        "        try:\n"
        "            reader, writer = await asyncio.wait_for(\n"
        "                asyncio.open_connection(self.address, AVR_CONTROL_PORT),\n"
        "                timeout=AVR_CONTROL_TIMEOUT,\n"
        "            )\n"
        "            writer.write(b\"PW?\\r\")\n"
        "            await asyncio.wait_for(writer.drain(), timeout=AVR_CONTROL_TIMEOUT)\n"
        "            response = await asyncio.wait_for(\n"
        "                reader.readuntil(b\"\\r\"), timeout=AVR_CONTROL_TIMEOUT\n"
        "            )\n"
        "            power_state = response.decode(\"ascii\", errors=\"replace\").strip().upper()\n"
        "            if power_state == \"PWON\":\n"
        "                command = \"PWSTANDBY\"\n"
        "            elif power_state in {\"PWSTANDBY\", \"PWOFF\"}:\n"
        "                command = \"PWON\"\n"
        "            else:\n"
        "                raise RuntimeError(f\"Unexpected AVR power response: {power_state!r}\")\n"
        "            writer.write(f\"{command}\\r\".encode(\"ascii\"))\n"
        "            await asyncio.wait_for(writer.drain(), timeout=AVR_CONTROL_TIMEOUT)\n"
        "        finally:\n"
        "            if writer is not None:\n"
        "                writer.close()\n"
        "                try:\n"
        "                    await writer.wait_closed()\n"
        "                except (ConnectionError, OSError):\n"
        "                    pass\n",
    )


def patch_remote(path: Path) -> None:
    replace_once(
        path,
        "        button_mapping = [\n"
        "            create_btn_mapping(Buttons.PLAY, short=\"PLAY\"),\n"
        "            create_btn_mapping(Buttons.STOP, short=\"STOP\"),\n"
        "            create_btn_mapping(Buttons.PREV, short=\"PREVIOUS\"),\n"
        "            create_btn_mapping(Buttons.NEXT, short=\"NEXT\"),\n"
        "            create_btn_mapping(Buttons.VOLUME_UP, short=\"VOLUME_UP\"),\n"
        "            create_btn_mapping(Buttons.VOLUME_DOWN, short=\"VOLUME_DOWN\"),\n"
        "            create_btn_mapping(Buttons.MUTE, short=\"MUTE_TOGGLE\"),\n"
        "        ]\n",
        "        button_mapping = [\n"
        "            create_btn_mapping(Buttons.PLAY, short=\"PLAY\"),\n"
        "            create_btn_mapping(Buttons.STOP, short=\"STOP\"),\n"
        "            create_btn_mapping(Buttons.PREV, short=\"PREVIOUS\"),\n"
        "            create_btn_mapping(Buttons.NEXT, short=\"NEXT\"),\n"
        "            # Remote 3 physical + and - buttons.\n"
        "            create_btn_mapping(Buttons.VOLUME_UP, short=\"VOLUME_UP\"),\n"
        "            create_btn_mapping(Buttons.VOLUME_DOWN, short=\"VOLUME_DOWN\"),\n"
        "            create_btn_mapping(Buttons.MUTE, short=\"MUTE_TOGGLE\"),\n"
        "        ]\n"
        "        if self._is_avr:\n"
        "            button_mapping.extend(\n"
        "                [\n"
        "                    create_btn_mapping(Buttons.POWER, short=\"POWER_TOGGLE\"),\n"
        "                    create_btn_mapping(\n"
        "                        Buttons.CHANNEL_UP, short=\"SUBWOOFER_1_LEVEL_UP\"\n"
        "                    ),\n"
        "                    create_btn_mapping(\n"
        "                        Buttons.CHANNEL_DOWN, short=\"SUBWOOFER_1_LEVEL_DOWN\"\n"
        "                    ),\n"
        "                ]\n"
        "            )\n",
    )
    replace_once(
        path,
        "        ]\n        cmds.extend(INPUT_COMMAND_MAP.keys())\n",
        "        ]\n"
        "        if self._is_avr:\n"
        "            cmds.extend(\n"
        "                [\n"
        "                    \"POWER_TOGGLE\",\n"
        "                    \"SUBWOOFER_1_LEVEL_UP\",\n"
        "                    \"SUBWOOFER_1_LEVEL_DOWN\",\n"
        "                ]\n"
        "            )\n"
        "        cmds.extend(INPUT_COMMAND_MAP.keys())\n",
    )
    replace_once(
        path,
        "        page1.add(create_ui_text(\"Volume\", 0, 3, Size(4, 1)))\n"
        "        page1.add(create_ui_icon(\"uc:up-arrow-bold\", 0, 4, cmd=\"VOLUME_UP\"))\n"
        "        page1.add(create_ui_icon(\"uc:down-arrow-bold\", 1, 4, cmd=\"VOLUME_DOWN\"))\n"
        "        page1.add(create_ui_icon(\"uc:mute\", 2, 4, cmd=\"MUTE_TOGGLE\"))\n",
        "        if self._is_avr:\n"
        "            page1.add(create_ui_text(\"Master Volume (1 dB)\", 0, 3, Size(4, 1)))\n"
        "            page1.add(create_ui_text(\"+1 dB\", 0, 4, Size(2, 1), cmd=\"VOLUME_UP\"))\n"
        "            page1.add(create_ui_text(\"-1 dB\", 2, 4, Size(2, 1), cmd=\"VOLUME_DOWN\"))\n"
        "            page1.add(create_ui_text(\"Subwoofer 1 +\", 0, 5, Size(2, 1), cmd=\"SUBWOOFER_1_LEVEL_UP\"))\n"
        "            page1.add(create_ui_text(\"Subwoofer 1 -\", 2, 5, Size(2, 1), cmd=\"SUBWOOFER_1_LEVEL_DOWN\"))\n"
        "        else:\n"
        "            page1.add(create_ui_text(\"Volume\", 0, 3, Size(4, 1)))\n"
        "            page1.add(create_ui_icon(\"uc:up-arrow-bold\", 0, 4, cmd=\"VOLUME_UP\"))\n"
        "            page1.add(create_ui_icon(\"uc:down-arrow-bold\", 1, 4, cmd=\"VOLUME_DOWN\"))\n"
        "            page1.add(create_ui_icon(\"uc:mute\", 2, 4, cmd=\"MUTE_TOGGLE\"))\n",
    )
    replace_once(
        path,
        "                    case \"VOLUME_UP\":\n"
        "                        await player.volume_up(5)\n"
        "                    case \"VOLUME_DOWN\":\n"
        "                        await player.volume_down(5)\n"
        "                    case \"MUTE_TOGGLE\":\n",
        "                    case \"VOLUME_UP\":\n"
        "                        await player.volume_up(1 if self._is_avr else 5)\n"
        "                    case \"VOLUME_DOWN\":\n"
        "                        await player.volume_down(1 if self._is_avr else 5)\n"
        "                    case \"POWER_TOGGLE\":\n"
        "                        await self._device.toggle_avr_power()\n"
        "                    case \"SUBWOOFER_1_LEVEL_UP\":\n"
        "                        await self._device.send_avr_command(\"PSSWL UP\")\n"
        "                    case \"SUBWOOFER_1_LEVEL_DOWN\":\n"
        "                        await self._device.send_avr_command(\"PSSWL DOWN\")\n"
        "                    case \"MUTE_TOGGLE\":\n",
    )


def patch_media_player(path: Path) -> None:
    replace_once(
        path,
        "                case Commands.VOLUME_UP:\n"
        "                    await player.volume_up(params.get(\"step\", 5))\n\n"
        "                case Commands.VOLUME_DOWN:\n"
        "                    await player.volume_down(params.get(\"step\", 5))\n",
        "                case Commands.VOLUME_UP:\n"
        "                    await player.volume_up(1 if self._is_avr else params.get(\"step\", 5))\n\n"
        "                case Commands.VOLUME_DOWN:\n"
        "                    await player.volume_down(1 if self._is_avr else params.get(\"step\", 5))\n",
    )


def patch_driver(path: Path, upstream_version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = upstream_version.removeprefix("v")
    data["version"] = f"{version}-custom.1"
    data.setdefault("name", {})["en"] = "HEOS Integration (Custom Denon AVR)"
    data.setdefault("description", {})["en"] = (
        "HEOS integration with custom Denon AVR controls: 1 dB master-volume "
        "steps and Subwoofer 1 controls on Remote 3."
    )
    data["home_page"] = CUSTOM_REPOSITORY
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path, help="Pristine upstream repository root")
    parser.add_argument("--upstream-version", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    patch_device(repo / "uc_intg_heos" / "device.py")
    patch_remote(repo / "uc_intg_heos" / "remote.py")
    patch_media_player(repo / "uc_intg_heos" / "media_player.py")
    patch_driver(repo / "driver.json", args.upstream_version)


if __name__ == "__main__":
    main()
