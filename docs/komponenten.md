# Komponenten-Referenz

Verbindliche Schnittstelle für `pcl`. Jede Komponente wird hier mit jeder
Eigenschaft (Name, Typ, Standardwert, Kategorie, deutscher Hilfetext) und
jedem Ereignis (Name, Signatur, Auslöser) dokumentiert, bevor sie in `pcl`
umgesetzt wird. Siehe konzept-natter.md, Abschnitt 5 und 23.2.

Status: leer. Wird ab M1 komponentenweise gefüllt, beginnend mit den
Standard-Komponenten aus Abschnitt 5.2 (Form, Label, Edit, Button, CheckBox,
RadioButton, RadioGroup, Memo, ComboBox, ListBox, ScrollBar, GroupBox, Panel,
MainMenu, PopupMenu).

## Vorlage pro Komponente

```
## <Komponente>

Qt-Basis: <...>

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| ... | ... | ... |
```
