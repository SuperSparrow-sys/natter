from u_pflanzen import Pflanze


class Garten:
    def __init__(self):
        self.beete: list[Pflanze] = []

    def pflanzen(self, pflanze: Pflanze):
        self.beete.append(pflanze)
