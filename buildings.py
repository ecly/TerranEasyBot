import identifiers as ids
import random

# Sizes used for determining amount of a certain building on screen
SMALL_PIX = 69
BIG_PIX = 137

# Sizes used for determining offsets when building new buildings
SMALL_GRID = 7
BIG_GRID = 12

# Several buildings to be build in a shared multi-column layout
COLUMN_HEIGHT = 5
SHARED_COLUMN = {ids.BUILD_STARPORT, ids.BUILD_BARRACKS, ids.BUILD_FACTORY}


def buildings():
    return [Building("Supply Depot", ids.TERRAN_SUPPLY_DEPOT, ids.BUILD_SUPPLY_DEPOT, 8, SMALL_GRID, SMALL_PIX),
            Building("Barracks", ids.TERRAN_BARRACKS, ids.BUILD_BARRACKS, 4, BIG_GRID, BIG_PIX),
            Building("Factory", ids.TERRAN_FACTORY, ids.BUILD_FACTORY, 2, BIG_GRID, BIG_PIX),
            Building("Starport", ids.TERRAN_STARPORT, ids.BUILD_STARPORT, 2, BIG_GRID, BIG_PIX),
            Building("Refinery", ids.TERRAN_REFINERY, ids.BUILD_REFINERY, 2, BIG_GRID, BIG_PIX)
            ]


def get_location_from_id(_id, obs):
    unit_type = obs.observation['screen'][ids.UNIT_TYPE]
    unit_y, unit_x = (unit_type == _id).nonzero()
    if unit_y.any():
        i = random.randint(0, len(unit_y) - 1)
        m_x = unit_x[i]
        m_y = unit_y[i]
        return [m_x, m_y]


class Building:
    def __init__(self, name, identifier, build, max_amount, size_grid, size_pixels):
        self.name = name
        self.identifier = identifier
        self.build = build
        self.max_amount = max_amount
        self.size_grid = size_grid
        self.size_pixels = size_pixels

    def amount_of_building(self, obs):
        unit_type = obs.observation['screen'][ids.UNIT_TYPE]
        _y, _ = (unit_type == self.identifier).nonzero()
        return int(round(len(_y) / self.size_pixels))

    def should_build(self, obs):
        return self.amount_of_building(obs) < self.max_amount and self.build in obs.observation['available_actions']

    def get_location(self, agent, obs):
        if self.build in SHARED_COLUMN:
            amount = sum(map(lambda b: b.amount_of_building(obs), filter(lambda b: b.build in SHARED_COLUMN, buildings())))
            x_offset = 20 + int(amount/COLUMN_HEIGHT) * self.size_grid
            y_offset = -30 + self.size_grid * (amount % COLUMN_HEIGHT)
        elif self.identifier == ids.TERRAN_SUPPLY_DEPOT:
            amount = self.amount_of_building(obs)
            shift = 4
            x_offset = -37 if amount < shift else -25 + self.size_grid * (amount % shift)
            y_offset = -23 + self.size_grid * amount if amount < shift else -32
        elif self.identifier == ids.TERRAN_REFINERY:
            return get_location_from_id(ids.NEUTRAL_VESPENE_GAS, obs)

        return agent.transformDistance(round(agent.cc_x.mean()), x_offset, round(agent.cc_y.mean()), y_offset)

