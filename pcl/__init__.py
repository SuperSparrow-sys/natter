"""Python Component Library (pcl) – Laufzeit der Natter-Komponenten.

Wird von Schülerprogrammen und der exportierten .exe verwendet, läuft ohne IDE.
Siehe konzept-natter.md, Abschnitt 5. Beispiel (Abschnitt 4.3):

    from pcl import Application, Button, Form, Shape
"""

from pcl.application import Application
from pcl.components.additional import Shape
from pcl.components.standard import (
    Button,
    CheckBox,
    ComboBox,
    Edit,
    Label,
    ListBox,
    Memo,
    RadioButton,
)
from pcl.control import Control
from pcl.form import Form
from pcl.properties import Event, Prop
from pcl.strings import Strings

__all__ = [
    "Application",
    "Button",
    "CheckBox",
    "ComboBox",
    "Control",
    "Edit",
    "Event",
    "Form",
    "Label",
    "ListBox",
    "Memo",
    "Prop",
    "RadioButton",
    "Shape",
    "Strings",
]
