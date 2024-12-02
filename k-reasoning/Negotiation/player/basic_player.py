from random import randint
import numpy as np

class Player():
    def __init__(self, name):
        self.name = name
        self.hp = 10
        self.biddings=[]
        self.cur_round = -1

        self.logs = None

    def start_round(self, round: int):
        self.cur_round = round

    def act(self):
        raise NotImplementedError
    
    def notice_round_result(self, round, bidding_info, round_target, win, bidding_details, history_biddings):
        raise NotImplementedError

    def end_round(self):
        pass

    def deduction(self, deducted_hp):
        self.hp -= deducted_hp
    
    @property
    def last_bidding(self):
        return self.biddings[-1]
    
    def show_info(self, print_ = False):
        if print_:
            print(f"NAME:{self.name}\tHEALTH POINT:{self.hp}\n")
        return f"NAME:{self.name}\tHEALTH POINT:{self.hp}"


class ProgramPlayer(Player):
    is_agent=False
    def __init__(self, name, strategy, mean, std):
        self.name = name
        self.hp = 10

        self.biddings = []

        self.strategy=strategy

        self.logs = None

    
    def start_round(self, round):
        return
    
    def end_round(self):
        pass

    def notice_round_result(self, round, bidding_info, round_target, win, bidding_details, history_biddings):
        pass
        
    def set_normal(self, mean, std):
        self.normal = True
        self.mean = mean
        self.std = std
    
    def act(self):
        if self.strategy=="mono":
            bidding = self.mean
        else:
            bidding = np.random.normal(self.mean, self.std)
        bidding = min(max(int(bidding), 1),100)
        self.biddings.append(bidding) 


from open_spiel.python.algorithms import mcts
class MCTSPlayert(ProgramPlayer):
    def __init__(self, config, **kwargs):
        # super(MCTSPlayert, self).__init__(config)
        self.rollout_count = 1
        self.uct_c = 2
        self.max_simulations = 1000
        self.solve = True
        self.verbose = False
        rng = np.random.RandomState()
        evaluator = mcts.RandomRolloutEvaluator(self.rollout_count, rng)
        self.bot = mcts.MCTSBot(
            kwargs['game'],
            self.uct_c,
            self.max_simulations,
            evaluator,
            random_state=rng,
            solve=self.solve,
            verbose=self.verbose)
    
    def notice_round_result(self, round, bidding_info, round_target, win, bidding_details, history_biddings):
        raise NotImplementedError

    def act(self):
        agent_action_list = observations['legal_moves']
        openspiel_action_list = observations['openspiel_legal_actions']
        state = observations['state']
        action = self.bot.step(state)

        # print(agent_action_list)
        # print(openspiel_action_list)
        # print(action)
        return agent_action_list[openspiel_action_list.index(action)], []

    def inform_action(self, state, player_idx, action):
        self.bot.inform_action(state, player_idx, action)