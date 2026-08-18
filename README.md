# HEOS Remote 3 – Denon AVR UI Patch

Dieses Projekt basiert **ausschließlich auf `mase1981/uc-intg-heos` v2.1.2**.
Die Denon/Marantz-Integration wird **nicht** als Integrationsbasis verwendet. Ihre Kommandotabelle dient nur als Referenz für die korrekten Denon-AVR-Telegramme.

## Gewünschtes Verhalten

Für als AVR erkannte HEOS-Player:

- **Power OFF:** Denon `PWSTANDBY`
- **Power ON:** Denon `PWON`
- **Lauter:** Denon `MVUP` zweimal pro Tastendruck = 1 dB
- **Leiser:** Denon `MVDOWN` zweimal pro Tastendruck = 1 dB
- **CH +:** Denon Subwoofer 1 `CVSW UP`
- **CH -:** Denon Subwoofer 1 `CVSW DOWN`
- **PREV:** vorheriger HEOS-Favorit
- **NEXT:** nächster HEOS-Favorit
- **PLAY/PAUSE/STOP/MUTE:** vorhandene HEOS-Funktion bleibt bestehen

Bei Nicht-AVR-HEOS-Playern bleibt das normale HEOS-Verhalten erhalten, soweit es von v2.1.2 vorgegeben ist.

## Denon-Kommunikation

Für AVR-Befehle wird kein Denon-Treiber eingebunden. Der HEOS-Player liefert die IP-Adresse des AVR; der Remote-Handler öffnet dafür direkt eine TCP-Verbindung auf Port 23 und sendet die dokumentierten Denon-Telnet-Kommandos mit `\\r`.

Der AVR muss Netzwerksteuerung für Steuerung aus Standby unterstützen/aktiviert haben.

## Upstream-Basis

- HEOS v2.1.2: https://github.com/mase1981/uc-intg-heos/tree/v2.1.2
- Die Patch-Datei in `patches/` ändert ausschließlich `uc_intg_heos/remote.py`.

## Build

Das Repo ist bewusst als **Patch-Projekt** aufgebaut: Die restliche HEOS-2.1.2-Integration bleibt unverändert und wird beim Build aus dem offiziellen Upstream-Tag bezogen.

```bash
./scripts/apply_patch.sh ../uc-intg-heos
```

Danach kann der normale Build der HEOS-2.1.2-Integration ausgeführt werden.
