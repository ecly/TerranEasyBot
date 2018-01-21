import random
import math
import os

import numpy as np
import pandas as pd
import units_and_buildings as ub

from random import randint
from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

_UNITS = ub.Unit.units()
_BUILDINGS = ub.Building.buildings()

_NO_OP = actions.FUNCTIONS.no_op.id
_SELECT_POINT = actions.FUNCTIONS.select_point.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id
_HARVEST_GATHER = actions.FUNCTIONS.Harvest_Gather_screen.id


_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
_PLAYER_ID = features.SCREEN_FEATURES.player_id.index

_PLAYER_SELF = 1
_PLAYER_HOSTILE = 4
_ARMY_SUPPLY = 5

_NOT_QUEUED = [0]
_QUEUED = [1]
_SELECT_ALL = [2]

DATA_FILE = 'sparse_agent_data'

ACTION_DO_NOTHING = 'donothing'
ACTION_ATTACK = 'attack'

UNIT_ACTION_MAP = {u.smart_action: u for u in _UNITS}
BUILDING_ACTION_MAP = {b.smart_action: b for b in _BUILDINGS}
smart_actions = [ACTION_DO_NOTHING] + list(UNIT_ACTION_MAP) + list(BUILDING_ACTION_MAP)

for mm_x in range(0, 64):
    for mm_y in range(0, 64):
        if (mm_x + 1) % 32 == 0 and (mm_y + 1) % 32 == 0:
            smart_actions.append(ACTION_ATTACK + '_' +
                                 str(mm_x - 16) + '_' + str(mm_y - 16))

