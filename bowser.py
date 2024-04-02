import commune as c


class Bowser:
    def __init__(self):
        self.module = c.module.Module()

    def getbalance(self):
        self.module.get_stake()
        