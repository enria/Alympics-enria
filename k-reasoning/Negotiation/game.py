from copy import deepcopy
import numpy 

round_number = round

class Negotiation():
    def __init__(self, players, seed) -> None:
        self.all_players = players[::]
        self.result= {
            "winner": None
        }
        self.proposals = []

        self.setting = self.set_by_seed(seed)

    def set_by_seed(self, seed):
        exchange = bool(seed%2)
        if exchange: seed-=1
        item_pool = []
        rng = numpy.random.RandomState(seed)
        target_sum = rng.randint(0, 31)
        def generate_value_vector():
            while True:
                vec1 = rng.randint(0, 11, 2)
                vec1_third = target_sum - vec1.sum()
                
                if 0 <= vec1_third <= 10:
                    vec1 = numpy.append(vec1, vec1_third)
                    break
            return vec1.tolist()
        
        def generate_quantity_vector():
            while True:
                vector = rng.randint(0, 6, 3)
                zero_count = numpy.count_nonzero(vector == 0)
                if zero_count <= 1:
                    return vector.tolist()
        
        item_pool = generate_quantity_vector()
        values = [generate_value_vector() for i in range(len(self.all_players))]
        if exchange: values=values[::-1]
        return {
            "item": item_pool,
            "values": values
        }

    def check_return(self, player_id, bid):
        returns = {}
        for index in range(len(self.all_players)):
            if index==player_id:
                split = bid
            else:
                split = [t-b for t,b in zip(self.setting["item"], bid)]
            p = sum([i*v for i, v in zip(split, self.setting["values"][index])])
            returns[self.all_players[index].name]=p
        win_retrun = max(returns.values())
        winners = [player_name for player_name, payoff in returns.items() if payoff==win_retrun]

        return winners, returns

    def run_single_round(self, round_id, player_id, begining=False):
        current_player = self.all_players[player_id]
        current_player.start_round(round_id, begining)
        Aggree, Bid = current_player.act()

        if Aggree: # If all players choose the same number, there is no winner.
            Bid = self.proposals[-1]
            WINNER, RETURNS = self.check_return(int(not bool(player_id)), Bid )
            return True, WINNER, RETURNS
        else:
            self.proposals.append(Bid)
            history_biddings = {player.name: deepcopy(player.biddings) for player in self.all_players} 

            for player in self.all_players:
                if player==current_player: continue
                player.notice_round_result(round_id, Bid, history_biddings)

            for player in self.all_players:
                player.end_round()

            return False, None, None

    def run_multi_round(self, max_round):
        for index, player in enumerate(self.all_players):
            player.set_info(self.setting["item"], self.setting["values"][index])
        
        # try:
        #     for i in range(1, max_round+1):
        #         for j in range(len(self.all_players)):
        #             current_player = self.all_players[j].name
        #             terminated, winner, payoffs = self.run_single_round(i, j, begining=(i==1 and j==0))
        #             if terminated:
        #                 self.result={
        #                     "winner": winner,
        #                     "payoffs": payoffs,
        #                     "bid": self.proposals[-1]
        #                 }
        #                 return 
        # except BaseException as e:
        #     print(e)                
        #     self.result={
        #         "error": True,
        #         "last_turn": current_player
        #     }
        
        for i in range(1, max_round+1):
            for j in range(len(self.all_players)):
                current_player = self.all_players[j].name
                terminated, winner, payoffs = self.run_single_round(i, j, begining=(i==1 and j==0))
                if terminated:
                    self.result={
                        "winner": winner,
                        "payoffs": payoffs,
                        "bid": self.proposals[-1]
                    }
                    return 
        
        