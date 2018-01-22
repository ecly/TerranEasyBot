import identifiers as ids


def units():
    return [Unit("SCV", ids.TERRAN_SCV, ids.TRAIN_SCV, ids.TERRAN_COMMAND_CENTER),
            Unit("Marine", ids.TERRAN_MARINE, ids.TRAIN_MARINE, ids.TERRAN_BARRACKS),
            Unit("Medivac", ids.TERRAN_MEDIVAC, ids.TRAIN_MEDIVAC, ids.TERRAN_STARPORT),
            ]


class Unit:
    def __init__(self, name, identifier, train, builds_from):
        self.name = name
        self.identifier = identifier
        self.train = train
        self.builds_from = builds_from
