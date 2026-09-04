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
CUSTOM_PACKAGE_REVISION = "24"
CUSTOM_DRIVER_ID_PREFIX = "heos_c"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one customization anchor in {path}, found {count}."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_device(path: Path) -> None:
    replace_once(
        path,
        "import logging\n",
        "import asyncio\nimport logging\n\nimport denonavr\n",
    )
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
        "    async def _get_denon_receiver(self) -> denonavr.DenonAVR:\n"
        "        \"\"\"Create the official Denon controller on first power action.\"\"\"\n"
        "        async with self._denon_power_lock:\n"
        "            if self._denon_receiver is None:\n"
        "                self._denon_receiver = denonavr.DenonAVR(\n"
        "                    host=self.address, timeout=AVR_CONTROL_TIMEOUT\n"
        "                )\n"
        "            return self._denon_receiver\n\n"
        "    async def power_on_avr(self) -> None:\n"
        "        \"\"\"Power on through the same Denon library command as the Denon integration.\"\"\"\n"
        "        receiver = await self._get_denon_receiver()\n"
        "        _LOG.info(\"[%s] Media/Remote UI: Denon power on\", self.log_id)\n"
        "        await receiver.async_power_on()\n\n"
        "    async def power_off_avr(self) -> None:\n"
        "        \"\"\"Power off through the same Denon library command as the Denon integration.\"\"\"\n"
        "        receiver = await self._get_denon_receiver()\n"
        "        _LOG.info(\"[%s] Media/Remote UI: Denon power off\", self.log_id)\n"
        "        await receiver.async_power_off()\n\n"
        "    async def toggle_avr_power(self) -> None:\n"
        "        \"\"\"Use the official Denon Integration toggle semantics for Main Zone power.\"\"\"\n"
        "        receiver = await self._get_denon_receiver()\n"
        "        # Match the Denon integration: its remote UI calls power_off when\n"
        "        # the controller reports ON, otherwise it calls power_on. Refresh\n"
        "        # this lightweight controller first because this driver keeps HEOS\n"
        "        # Media UI as its primary UI and has no Denon polling loop.\n"
        "        await receiver.async_update()\n"
        "        if receiver.power == \"ON\":\n"
        "            await self.power_off_avr()\n"
        "        else:\n"
        "            await self.power_on_avr()\n",
    )

    replace_once(
        path,
        "        self._last_update_time: float = 0.0\n",
        "        self._last_update_time: float = 0.0\n"
        "        # Dedicated controller for Media/Remote UI power only. It is not\n"
        "        # used for HEOS playback, metadata, volume or subwoofer controls.\n"
        "        self._denon_receiver: denonavr.DenonAVR | None = None\n"
        "        self._denon_power_lock = asyncio.Lock()\n",
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
        "                    create_btn_mapping(\n"
        "                        Buttons.POWER,\n"
        "                        short=remote.create_send_cmd(\"POWER_TOGGLE\"),\n"
        "                    ),\n"
        "                    create_btn_mapping(\n"
        "                        Buttons.CHANNEL_UP,\n"
        "                        short=remote.create_send_cmd(\"SUBWOOFER_1_LEVEL_UP\"),\n"
        "                    ),\n"
        "                    create_btn_mapping(\n"
        "                        Buttons.CHANNEL_DOWN,\n"
        "                        short=remote.create_send_cmd(\"SUBWOOFER_1_LEVEL_DOWN\"),\n"
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
        "                        await self._device.send_avr_command(\"PSSWL ON\")\n"
        "                        await self._device.send_avr_command(\"PSSWL UP\")\n"
        "                    case \"SUBWOOFER_1_LEVEL_DOWN\":\n"
        "                        await self._device.send_avr_command(\"PSSWL ON\")\n"
        "                        await self._device.send_avr_command(\"PSSWL DOWN\")\n"
        "                    case \"MUTE_TOGGLE\":\n",
    )

    replace_once(
        path,
        "            player = self._device.get_player(self._player_id)\n"
        "            if not player:\n"
        "                return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "            now = time.monotonic()\n",
        "            player = self._device.get_player(self._player_id)\n"
        "            # Power is provided by the dedicated Denon controller and\n"
        "            # remains usable when HEOS has disconnected in standby.\n"
        "            if not player and command != \"POWER_TOGGLE\":\n"
        "                return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "            now = time.monotonic()\n",
    )