# Stolen from https://github.com/MorvanZhou/Reinforcement-learning-with-tensorflow
class QLearningTable:
    def __init__(self, actions, learning_rate=0.01, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions  # a list
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon = e_greedy
        self.q_table = pd.DataFrame(columns=self.actions, dtype=np.float64)

    def choose_action(self, observation):
        self.check_state_exist(observation)

        if np.random.uniform() < self.epsilon:
            # choose best action
            state_action = self.q_table.ix[observation, :]

            # some actions have the same value
            state_action = state_action.reindex(
                np.random.permutation(state_action.index))

            action = state_action.idxmax()
        else:
            # choose random action
            action = np.random.choice(self.actions)

        return action

    def learn(self, s, a, r, s_):
        self.check_state_exist(s_)
        self.check_state_exist(s)

        q_predict = self.q_table.ix[s, a]

        if s_ != 'terminal':
            q_target = r + self.gamma * self.q_table.ix[s_, :].max()
        else:
            q_target = r  # next state is terminal

        # update
        self.q_table.ix[s, a] += self.lr * (q_target - q_predict)

    def check_state_exist(self, state):
        if state not in self.q_table.index:
            # append new state to q table
            self.q_table = self.q_table.append(
                pd.Series([0] * len(self.actions), index=self.q_table.columns, name=state))


class SparseAgent(base_agent.BaseAgent):
    def __init__(self):
        super(SparseAgent, self).__init__()

        self.qlearn = QLearningTable(actions=list(range(len(smart_actions))))
        self.previous_action = None
        self.previous_state = None
        self.cc_y = None
        self.cc_x = None
        self.move_number = 0

        if os.path.isfile(DATA_FILE + '.gz'):
            self.qlearn.q_table = pd.read_pickle(DATA_FILE + '.gz', compression='gzip')

    def select_workers(self, obs):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        unit_y, unit_x = (unit_type == ub.TERRAN_SCV).nonzero()
        if unit_y.any():
            i = random.randint(0, len(unit_y) - 1)
            target = [unit_x[i], unit_y[i]]
            return actions.FunctionCall(_SELECT_POINT, [_NOT_QUEUED, target])

    def unit_attack(self, x, y, obs):
        if self.move_number == 0:
            if _SELECT_ARMY in obs.observation['available_actions']:
                return actions.FunctionCall(_SELECT_ARMY, [_NOT_QUEUED])
        elif self.move_number == 1:
            do_it = True

            if len(obs.observation['single_select']) > 0 and obs.observation['single_select'][0][0] == ub.TERRAN_SCV:
                do_it = False

            if len(obs.observation['multi_select']) > 0 and obs.observation['multi_select'][0][0] == ub.TERRAN_SCV:
                do_it = False

            if do_it and _ATTACK_MINIMAP in obs.observation["available_actions"]:
                x_offset = random.randint(-1, 1)
                y_offset = random.randint(-1, 1)
                return actions.FunctionCall(_ATTACK_MINIMAP, [_NOT_QUEUED, self.transformLocation(int(x) + (x_offset * 8), int(y) + (y_offset * 8))])

    def train_unit(self, building_type, obs):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        if self.move_number == 0:
            target = ub.Building.get_location_from_id(building_type, obs)
            if target is not None:
                return actions.FunctionCall(_SELECT_POINT, [_SELECT_ALL, target])
        if self.move_number == 1:
            if unit_type in obs.observation['available_actions']:
                return actions.FunctionCall(unit_type, [_QUEUED])

    # assumes a worker is selected
    def return_worker_to_harvest(self, obs):
        r = randint(0, 99)
        target = ub.Building.get_location_from_id(ub.NEUTRAL_VESPENE_GAS, obs) if r < 20 else \
            ub.Building.get_location_from_id(ub.NEUTRAL_MINERAL_FIELD, obs)
        return actions.FunctionCall(_HARVEST_GATHER, [_QUEUED, target])

    def build(self, building, obs):
        if self.move_number == 0:
            return self.select_workers(obs)
        elif self.move_number == 1:
            if building.amount_of_building(obs) < building.max_amount and building.build in obs.observation['available_actions']:
                return actions.FunctionCall(building.build, [_NOT_QUEUED, building.get_location(self, obs)])
        elif self.move_number == 2:
            if _HARVEST_GATHER in obs.observation['available_actions'] and building.build is not ub.BUILD_REFINERY:
                return self.return_worker_to_harvest(obs)

    @staticmethod
    def get_location(_id, obs):
        unit_type = obs.observation['screen'][_UNIT_TYPE]
        unit_y, unit_x = (unit_type == _id).nonzero()
        if unit_y.any():
            i = random.randint(0, len(unit_y) - 1)
            m_x = unit_x[i]
            m_y = unit_y[i]
            return [m_x, m_y]

    def transformDistance(self, x, x_distance, y, y_distance):
        if not self.base_top_left:
            return [x - x_distance, y - y_distance]
        return [x + x_distance, y + y_distance]

    def transformLocation(self, x, y):
        if not self.base_top_left:
            return [64 - x, 64 - y]
        return [x, y]

    def splitAction(self, action_id):
        smart_action = smart_actions[action_id]
        y = x = 0
        if '_' in smart_action:
            smart_action, x, y = smart_action.split('_')

        return (smart_action, x, y)


    def step(self, obs):
        super(SparseAgent, self).step(obs)

        if obs.last():
            reward = obs.reward

            self.qlearn.learn(str(self.previous_state),
                              self.previous_action, reward, 'terminal')

            self.qlearn.q_table.to_pickle(DATA_FILE + '.gz', 'gzip')
            self.previous_action = None
            self.previous_state = None
            self.move_number = 0

            return actions.FunctionCall(_NO_OP, [])

        unit_type = obs.observation['screen'][_UNIT_TYPE]

        if obs.first():
            player_y, player_x = (obs.observation['minimap'][_PLAYER_RELATIVE] == _PLAYER_SELF).nonzero()
            self.base_top_left = 1 if player_y.any() and player_y.mean() <= 31 else 0
            self.cc_y, self.cc_x = (unit_type == ub.TERRAN_COMMAND_CENTER).nonzero()

        cc_y, cc_x = (unit_type == ub.TERRAN_COMMAND_CENTER).nonzero()
        cc_count = 1 if cc_y.any() else 0

        depot = BUILDING_ACTION_MAP[ub.ACTION_BUILD_SUPPLY_DEPOT]
        supply_depot_count = depot.amount_of_building(obs)
        building_types = [ub.ACTION_BUILD_STARPORT, ub.ACTION_BUILD_BARRACKS, ub.ACTION_BUILD_BARRACKS]
        building_count = sum(map(lambda b: BUILDING_ACTION_MAP[b].amount_of_building(obs), building_types))

        if self.move_number == 0:
            current_state = np.zeros(8)
            current_state[0] = cc_count
            current_state[1] = supply_depot_count
            current_state[2] = building_count
            current_state[3] = obs.observation['player'][_ARMY_SUPPLY]

            hot_squares = np.zeros(4)
            enemy_y, enemy_x = (obs.observation['minimap'][_PLAYER_RELATIVE] == _PLAYER_HOSTILE).nonzero()
            for i in range(0, len(enemy_y)):
                y = int(math.ceil((enemy_y[i] + 1) / 32))
                x = int(math.ceil((enemy_x[i] + 1) / 32))
                hot_squares[((y - 1) * 2) + (x - 1)] = 1

            if not self.base_top_left:
                hot_squares = hot_squares[::-1]

            for i in range(0, 4):
                current_state[i + 4] = hot_squares[i]

            if self.previous_action is not None:
                self.qlearn.learn(str(self.previous_state),
                                  self.previous_action, 0, str(current_state))

            rl_action = self.qlearn.choose_action(str(current_state))

            self.previous_state = current_state
            self.previous_action = rl_action

        smart_action, x, y = self.splitAction(self.previous_action)

        if smart_action in UNIT_ACTION_MAP:
            move = self.train_unit(UNIT_ACTION_MAP[smart_action], obs)
        elif smart_action in BUILDING_ACTION_MAP:
            move = self.build(BUILDING_ACTION_MAP[smart_action], obs)
        elif smart_action == ACTION_ATTACK:
            move = self.unit_attack(x, y, obs)
        else:
            move = actions.FunctionCall(_NO_OP, [])

        if move is None:
            move = actions.FunctionCall(_NO_OP, [])
        
        self.move_number = 0 if self.move_number == 3 else self.move_number + 1
        return move
