"""Python Component Library (pcl) – Laufzeit der Natter-Komponenten.

Wird von Schülerprogrammen und der exportierten .exe verwendet, läuft ohne IDE.
Siehe konzept-natter.md, Abschnitt 5. Beispiel (Abschnitt 4.3):

    from pcl import Application, Button, Form, Shape
"""

from pcl.application import Application
from pcl.components.additional import Shape
from pcl.components.standard import Button, Label
from pcl.control import Control
from pcl.form import Form
from pcl.properties import Event, Prop

__all__ = [
    "Application",
    "Button",
    "Control",
    "Event",
    "Form",
    "Label",
    "Prop",
    "Shape",
]