def patch_media_player(path: Path) -> None:
    replace_once(
        path,
        "        if self._device.state == \"UNAVAILABLE\":\n"
        "            self.update({Attributes.STATE: States.UNAVAILABLE})\n"
        "            return\n\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        if not player:\n"
        "            self.update({Attributes.STATE: States.UNAVAILABLE})\n"
        "            return\n",
        "        if self._device.state == \"UNAVAILABLE\":\n"
        "            # HEOS disconnects while a Denon AVR is in standby. Keep the\n"
        "            # Media UI active so Remote 3 can still deliver a power command.\n"
        "            state = States.STANDBY if self._is_avr else States.UNAVAILABLE\n"
        "            self.update({Attributes.STATE: state})\n"
        "            return\n\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        if not player:\n"
        "            state = States.STANDBY if self._is_avr else States.UNAVAILABLE\n"
        "            self.update({Attributes.STATE: state})\n"
        "            return\n",
    )
    replace_once(
        path,
        "        params = params or {}\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        if not player:\n"
        "            return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "        try:\n",
        "        params = params or {}\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        if not player:\n"
        "            return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "        try:\n",
    )
    replace_once(
        path,
        "        params = params or {}\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        if not player:\n"
        "            return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "        try:\n",
        "        params = params or {}\n"
        "        player = self._device.get_player(self._player_id)\n"
        "        avr_power_command = self._is_avr and cmd_id in (\n"
        "            Commands.ON, Commands.OFF, Commands.TOGGLE\n"
        "        )\n"
        "        if not player and not avr_power_command:\n"
        "            return StatusCodes.SERVICE_UNAVAILABLE\n\n"
        "        try:\n",
    )
    replace_once(
        path,
        "        entity_id = f\"media_player.{device_config.identifier}.{player.player_id}\"\n\n"
        "        super().__init__(\n"
        "            entity_id,\n"
        "            player.name,\n"
        "            FEATURES,\n",
        "        entity_id = f\"media_player.{device_config.identifier}.{player.player_id}\"\n\n"
        "        features = FEATURES.copy()\n"
        "        if self._is_avr:\n"
        "            features.append(Features.CHANNEL_SWITCHER)\n"
        "            features.append(Features.TOGGLE)\n\n"
        "        super().__init__(\n"
        "            entity_id,\n"
        "            player.name,\n"
        "            features,\n",
    )
    replace_once(
        path,
        "                case Commands.ON:\n"
        "                    await player.play()\n\n"
        "                case Commands.OFF:\n"
        "                    if self._is_avr:\n"
        "                        try:\n"
        "                            await player.set_volume(0)\n"
        "                            await asyncio.sleep(0.3)\n"
        "                            await player.stop()\n"
        "                        except Exception:\n"
        "                            await player.stop()\n"
        "                    else:\n"
        "                        await player.stop()\n\n"
        "                case Commands.PLAY_PAUSE:\n",
        "                case Commands.ON:\n"
        "                    if self._is_avr:\n"
        "                        await self._device.power_on_avr()\n"
        "                    else:\n"
        "                        await player.play()\n\n"
        "                case Commands.OFF:\n"
        "                    if self._is_avr:\n"
        "                        # Remote 3's physical power key dispatches OFF in\n"
        "                        # Media UI even while the AVR is already in standby.\n"
        "                        # Route it through the Denon Remote-UI toggle path.\n"
        "                        await self._device.toggle_avr_power()\n"
        "                    else:\n"
        "                        await player.stop()\n\n"
        "                case Commands.TOGGLE:\n"
        "                    if not self._is_avr:\n"
        "                        return StatusCodes.NOT_IMPLEMENTED\n"
        "                    await self._device.toggle_avr_power()\n\n"
        "                case Commands.PLAY_PAUSE:\n",
    )
    replace_once(
        path,
        "                case Commands.VOLUME_UP:\n"
        "                    await player.volume_up(params.get(\"step\", 5))\n\n"
        "                case Commands.VOLUME_DOWN:\n"
        "                    await player.volume_down(params.get(\"step\", 5))\n",
        "                case Commands.VOLUME_UP:\n"
        "                    if self._is_avr:\n"
        "                        # MV is the Denon Main Zone command. Each command is\n"
        "                        # 0.5 dB, so send it twice for the requested 1 dB step.\n"
        "                        await self._device.send_avr_command(\"MVUP\")\n"
        "                        await self._device.send_avr_command(\"MVUP\")\n"
        "                    else:\n"
        "                        await player.volume_up(params.get(\"step\", 5))\n\n"
        "                case Commands.VOLUME_DOWN:\n"
        "                    if self._is_avr:\n"
        "                        # MVDOWN operates Main Zone, not Zone 2 or Zone 3.\n"
        "                        await self._device.send_avr_command(\"MVDOWN\")\n"
        "                        await self._device.send_avr_command(\"MVDOWN\")\n"
        "                    else:\n"
        "                        await player.volume_down(params.get(\"step\", 5))\n\n"
        "                case Commands.CHANNEL_UP:\n"
        "                    if not self._is_avr:\n"
        "                        return StatusCodes.NOT_IMPLEMENTED\n"
        "                    await self._device.send_avr_command(\"PSSWL ON\")\n"
        "                    await self._device.send_avr_command(\"PSSWL UP\")\n\n"
        "                case Commands.CHANNEL_DOWN:\n"
        "                    if not self._is_avr:\n"
        "                        return StatusCodes.NOT_IMPLEMENTED\n"
        "                    await self._device.send_avr_command(\"PSSWL ON\")\n"
        "                    await self._device.send_avr_command(\"PSSWL DOWN\")\n",
    )


def patch_requirements(path: Path) -> None:
    """Bundle the same pinned Denon controller used by the Denon integration."""
    replace_once(
        path,
        "pyheos>=1.0.5\n",
        "pyheos>=1.0.5\n"
        "denonavr @ git+https://github.com/henrikwidlund/denonavr.git@"
        "ecf8021049b37ceb9d9c640dea1199d088f27cc7\n",
    )

def patch_driver(path: Path, upstream_version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = upstream_version.removeprefix("v")
    # Every package gets a compact, version-specific ID so it can be installed
    # as a separate custom integration instead of updating an earlier package.
    compact_version = version.replace(".", "")
    data["driver_id"] = (
        f"{CUSTOM_DRIVER_ID_PREFIX}{compact_version}_{CUSTOM_PACKAGE_REVISION}"
    )
    data["version"] = f"{version}-custom.{CUSTOM_PACKAGE_REVISION}"
    data.setdefault("name", {})["en"] = "HEOS Integration (Custom Denon AVR Standalone)"
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
    patch_requirements(repo / "requirements.txt")
    patch_driver(repo / "driver.json", args.upstream_version)


if __name__ == "__main__":
    main()

