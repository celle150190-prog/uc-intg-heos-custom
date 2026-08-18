# HEOS Custom – Media UI

Custom build based on `mase1981/uc-intg-heos` 2.1.2 for Unfolded Circle Remote 3.

## Änderungen

- Media-UI `Next` / `Previous` navigieren durch die gespeicherten HEOS-Favoriten statt durch den aktuellen Track.
- Lautstärke `+` / `-` arbeitet in 1-dB-Schritten.
- Die Media-UI stellt `Channel Up/Down` bereit; diese steuern beim AVR Subwoofer 1 über `CVSW UP/DOWN`.
- Bei einem als AVR erkannten HEOS-Player wird `HEOS` als auswählbare Media-Quelle angeboten. Die Auswahl startet/resumiert HEOS, sodass die Quelle in Aktivitäten verwendet werden kann.
- Keine Änderungen an der separaten Remote-UI.

## Build

Der GitHub-Action-Workflow holt exakt den Upstream-Stand 2.1.2, wendet den Patch an und baut ein aarch64-TAR.GZ für die Remote 3.
