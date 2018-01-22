from pysc2.lib import actions
from pysc2.lib import features


#Features
PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
PLAYER_ID = features.SCREEN_FEATURES.player_id.index

"""
Actions
"""
#Misc
NO_OP = actions.FUNCTIONS.no_op.id
SELECT_POINT = actions.FUNCTIONS.select_point.id
SELECT_ARMY = actions.FUNCTIONS.select_army.id
ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id
HARVEST_GATHER = actions.FUNCTIONS.Harvest_Gather_screen.id

#Build
BUILD_COMMAND_CENTER = actions.FUNCTIONS.Build_CommandCenter_screen.id
BUILD_SUPPLY_DEPOT = actions.FUNCTIONS.Build_SupplyDepot_screen.id
BUILD_BARRACKS = actions.FUNCTIONS.Build_Barracks_screen.id
BUILD_STARPORT = actions.FUNCTIONS.Build_Starport_screen.id
BUILD_REFINERY = actions.FUNCTIONS.Build_Refinery_screen.id
BUILD_FACTORY = actions.FUNCTIONS.Build_Factory_screen.id

# Train
TRAIN_SCV = actions.FUNCTIONS.Train_SCV_quick.id
TRAIN_MARINE = actions.FUNCTIONS.Train_Marine_quick.id
TRAIN_MEDIVAC = actions.FUNCTIONS.Train_Medivac_quick.id

"""
IDs:
Complete list of IDs
https://pastebin.com/KCwwLiQ1
"""
PLAYER_SELF = 1
PLAYER_HOSTILE = 4
ARMY_SUPPLY = 5
TERRAN_COMMAND_CENTER = 18
TERRAN_SUPPLY_DEPOT = 19
TERRAN_REFINERY = 20
TERRAN_BARRACKS = 21
TERRAN_FACTORY = 27
TERRAN_STARPORT = 28
TERRAN_SCV = 45
TERRAN_MARINE = 48
TERRAN_MEDIVAC = 54
NEUTRAL_VESPENE_GAS = 342
NEUTRAL_MINERAL_FIELD = 341
