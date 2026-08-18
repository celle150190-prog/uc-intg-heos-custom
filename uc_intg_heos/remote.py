"""HEOS Remote entity with Denon AVR command mapping changes.

Base: mase1981/uc-intg-heos v2.1.2.
Only remote command/UI behavior is customized.
"""

import asyncio
import logging
import time
from typing import Any

from ucapi import remote, StatusCodes
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text
from pyheos import HeosError, HeosPlayer
from pyheos.types import PlayState, RepeatType
from ucapi_framework import RemoteEntity

from uc_intg_heos.config import HeosDeviceConfig
from uc_intg_heos.const import INPUT_COMMAND_MAP
from uc_intg_heos.device import HeosDevice

_LOG = logging.getLogger(__name__)

COMMAND_RATE_LIMIT = 0.5
DENON_TELNET_PORT = 23
DENON_COMMAND_TIMEOUT = 1.5


def _safe_cmd_name(name: str) -> str:
    return name.upper().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace(".", "")


class HeosRemote(RemoteEntity):
    """Remote entity for a HEOS player."""

    def __init__(
        self, device_config: HeosDeviceConfig, device: HeosDevice, player: HeosPlayer
    ) -> None:
        self._device = device
        self._player = player
        self._player_id = player.player_id
        self._is_avr = device.is_avr(player)
        self._last_cmd_time = 0.0
        self._cmd_lock = asyncio.Lock()
        self._favorite_indices: list[int] = []
        self._favorite_index: int | None = None

        entity_id = f"remote.{device_config.identifier}.{player.player_id}"
        simple_commands = self._build_commands(device)
        ui_pages = self._build_ui_pages(player.name, device)

        button_mapping = [
            create_btn_mapping(Buttons.PLAY, short="PLAY"),
            create_btn_mapping(Buttons.STOP, short="STOP"),
            create_btn_mapping(Buttons.PREV, short="PREVIOUS_FAVORITE"),
            create_btn_mapping(Buttons.NEXT, short="NEXT_FAVORITE"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
            create_btn_mapping(Buttons.CHANNEL_UP, short="SUBWOOFER_UP"),
            create_btn_mapping(Buttons.CHANNEL_DOWN, short="SUBWOOFER_DOWN"),
        ]

        super().__init__(
            entity_id,
            f"{player.name} Remote",
            [remote.Features.ON_OFF, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=simple_commands,
            button_mapping=button_mapping,
            ui_pages=ui_pages,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({remote.Attributes.STATE: remote.States.UNAVAILABLE})
            return
        self.update({remote.Attributes.STATE: remote.States.ON})

    def _build_commands(self, device: HeosDevice) -> list[str]:
        cmds = [
            "PLAY", "PAUSE", "STOP", "PLAY_PAUSE",
            "NEXT", "PREVIOUS",
            "PREVIOUS_FAVORITE", "NEXT_FAVORITE",
            "VOLUME_UP", "VOLUME_DOWN", "MUTE_TOGGLE",
            "SUBWOOFER_UP", "SUBWOOFER_DOWN",
            "ON", "OFF",
            "REPEAT_OFF", "REPEAT_ALL", "REPEAT_ONE",
            "SHUFFLE_ON", "SHUFFLE_OFF",
        ]
        cmds.extend(INPUT_COMMAND_MAP.keys())
        if len(device.players) > 1:
            cmds.append("GROUP_ALL_SPEAKERS")
        cmds.append("LEAVE_GROUP")
        for pid, p in device.players.items():
            if pid != self._player_id:
                cmds.append(f"GROUP_WITH_{_safe_cmd_name(p.name)}")
        return cmds

    def _build_ui_pages(self, player_name: str, device: HeosDevice) -> list[UiPage]:
        pages: list[UiPage] = []

        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))
        page1.add(create_ui_text("Power / Playback", 0, 0, Size(4, 1)))
        page1.add(create_ui_icon("uc:power", 0, 1, cmd="OFF" if self._is_avr else "STOP"))
        page1.add(create_ui_icon("uc:play", 1, 1, cmd="PLAY"))
        page1.add(create_ui_icon("uc:pause", 2, 1, cmd="PAUSE"))
        page1.add(create_ui_icon("uc:prev", 0, 2, cmd="PREVIOUS_FAVORITE"))
        page1.add(create_ui_icon("uc:next", 1, 2, cmd="NEXT_FAVORITE"))

        page1.add(create_ui_text("Volume", 0, 3, Size(4, 1)))
        page1.add(create_ui_icon("uc:up-arrow-bold", 0, 4, cmd="VOLUME_UP"))
        page1.add(create_ui_icon("uc:down-arrow-bold", 1, 4, cmd="VOLUME_DOWN"))
        page1.add(create_ui_icon("uc:mute", 2, 4, cmd="MUTE_TOGGLE"))
        if self._is_avr:
            page1.add(create_ui_text("Subwoofer", 0, 5, Size(2, 1)))
            page1.add(create_ui_text("CH +", 2, 5, cmd="SUBWOOFER_UP"))
            page1.add(create_ui_text("CH -", 3, 5, cmd="SUBWOOFER_DOWN"))
        pages.append(page1)

        page2 = UiPage("modes", f"{player_name} Modes", grid=Size(4, 6))
        page2.add(create_ui_text("Repeat", 0, 0, Size(4, 1)))
        page2.add(create_ui_text("Off", 0, 1, cmd="REPEAT_OFF"))
        page2.add(create_ui_text("All", 1, 1, cmd="REPEAT_ALL"))
        page2.add(create_ui_text("One", 2, 1, cmd="REPEAT_ONE"))
        page2.add(create_ui_text("Shuffle", 0, 2, Size(4, 1)))
        page2.add(create_ui_text("On", 0, 3, Size(2, 1), cmd="SHUFFLE_ON"))
        page2.add(create_ui_text("Off", 2, 3, Size(2, 1), cmd="SHUFFLE_OFF"))
        page2.add(create_ui_text("Inputs", 0, 4, Size(4, 1)))
        page2.add(create_ui_text("HDMI", 0, 5, Size(2, 1), cmd="INPUT_HDMI_ARC"))
        page2.add(create_ui_text("AUX", 2, 5, Size(2, 1), cmd="INPUT_AUX"))
        pages.append(page2)

        if len(device.players) > 1:
            page3 = UiPage("grouping", f"{player_name} Grouping", grid=Size(4, 6))
            page3.add(create_ui_text("Multi-Room", 0, 0, Size(4, 1)))
            page3.add(create_ui_text("Group All", 0, 1, Size(4, 1), cmd="GROUP_ALL_SPEAKERS"))
            row = 2
            for pid, p in device.players.items():
                if pid != self._player_id and row < 5:
                    cmd_name = f"GROUP_WITH_{_safe_cmd_name(p.name)}"
                    page3.add(create_ui_text(f"+ {p.name[:18]}", 0, row, Size(4, 1), cmd=cmd_name))
                    row += 1
            page3.add(create_ui_text("Ungroup", 0, row, Size(4, 1), cmd="LEAVE_GROUP"))
            pages.append(page3)
        return pages

    async def _send_denon(self, player: HeosPlayer, command: str) -> None:
        """Send a single Denon AVR telnet command without using the Denon integration."""
        if not self._is_avr:
            raise HeosError("Denon command requested for non-AVR player")
        writer = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(player.ip_address, DENON_TELNET_PORT),
                timeout=DENON_COMMAND_TIMEOUT,
            )
            writer.write((command + "\r").encode("ascii"))
            await asyncio.wait_for(writer.drain(), timeout=DENON_COMMAND_TIMEOUT)
            await asyncio.sleep(0.02)
        except Exception as err:
            raise HeosError(f"Denon command {command} failed: {err}") from err
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _send_denon_volume(self, player: HeosPlayer, direction: str) -> None:
        # Denon MVUP/MVDOWN is issued twice so one Remote button press equals 1 dB.
        command = "MVUP" if direction == "up" else "MVDOWN"
        await self._send_denon(player, command)
        await self._send_denon(player, command)

    async def _get_favorite_indices(self, refresh: bool = False) -> list[int]:
        heos = self._device.heos
        if not heos:
            raise HeosError("HEOS not connected")
        if refresh or not self._favorite_indices:
            favorites = await heos.get_favorites()
            self._favorite_indices = sorted(int(index) for index in favorites)
        return self._favorite_indices

    async def _change_favorite(self, player: HeosPlayer, direction: int) -> None:
        indices = await self._get_favorite_indices()
        if not indices:
            raise HeosError("No HEOS favorites available")

        if self._favorite_index not in indices:
            # Start at the first/last item depending on direction.
            self._favorite_index = indices[0] if direction > 0 else indices[-1]
        else:
            pos = indices.index(self._favorite_index)
            self._favorite_index = indices[(pos + direction) % len(indices)]

        await player.play_preset_station(self._favorite_index)

    async def _handle_command(
        self, entity: remote.RemoteEntity, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        async with self._cmd_lock:
            command = (params or {}).get("command", cmd_id)
            player = self._device.get_player(self._player_id)
            if not player:
                return StatusCodes.SERVICE_UNAVAILABLE

            now = time.monotonic()
            elapsed = now - self._last_cmd_time
            if elapsed < COMMAND_RATE_LIMIT:
                await asyncio.sleep(COMMAND_RATE_LIMIT - elapsed)
            self._last_cmd_time = time.monotonic()

            try:
                if command == "ON" and self._is_avr:
                    await self._send_denon(player, "PWON")
                elif command == "OFF" and self._is_avr:
                    await self._send_denon(player, "PWSTANDBY")
                elif command == "PLAY":
                    await player.play()
                elif command == "PAUSE":
                    await player.pause()
                elif command == "STOP":
                    if self._is_avr:
                        try:
                            await player.set_volume(0)
                            await asyncio.sleep(0.3)
                        except Exception:
                            pass
                    await player.stop()
                elif command == "PLAY_PAUSE":
                    if player.state == PlayState.PLAY:
                        await player.pause()
                    else:
                        await player.play()
                elif command in ("NEXT", "NEXT_FAVORITE"):
                    if self._is_avr and command == "NEXT_FAVORITE":
                        await self._change_favorite(player, +1)
                    else:
                        await player.play_next()
                elif command in ("PREVIOUS", "PREVIOUS_FAVORITE"):
                    if self._is_avr and command == "PREVIOUS_FAVORITE":
                        await self._change_favorite(player, -1)
                    else:
                        await player.play_previous()
                elif command == "VOLUME_UP":
                    if self._is_avr:
                        await self._send_denon_volume(player, "up")
                    else:
                        await player.volume_up(5)
                elif command == "VOLUME_DOWN":
                    if self._is_avr:
                        await self._send_denon_volume(player, "down")
                    else:
                        await player.volume_down(5)
                elif command == "SUBWOOFER_UP" and self._is_avr:
                    await self._send_denon(player, "CVSW UP")
                elif command == "SUBWOOFER_DOWN" and self._is_avr:
                    await self._send_denon(player, "CVSW DOWN")
                elif command == "MUTE_TOGGLE":
                    await player.toggle_mute()
                elif command == "REPEAT_OFF":
                    await player.set_play_mode(RepeatType.OFF, player.shuffle)
                elif command == "REPEAT_ALL":
                    await player.set_play_mode(RepeatType.ON_ALL, player.shuffle)
                elif command == "REPEAT_ONE":
                    await player.set_play_mode(RepeatType.ON_ONE, player.shuffle)
                elif command == "SHUFFLE_ON":
                    await player.set_play_mode(player.repeat, True)
                elif command == "SHUFFLE_OFF":
                    await player.set_play_mode(player.repeat, False)
                elif command in INPUT_COMMAND_MAP:
                    await player.play_input_source(INPUT_COMMAND_MAP[command])
                elif command == "GROUP_ALL_SPEAKERS":
                    await self._group_all(player)
                elif command == "LEAVE_GROUP":
                    await self._leave_group()
                elif command.startswith("GROUP_WITH_"):
                    await self._handle_group_with(command, player)
                else:
                    return StatusCodes.NOT_IMPLEMENTED
                return StatusCodes.OK
            except HeosError as err:
                _LOG.error("[%s] Remote command error %s: %s", entity.id, command, err)
                return StatusCodes.SERVER_ERROR
            except Exception as err:
                _LOG.error("[%s] Remote error %s: %s", entity.id, command, err)
                return StatusCodes.SERVER_ERROR

    async def _group_all(self, player: HeosPlayer) -> None:
        heos = self._device.heos
        if not heos:
            raise HeosError("HEOS not connected")
        all_ids = [self._player_id] + [pid for pid in self._device.players if pid != self._player_id]
        try:
            await self._execute_with_retry(lambda: heos.set_group(all_ids), "GROUP_ALL")
        except HeosError as err:
            _LOG.info("[%s] GROUP_ALL ignored (already grouped?): %s", self._player_id, err)

    async def _leave_group(self) -> None:
        heos = self._device.heos
        if not heos:
            raise HeosError("HEOS not connected")
        try:
            await self._execute_with_retry(lambda: heos.set_group([self._player_id]), "LEAVE_GROUP")
        except HeosError as err:
            _LOG.info("[%s] LEAVE_GROUP ignored (not in group?): %s", self._player_id, err)

    async def _handle_group_with(self, command: str, player: HeosPlayer) -> None:
        heos = self._device.heos
        if not heos:
            raise HeosError("HEOS not connected")
        target_name = command.replace("GROUP_WITH_", "")
        for pid, p in self._device.players.items():
            if _safe_cmd_name(p.name) == target_name:
                try:
                    await self._execute_with_retry(
                        lambda pid=pid: heos.set_group([self._player_id, pid]),
                        f"GROUP_WITH_{target_name}",
                    )
                except HeosError as err:
                    _LOG.info("[%s] GROUP_WITH_%s ignored: %s", self._player_id, target_name, err)
                return
        _LOG.warning("Group target not found: %s", target_name)

    async def _execute_with_retry(self, func, name: str, retries: int = 2) -> None:
        for attempt in range(retries):
            try:
                await func()
                return
            except HeosError as err:
                _LOG.warning(
                    "[%s] %s attempt %d/%d failed: %s",
                    self._player_id, name, attempt + 1, retries, err,
                )
                if "Processing previous command" in str(err) and attempt < retries - 1:
                    await asyncio.sleep(1.0)
                    continue
                raise


def create_remotes(device_config: HeosDeviceConfig, device: HeosDevice) -> list[HeosRemote]:
    return [HeosRemote(device_config, device, player) for player in device.players.values()]
