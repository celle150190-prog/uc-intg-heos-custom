from pathlib import Path

p = Path("upstream/uc_intg_heos/device.py")
s = p.read_text(encoding="utf-8")

def replace(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit("Device patch anchor not found")
    s = s.replace(old, new, 1)

replace(
'''import logging
import time
from typing import Any
''',
'''import asyncio
import logging
import time
from typing import Any
'''
)

replace(
'''        self._last_update_time: float = 0.0
''',
'''        self._last_update_time: float = 0.0
        self._favorite_cursor: dict[int, int] = {}
'''
)

replace(
'''        for player_id in self._players:
            self._source_lists[player_id] = list(base_sources)
''',
'''        for player_id, player in self._players.items():
            sources = list(base_sources)
            if self.is_avr(player) and "HEOS" not in sources:
                sources.append("HEOS")
            self._source_lists[player_id] = sources
'''
)

replace(
'''    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:
        for fav_idx, fav in self._favorites.items():
''',
'''    async def play_adjacent_favorite(self, player_id: int, direction: int) -> bool:
        if not self._heos:
            return False
        try:
            self._favorites = await self._heos.get_favorites()
            self._build_source_lists()
        except HeosError as err:
            _LOG.debug("[%s] Favorite refresh failed: %s", self.log_id, err)

        items = list(self._favorites.items())
        player = self._players.get(player_id)
        if not player or not items:
            return False

        current = player.now_playing_media
        current_id = getattr(current, "media_id", None) if current else None
        current_name = ((getattr(current, "station", None) or getattr(current, "song", None)) if current else None)

        current_index = None
        for idx, (_preset_id, favorite) in enumerate(items):
            if current_id and getattr(favorite, "media_id", None) == current_id:
                current_index = idx
                break
            if current_name and getattr(favorite, "name", None) == current_name:
                current_index = idx
                break

        if current_index is None:
            current_index = self._favorite_cursor.get(player_id, -1 if direction > 0 else 0)

        target_index = (current_index + direction) % len(items)
        preset_id = items[target_index][0]
        _LOG.info("[%s] Favorite navigation dir=%s preset=%s name=%s",
                  self.log_id, direction, preset_id, items[target_index][1].name)
        await player.play_preset_station(preset_id)
        self._favorite_cursor[player_id] = target_index
        return True

    async def send_denon_steps(self, player_id: int, command: str, count: int, delay: float = 0.12) -> bool:
        player = self._players.get(player_id)
        if not player or not self.is_avr(player):
            return False
        host = player.ip_address or self._device_config.host
        writer = None
        try:
            _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, 23), timeout=2.0)
            for _ in range(count):
                writer.write((command + "\r").encode("ascii"))
                await writer.drain()
                await asyncio.sleep(delay)
            _LOG.info("[%s] Denon command %s x%d sent to %s", self.log_id, command, count, host)
            return True
        except (OSError, asyncio.TimeoutError) as err:
            _LOG.error("[%s] Denon command %s failed: %s", self.log_id, command, err)
            return False
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def play_source_by_name(self, player_id: int, source_name: str) -> bool:
        if source_name == "HEOS":
            player = self._players.get(player_id)
            if not player or not self.is_avr(player):
                return False
            if not await self.send_denon_steps(player_id, "PWON", 1, 0.1):
                return False
            await asyncio.sleep(1.0)
            if not await self.send_denon_steps(player_id, "SINET", 1, 0.1):
                return False
            await asyncio.sleep(0.2)
            await player.play()
            return True

        for fav_idx, fav in self._favorites.items():
''')
replace(old, new)

p.write_text(s, encoding="utf-8")
compile(s, "device.py", "exec")
