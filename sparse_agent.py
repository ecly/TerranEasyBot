import random
import os
import buildings
import units

import numpy as np
import pandas as pd
import identifiers as ids

from random import randint
from pysc2.agents import base_agent
from pysc2.lib import actions

UNITS = {u.name: u for u in units.units()}
BUILDINGS = {b.name: b for b in buildings.buildings()}

_NOT_QUEUED = [0]
_QUEUED = [1]
_SELECT_ALL = [2]

DATA_FILE = 'sparse_agent_data'
ACTION_DO_NOTHING = 'donothing'
ACTION_ATTACK = 'attack'

smart_actions = [ACTION_DO_NOTHING] + list(UNITS) + list(BUILDINGS)

#for mm_x in range(0, 64):
#    for mm_y in range(0, 64):
#        if (mm_x + 1) % 32 == 0 and (mm_y + 1) % 32 == 0:
#            smart_actions.append(ACTION_ATTACK + '_' + str(mm_x - 16) + '_' + str(mm_y - 16))

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
        q_target = r + self.gamma * self.q_table.ix[s_, :].max() if s_ != 'terminal' else r  # next state is terminal

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
        self.previous_num_starports = 0
        self.previous_num_factory = 0
        self.cc_y = None
        self.cc_x = None
        self.move_number = 0

        if os.path.isfile(DATA_FILE + '.gz'):
            self.qlearn.q_table = pd.read_pickle(
                DATA_FILE + '.gz', compression='gzip')

    def select_workers(self, obs):
        unit_type = obs.observation['screen'][ids.UNIT_TYPE]
        unit_y, unit_x = (unit_type == ids.TERRAN_SCV).nonzero()
        if unit_y.any():
            i = random.randint(0, len(unit_y) - 1)
            target = [unit_x[i], unit_y[i]]
            return actions.FunctionCall(ids.SELECT_POINT, [_NOT_QUEUED, target])

    def unit_attack(self, x, y, obs):
        if self.move_number == 0:
            if ids.SELECT_ARMY in obs.observation['available_actions']:
                return actions.FunctionCall(ids.SELECT_ARMY, [_NOT_QUEUED])
        elif self.move_number == 1:
            do_it = True

            if ((len(obs.observation['single_select']) > 0 and obs.observation['single_select'][0][0] == ids.TERRAN_SCV)
               or (len(obs.observation['multi_select']) > 0 and obs.observation['multi_select'][0][0] == ids.TERRAN_SCV)):
                do_it = False

            if do_it and ids.ATTACK_MINIMAP in obs.observation["available_actions"]:
                x_offset = random.randint(-1, 1)
                y_offset = random.randint(-1, 1)
                return actions.FunctionCall(ids.ATTACK_MINIMAP, [_NOT_QUEUED, self.transformLocation(int(x) + (x_offset * 8), int(y) + (y_offset * 8))])

    def train_unit(self, unit, obs):
        if self.move_number == 0:
            target = buildings.get_location_from_id(unit.builds_from, obs)
            if target is not None:
                return actions.FunctionCall(ids.SELECT_POINT, [_SELECT_ALL, target])
        if self.move_number == 1:
            if unit.train in obs.observation['available_actions']:
                return actions.FunctionCall(unit.train, [_QUEUED])

    # assumes a worker is selected
    def return_worker_to_harvest(self, obs):
        r = randint(0, 99)
        target = buildings.get_location_from_id(ids.NEUTRAL_VESPENE_GAS, obs) if r < 20 else \
            buildings.get_location_from_id(ids.NEUTRAL_MINERAL_FIELD, obs)
        return actions.FunctionCall(ids.HARVEST_GATHER, [_QUEUED, target])

    def build(self, building, obs):
        if self.move_number == 0:
            return self.select_workers(obs)
        elif self.move_number == 1:
            if building.amount_of_building(obs) < building.max_amount and building.build in obs.observation['available_actions']:
                return actions.FunctionCall(building.build, [_NOT_QUEUED, building.get_location(self, obs)])
        elif self.move_number == 2:
            if ids.HARVEST_GATHER in obs.observation['available_actions'] and building.build is not ids.BUILD_REFINERY:
                return self.return_worker_to_harvest(obs)

    @staticmethod
    def get_location(_id, obs):
        unit_type = obs.observation['screen'][ids.UNIT_TYPE]
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


    def award_step_reward(self, current_state, obs):
        reward = 0
        num_starports = BUILDINGS["Starport"].amount_of_building(obs)
        """
        num_starports =  self.amount_of_building(_TERRAN_STARPORT, obs)
        if num_starports > self.previous_num_starports:
            print("GOOD JOB on the starport")
            reward += 100
        self.previous_num_starports = num_starports

        num_factory =  self.amount_of_building(_TERRAN_FACTORY, obs)
        if num_factory > self.previous_num_factory:
            print("GOOD JOB on the factory")
            reward += 50
        self.previous_num_factory = num_factory
        self.previous_num_starports = num_starports
        """
        self.qlearn.learn(str(self.previous_state),self.previous_action, reward, str(current_state))

    def award_end_game_reward(self, obs):
        #reward = obs.reward
        reward = 0
        reward += 10*self.previous_state[2]
        reward += 50*self.previous_state[3]
        reward += 250*self.previous_state[4]
        print("Total barracks: " + str(self.previous_state[2]))
        print("Total factory: " + str(self.previous_state[3]))
        print("Total starport: " + str(self.previous_state[4]))
        print("Total reward: " + str(reward))

        self.qlearn.learn(str(self.previous_state), self.previous_action, reward, 'terminal')

    def update_state(self, obs):
        unit_type = obs.observation['screen'][ids.UNIT_TYPE]
        cc_y, cc_x = (unit_type == ids.TERRAN_COMMAND_CENTER).nonzero()
        cc_count = 1 if cc_y.any() else 0

        supply_depot_count = BUILDINGS["Supply Depot"].amount_of_building(obs)
        refinery_count = BUILDINGS["Refinery"].amount_of_building(obs)
        barracks_count = BUILDINGS["Barracks"].amount_of_building(obs)
        factory_count = BUILDINGS["Factory"].amount_of_building(obs)
        starport_count = BUILDINGS["Starport"].amount_of_building(obs)
        current_state = np.zeros(6)
        
        current_state[0] = cc_count
        current_state[1] = supply_depot_count
        current_state[2] = barracks_count
        current_state[3] = factory_count
        current_state[4] = starport_count
        current_state[5] = refinery_count
        print(current_state)
        #current_state[5] = obs.observation['player'][_ARMY_SUPPLY]

        """
        hot_squares = np.zeros(4)
        enemy_y, enemy_x = (
            obs.observation['minimap'][_PLAYER_RELATIVE] == _PLAYER_HOSTILE).nonzero()
        for i in range(0, len(enemy_y)):
            y = int(math.ceil((enemy_y[i] + 1) / 32))
            x = int(math.ceil((enemy_x[i] + 1) / 32))

            hot_squares[((y - 1) * 2) + (x - 1)] = 1

        if not self.base_top_left:
            hot_squares = hot_squares[::-1]

        for i in range(0, 4):
            current_state[i + 4] = hot_squares[i]
        """
        return current_state

    def step(self, obs):
        super(SparseAgent, self).step(obs)

        if obs.last():
            self.award_end_game_reward(obs)
            self.qlearn.q_table.to_pickle(DATA_FILE + '.gz', 'gzip')
            self.previous_action = None
            self.previous_state = None
            self.move_number = 0

            return actions.FunctionCall(ids.NO_OP, [])

        unit_type = obs.observation['screen'][ids.UNIT_TYPE]

        if obs.first():
            player_y, player_x = (
                obs.observation['minimap'][ids.PLAYER_RELATIVE] == ids.PLAYER_SELF).nonzero()
            self.base_top_left = 1 if player_y.any() and player_y.mean() <= 31 else 0
            self.cc_y, self.cc_x = (
                unit_type == ids.TERRAN_COMMAND_CENTER).nonzero()

        if self.move_number == 0:
            current_state = self.update_state(obs)

            if self.previous_action is not None:
                self.award_step_reward(current_state, obs)

            rl_action = self.qlearn.choose_action(str(current_state))

            self.previous_state = current_state
            self.previous_action = rl_action

        smart_action, x, y = self.splitAction(self.previous_action)

        if smart_action in UNITS:
            move = self.train_unit(UNITS[smart_action], obs)
        elif smart_action in BUILDINGS:
            move = self.build(BUILDINGS[smart_action], obs)
        elif smart_action == ACTION_ATTACK:
            move = self.unit_attack(x, y, obs)
        else:
            move = actions.FunctionCall(ids.NO_OP, [])

        if move is None:
            move = actions.FunctionCall(ids.NO_OP, [])

        self.move_number = 0 if self.move_number == 3 else self.move_number + 1
        return move
