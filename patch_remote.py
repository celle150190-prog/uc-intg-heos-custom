from pathlib import Path

p = Path("uc_intg_heos/remote.py")
s = p.read_text(encoding="utf-8")

# Physical Play button becomes Play/Pause; Stop is removed from the remote UI.
old_buttons = '''            create_btn_mapping(Buttons.PLAY, short="PLAY"),
            create_btn_mapping(Buttons.STOP, short="STOP"),
'''
new_buttons = '''            create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
'''
if old_buttons not in s:
    raise SystemExit("Button mapping block not found")
s = s.replace(old_buttons, new_buttons, 1)

# Replace the original command/UI section with playback + HEOS favorites only.
start = s.index("    def _build_commands(self, device: HeosDevice) -> list[str]:")
end = s.index("    async def _handle_command(", start)

new_section = '''    def _build_commands(self, device: HeosDevice) -> list[str]:
        cmds = [
            "PLAY_PAUSE",
            "NEXT",
            "PREVIOUS",
            "VOLUME_UP",
            "VOLUME_DOWN",
            "MUTE_TOGGLE",
        ]

        # Favorites are loaded by HeosDevice before entities are registered.
        for favorite_id in device.favorites:
            cmds.append(f"FAVORITE_{favorite_id}")

        return cmds

    def _build_ui_pages(self, player_name: str, device: HeosDevice) -> list[UiPage]:
        pages = []

        # Page 1: playback controls only.
        page1 = UiPage("playback", f"{player_name} Controls", grid=Size(4, 6))
        page1.add(create_ui_text("HEOS", 0, 0, Size(4, 1)))
        page1.add(create_ui_icon("uc:prev", 0, 1, cmd="PREVIOUS"))
        page1.add(create_ui_icon("uc:play", 1, 1, cmd="PLAY_PAUSE"))
        page1.add(create_ui_icon("uc:next", 2, 1, cmd="NEXT"))
        page1.add(create_ui_icon("uc:up-arrow-bold", 0, 2, cmd="VOLUME_UP"))
        page1.add(create_ui_icon("uc:down-arrow-bold", 1, 2, cmd="VOLUME_DOWN"))
        page1.add(create_ui_icon("uc:mute", 2, 2, cmd="MUTE_TOGGLE"))
        pages.append(page1)

        # Page 2+: only HEOS favorites. No HDMI/AUX, inputs, repeat, shuffle or grouping.
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

'''
s = s[:start] + new_section + s[end:]

# Add direct favorite playback while leaving the original legacy handlers untouched.
needle = '''                    case cmd if cmd in INPUT_COMMAND_MAP:
                        input_name = INPUT_COMMAND_MAP[cmd]
                        await player.play_input_source(input_name)
'''
favorite_case = '''                    case cmd if cmd.startswith("FAVORITE_"):
                        try:
                            favorite_id = int(cmd.split("_", 1)[1])
                        except ValueError:
                            return StatusCodes.BAD_REQUEST
                        if favorite_id not in self._device.favorites:
                            return StatusCodes.BAD_REQUEST
                        await player.play_preset_station(favorite_id)
'''
if needle not in s:
    raise SystemExit("Input command handler not found")
s = s.replace(needle, favorite_case + "\n" + needle, 1)

p.write_text(s, encoding="utf-8")
