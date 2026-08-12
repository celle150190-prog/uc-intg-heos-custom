from pathlib import Path
import ast

DRIVER = Path("uc_intg_heos/driver.py")
BUTTON_MODULE = Path("uc_intg_heos/browse_button.py")

button_module = '"""HEOS Browse/Favorites activity button."""\n\nimport logging\nfrom typing import Any\n\nfrom ucapi import StatusCodes\nfrom ucapi.button import Button, Commands\nfrom uc_intg_heos.config import HeosDeviceConfig\nfrom uc_intg_heos.device import HeosDevice\n\n_LOG = logging.getLogger(__name__)\n\n\nclass HeosFavoritesButton(Button):\n    """Button used by an Activity to expose HEOS Favorites."""\n\n    def __init__(\n        self,\n        device_config: HeosDeviceConfig,\n        device: HeosDevice,\n        player_id: int,\n    ) -> None:\n        self._device = device\n        self._player_id = player_id\n        entity_id = (\n            f"button.{device_config.identifier}."\n            f"{player_id}.heos_favorites"\n        )\n        super().__init__(\n            entity_id,\n            "HEOS Favoriten",\n            description="HEOS Favoriten / Browse",\n            cmd_handler=self._handle_command,\n        )\n\n    async def _handle_command(\n        self,\n        entity: Button,\n        cmd_id: str,\n        params: dict[str, Any] | None,\n        websocket: Any | None = None,\n    ) -> StatusCodes:\n        if cmd_id != Commands.PUSH:\n            return StatusCodes.NOT_IMPLEMENTED\n\n        _LOG.info(\n            "[%s] HEOS Favorites Activity button pressed "\n            "(player_id=%s)",\n            self._device.log_id,\n            self._player_id,\n        )\n\n        # Refresh the HEOS account favorites now. This gives us a useful,\n        # observable test and keeps the button tied to the current HEOS list.\n        if self._device.heos is not None:\n            try:\n                try:\n                    favorites = await self._device.heos.get_favorites(\n                        refresh=True\n                    )\n                except TypeError:\n                    favorites = await self._device.heos.get_favorites()\n\n                self._device._favorites = favorites\n                self._device._build_source_lists()\n\n                _LOG.info(\n                    "[%s] HEOS favorites refreshed: %d item(s)",\n                    self._device.log_id,\n                    len(favorites),\n                )\n            except Exception as err:\n                _LOG.warning(\n                    "[%s] HEOS favorites refresh failed: %s",\n                    self._device.log_id,\n                    err,\n                )\n                return StatusCodes.SERVER_ERROR\n\n        return StatusCodes.OK\n\n\ndef create_browse_buttons(\n    device_config: HeosDeviceConfig,\n    device: HeosDevice,\n) -> list[HeosFavoritesButton]:\n    """Create one HEOS Favorites button per discovered AVR player."""\n    return [\n        HeosFavoritesButton(device_config, device, player.player_id)\n        for player in device.players.values()\n        if device.is_avr(player)\n    ]\n'
BUTTON_MODULE.write_text(button_module, encoding="utf-8")

driver = DRIVER.read_text(encoding="utf-8")

needle_import = "from uc_intg_heos.select import create_selects\n"
replacement_import = (
    "from uc_intg_heos.select import create_selects\n"
    "from uc_intg_heos.browse_button import create_browse_buttons\n"
)
if needle_import not in driver:
    raise SystemExit("driver.py select import not found")
driver = driver.replace(needle_import, replacement_import, 1)

needle_entities = "                lambda cfg, dev: create_selects(cfg, dev),\n"
replacement_entities = (
    "                lambda cfg, dev: create_selects(cfg, dev),\n"
    "                lambda cfg, dev: create_browse_buttons(cfg, dev),\n"
)
if needle_entities not in driver:
    raise SystemExit("driver.py entity class list insertion point not found")
driver = driver.replace(needle_entities, replacement_entities, 1)

ast.parse(driver)
ast.parse(button_module)
DRIVER.write_text(driver, encoding="utf-8")

print("patch_browse_button_1.2.10.py: driver and button module validated")
