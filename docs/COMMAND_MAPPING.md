# Command Mapping

| Remote-Funktion | AVR-Telegramm |
|---|---|
| Power ON | `PWON` |
| Power OFF | `PWSTANDBY` |
| Volume + 1 dB | `MVUP` + `MVUP` |
| Volume - 1 dB | `MVDOWN` + `MVDOWN` |
| Subwoofer + | `CVSW UP` |
| Subwoofer - | `CVSW DOWN` |

PREV/NEXT verwenden keine Denon-Track-Transport-Kommandos. Sie rufen HEOS-Favoriten über `get_favorites()` ab und wechseln mit `play_preset_station()` zum vorherigen/nächsten Favoriten.
