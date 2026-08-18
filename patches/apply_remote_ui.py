from pathlib import Path

p = Path("upstream/uc_intg_heos/remote.py")
s = p.read_text(encoding="utf-8")

def replace(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit("Remote patch anchor not found")
    s = s.replace(old, new, 1)

old = '''            create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            create_btn_mapping(Buttons.NEXT, short="NEXT"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
        ]
'''
new = '''            create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
            create_btn_mapping(Buttons.NEXT, short="NEXT"),
            create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
            create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
            create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
        ]
        if self._is_avr:
            channel_up = getattr(Buttons, "CHANNEL_UP", None)
            channel_down = getattr(Buttons, "CHANNEL_DOWN", None)
            if channel_up is not None:
                button_mapping.append(create_btn_mapping(channel_up, short="SUB1_UP"))
            if channel_down is not None:
                button_mapping.append(create_btn_mapping(channel_down, short="SUB1_DOWN"))
'''
replace(old, new)

old = '''            "SHUFFLE_ON", "SHUFFLE_OFF",
        ]
'''
new = '''            "SHUFFLE_ON", "SHUFFLE_OFF",
        ]
        if self._is_avr:
            cmds.extend(["SUB1_UP", "SUB1_DOWN"])
'''
replace(old, new)

replace(
'''        page1.add(create_ui_text("Playback", 0, 0, Size(4, 1)))
''',
'''        page1.add(create_ui_text("Favorites", 0, 0, Size(4, 1)))
'''
)

replace(
'''        page1.add(create_ui_icon("uc:mute", 2, 4, cmd="MUTE_TOGGLE"))
        pages.append(page1)
''',
'''        page1.add(create_ui_icon("uc:mute", 2, 4, cmd="MUTE_TOGGLE"))
        if self._is_avr:
            page1.add(create_ui_text("Subwoofer 1", 0, 5, Size(4, 1)))
            page1.add(create_ui_text("-", 0, 5, Size(2, 1), cmd="SUB1_DOWN"))
            page1.add(create_ui_text("+", 2, 5, Size(2, 1), cmd="SUB1_UP"))
        pages.append(page1)
'''
)

old = '''                    case "NEXT":
                        await player.play_next()
                    case "PREVIOUS":
                        await player.play_previous()
                    case "VOLUME_UP":
                        await player.volume_up(5)
                    case "VOLUME_DOWN":
                        await player.volume_down(5)
'''
new = '''                    case "NEXT":
                        if self._is_avr:
                            if not await self._device.play_adjacent_favorite(self._player_id, +1):
                                return StatusCodes.BAD_REQUEST
                        else:
                            await player.play_next()
                    case "PREVIOUS":
                        if self._is_avr:
                            if not await self._device.play_adjacent_favorite(self._player_id, -1):
                                return StatusCodes.BAD_REQUEST
                        else:
                            await player.play_previous()
                    case "VOLUME_UP":
                        if self._is_avr:
                            if not await self._device.send_denon_steps(self._player_id, "MVUP", 2):
                                return StatusCodes.SERVER_ERROR
                        else:
                            await player.volume_up(1)
                    case "VOLUME_DOWN":
                        if self._is_avr:
                            if not await self._device.send_denon_steps(self._player_id, "MVDOWN", 2):
                                return StatusCodes.SERVER_ERROR
                        else:
                            await player.volume_down(1)
                    case "SUB1_UP":
                        if not self._is_avr:
                            return StatusCodes.NOT_IMPLEMENTED
                        if not await self._device.send_denon_steps(self._player_id, "CVSW UP", 2):
                            return StatusCodes.SERVER_ERROR
                    case "SUB1_DOWN":
                        if not self._is_avr:
                            return StatusCodes.NOT_IMPLEMENTED
                        if not await self._device.send_denon_steps(self._player_id, "CVSW DOWN", 2):
                            return StatusCodes.SERVER_ERROR
'''
replace(old, new)

p.write_text(s, encoding="utf-8")
compile(s, "remote.py", "exec")
