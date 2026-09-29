# Das zweite Fenster des Notizbuchs: eine kleine Info.
#
# Ein Formular wie jedes andere, mit eigener .pfm und eigenem
# Designer. u_main.py erzeugt es mit FormInfo() und öffnet es mit
# show_modal(). „OK“ ist der Standardknopf (default im
# Objektinspektor): die Eingabetaste schließt das Fenster.

from u_info_design import FormInfoDesign


class FormInfo(FormInfoDesign):
    def b_ok_click(self, sender) -> None:
        self.close()
