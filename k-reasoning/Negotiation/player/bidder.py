import time
from copy import deepcopy
from openai import BadRequestError
from functools import cmp_to_key
import json
import re

from .reasoning_player import AgentPlayer

round_number = round



class BIDDERPlayer(AgentPlayer):
    INQUIRY_COT = ("First think step by step, and finalize your response (proposal or agreement).")
    INQUIRY_KR = ("Another game expert's prediction for the next round of the opponent's action is as follows: "
                   "{prediction}"
                   "Based on the prediction of other players, first think step by step, and finalize your response (proposal or agreement).")

    PREDICTION_SUMMARY = "If your proposal is {my}, then the opponent will {opponent}."
    PREDICTION_INQUIRY = 'Just output your decision, don\'t use any other text.'
    PREDICTION_RESPONSE = "Proposal: {bidding}."

    def __init__(self, name, persona, client, players, player_k):
        super().__init__(name, persona, client)
        self.logs = {}
        
        self.opponent_biddings = []
        self.opponent_name = [p for p in players if p!=name][0]

        self.k_level = player_k
    
    def llm_query(self, msgs):
        while 1:
            try:
                response = self.client.chat_completion(messages = msgs)
                return response
            except BadRequestError as e:
                print(e)
                raise e
            except Exception as e:
                print(e)
                time.sleep(15)

    def start_round(self, round, begining):
        query = self.INQUIRY_COT

        self.message += [{"role":"user","content":self.get_state_prompt(begining)+ "\n" + query}]
    
    def notice_round_result(self, round, bidding_info, history_biddings):
        super().notice_round_result(round, bidding_info, history_biddings)
        self.opponent_biddings = [biddings for player, biddings in history_biddings.items() if player!=self.name][0]

    
    @staticmethod
    def is_over(utterance):
        return "agree" in utterance.lower()
    
    @staticmethod
    def to_next_obs(obs, utterance, opponent_values):
        # def to_str_list(l):
        #     l = eval(l)
        #     l = [str(i) for i in l]
        #     return l
        assert type(utterance)==list and len(utterance)==3
        new_obs = deepcopy(obs)
        new_obs["self_moves"].append(utterance)
        change_position = True
        assert opponent_values, "Provide opponent values"
        new_obs["opponent_moves"], new_obs["self_moves"] = new_obs["self_moves"], new_obs["opponent_moves"]
        new_obs["self_value_vector"] = opponent_values
        new_obs["mose_recent_utterance"] = utterance
        new_obs["turn_type"] = "Proposal"
        return new_obs
    
    @staticmethod
    def parse_with_sep(content, sep):
        sep, keepin = sep
        results = []
        for c in [content]:
            index = c.rindex(sep)
            if index >=0:
                if keepin:
                    results.append(c[index:])
                else:
                    results.append(c[index+len(sep):])
        return results[0]
    
    def direct_modeling(self, observations, name):
        # query_list = []
        # env_name = observations['env_name']
        # system_prompt = construct_system_prompt(env_name)
        # observation_prompt = construct_observation_prompt(
        #     observations, env_name)
        # step_instruct = construct_direct_step_prompt(observations)
        # step_prompt = step_instruct['prompt']
        # observation_prompt = observation_prompt + '\n' + step_prompt
        # regex = step_instruct['regex']

        # msgs = self.construct_init_messages(
        #     system_prompt, observation_prompt)

        # responses, query = self.llm_query(
        #     msgs, n=self.num_generations, stop=None, prompt_type='move')
        # query_list.append(query)

        # # print(f'Prompt: {observation_prompt}')
        # # print(f'Response: {responses}')

        # moves = self.parse_with_regex(responses, regex)
        # if len(moves) != 0:
        #     move = self.post_processing(moves, majority_vote=False)
        # else:
        #     move = ""

        # return move
        first_hand = self.name=="Alex"
        my_bidding=observations["self_moves"]
        opponent_bidding=observations["opponent_moves"]
        value = observations["self_value_vector"]
        message = [{
            "role": "system",
            "content": f"You are {name} and involved in a negotiation. "+self.GAME_SETTING
        }]

        def get_state_prompt(value, begining=False):
            if begining:
                stage_prompt="The current round is the first one, and it is your turn to present a new proposal"
            else:
                stage_prompt="Now, you are in the Proposal stage"
            item_prompt=self.item_pool_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
            proposal_prompt=self.proposal_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
            value_prompt=self.value_prompt.format(v1=value[0], v2=value[1], v3=value[2])
            return self.state_prompt.format(name=name, stage_prompt=stage_prompt, item_prompt=item_prompt, value_prompt=value_prompt, proposal_prompt=proposal_prompt)

        for r in range(len(my_bidding)):
            if first_hand:
                if r>0:
                    bidding=opponent_bidding[r-1]
                    message.append({
                        "role": "user",
                        "content": self.opponent_propose_prompt.format(p1=bidding[0], p2=bidding[1], p3=bidding[2])
                    })
            else:
                bidding=opponent_bidding[r]
                message.append({
                    "role": "user",
                    "content": self.opponent_propose_prompt.format(p1=bidding[0], p2=bidding[1], p3=bidding[2])
                })
            message.append({
                "role": "user",
                "content": get_state_prompt(value, first_hand and r==0)+ "\n"+self.PREDICTION_INQUIRY
            })
            message.append({
                "role": "assistant",
                "content": self.PREDICTION_RESPONSE.format(bidding=my_bidding[r])
            })
        
        # Predict the opponent's next move based on their historical information.
        if opponent_bidding:
            message.append({
                "role": "user",
                "content": self.opponent_propose_prompt.format(p1=opponent_bidding[-1][0], p2=opponent_bidding[-1][1], p3=opponent_bidding[-1][2])
            })
        message.append({
            "role": "user",
            "content": get_state_prompt(value)+ "\n"+self.PREDICTION_INQUIRY
        })
        next_bidding = self.llm_query(message)
        message.append({
            "role": "assistant",
            "content": next_bidding
        })
        action = self.parse_result(next_bidding)
        if not action:
            action="agree"
        return action=="agree", action
    
    # def process_response_to_move(self, responses):
    #     regex = '(?:agree|Agree|AGREE)|\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\]'
    #     moves = self.parse_with_regex([responses], regex)
    #     if len(moves) != 0:
    #         move = self.post_processing(moves, majority_vote=False)
    #     else:
    #         move = ""

    #     return move
    
    @staticmethod
    def aggragated_payoff(exp_tree):

                #     "Utterance1":{
        #         "Payoff": "<payoff>",
        #         "Reward": "<normalized payoff number>",
        #         "Probability": "<probability>",
        #         "Utterances":{

        #         }
        #     }

        def beta_aggregate(dist):

            def list_compare(a,b):
                a, b = a[1], b[1]
                min_len=min(len(a),len(b))
                a=a[:min_len]
                b=b[:min_len]
                a_payoff = sum([float(p)*float(i) for p,i in a])
                b_payoff = sum([float(p)*float(i) for p,i in b])

                return a_payoff-b_payoff
                    
            def dfs(tree, payoffs):
                if not tree.get("Proposals", {}):
                    payoff = (tree["Payoff"], tree["Probability"])
                    return None, payoffs+[payoff]
                else:
                    long_payoff = {}
                    for action in tree["Proposals"]:
                        next_action, next_payoffs = dfs(tree["Proposals"][action], payoffs+[(tree["Payoff"], tree["Probability"])])
                        long_payoff[action]=next_payoffs
                    return max(long_payoff.items(), key=cmp_to_key(list_compare))

            action, _ = dfs(dist,[])
            return action
        
        return beta_aggregate({"Proposals":exp_tree, "Payoff": 0, "Probability": 0})
    

    def act(self):
        print('-' * 20 + 'BIDDER Begin' + '-' * 20)
        # we follow the official tot implementation: https://github.com/princeton-nlp/tree-of-thought-llm/blob/master/src/tot/methods/bfs.py
        observations = {}
        observations["opponent_moves"]=self.opponent_biddings
        observations["self_moves"]=self.biddings
        observations["self_value_vector"]=self.value
        observations["most_recent_utterance"]=self.opponent_biddings[-1] if self.opponent_biddings else []
        observations["item_pool"]=self.item_pool

        if not observations["opponent_moves"]:
            agree, bidding =  self.direct_modeling(observations, self.name)
            self.biddings.append(bidding)
            print(self.name, ":", bidding)
            print('-' * 20 + 'BIDDER End' + '-' * 20)
            return agree, bidding

        my_valus = self.value
        opponent_values = self._get_infer(observations)

        def explore(obs, step):
            # Propose Actions
            # step_instruct = construct_step_prompt(observations, opponent_values)
            # step_prompt = step_instruct['prompt']

            # x = self.construct_init_messages(system_prompt, step_prompt)
            # utterances = self._get_samples(x) 
            # query_list.append(x)
            if step>self.k_level:
                return {}
            print('-' * 20 + f'BIDDER Exploration Step:{step} Begin' + '-' * 20)
            proposals = self._get_samples(obs, opponent_values)

            result = {}

            for proposal in proposals:
                result[proposal["Proposal"]] = proposal
                if self.is_over(proposal["Proposal"]): 
                    continue

                proposal_vector = eval(proposal["Proposal"])
                oppoent_obs = self.to_next_obs(obs, proposal_vector, opponent_values)
                agree, opponent_proposal = self.direct_modeling(oppoent_obs, self.opponent_name)
                if agree: 
                    continue
                
                player_obs = self.to_next_obs(oppoent_obs, opponent_proposal, my_valus)

                result[proposal["Proposal"]]["Proposals"]=explore(player_obs, step+1)
            return result

        payoffs = explore(observations, 1)
        move = self.aggragated_payoff(payoffs)
        action = self.parse_result(move)
        if not action:
            action="agree"
        self.biddings.append(action)
        print(self.name, ":", action)
        print('-' * 20 + 'BIDDER End' + '-' * 20)

        return action=="agree", action

        # move = self.process_response_to_move(move)

        print('-' * 20 + 'BIDDER End' + '-' * 20)
        return move=="agree", move
    
    def _get_infer(self, observations):
        if not observations["opponent_moves"]:
            return "", []
        infer_instruct = construct_infer_prompt(observations, observations["opponent_moves"]) # TODO

        infer_messages = [{"role":"system","content":infer_instruct['system']}, {"role":"system","content":infer_instruct["prompt"]}]
        opponent_values = self.llm_query(infer_messages)
        # index = opponent_values[0].rindex((infer_instruct["sep"]))
        # return opponent_values[0][index:]
        opponent_values = self.parse_with_sep(opponent_values, infer_instruct["sep"])
        format_values = re.findall("\d+", opponent_values)
        format_values = [int(v) for v in format_values]
        return format_values
    
    def _get_samples(self, observations, opponent_values):
        # print('Thought/Action Prompt:')
        # print(messages[-1]['content'])
        # responses, query = self.llm_query(messages, n=1, stop= None, prompt_type='plan')
        # print('Thought/Action Response:')
        # print(responses)
        # return responses, query

        step_instruct = construct_step_prompt(observations, opponent_values)
        step_prompt = step_instruct['prompt']

        x = [{"role":"system","content":self.GAME_SETTING}, {"role":"system","content":step_prompt}]
        responses = self.llm_query(x)
        responses=responses.replace("\n","")
        utterances=self.parse_with_sep(responses, step_instruct["sep"])
        return json.loads(utterances)


def construct_infer_prompt(observation, events):

    event_logs = []
    for i in range(0,len(events)):
        event_logs.append(
            f"Round {i+1}: <Proposal: {events[i]}>"
        )
    events = "; ".join(event_logs)

    item_pool = observation['item_pool']
    item_pool_prompt = f'There are {item_pool[0]} peppers, {item_pool[1]} strawberries, and {item_pool[2]} cherries in the item pool.'

    system = """As a tactical mastermind, you excel at analyzing opponents' performances in the game of Negotiation and utilizing their behaviors to infer the value of each item to your opponent.
Negotiation Game Rule: Negotiating the division of Peppers, Strawberries, and Cherries with the opponent. Different values these items hold for both you and your opponent. The process is structured into two stages per round: the proposal stage and the utterance stage.\nIn the Proposal stage: you'll determine the division of items you desire. This is expressed as [a, b, c], where 'a' represents the quantity of Peppers, 'b' the quantity of Strawberries, and 'c' the quantity of Cherries you wish to acquire. It's crucial to base this division on the perceived value these items have for you, keeping in mind that the goal is to reach a mutually agreeable solution. 
For each category, you can not take all the items in a category, i.e., you can not Utterance that take all 5 Peppers, 5 Strawberries, or 5 Cherries. Instead, you have to leave at least one item for each category to your opponent.'"""

    prompt = f"""Based on the public information provided below, infer the value of each item to your opponent.

Opponent behavior:
{events}  
Item Pool:
{item_pool_prompt}

Instructions:
1. Consider the players' historical actions in your evaluation.
2. The value is between 0 and 10.

Please provide your evaluation based on the information above.
Output Format:

Evaluation: 
Peppers: <value>
Strawberries: <value>  
Cherries: <value>
    """

    return {
        'system': system,
        'prompt': prompt,
        'sep': ("Evaluation:", False)
    }

def construct_step_prompt(observation, infered_values):
    item_pool = observation['item_pool']
    item_pool_prompt = f'There are {item_pool[0]} peppers, {item_pool[1]} strawberries, and {item_pool[2]} cherries in the item pool.'

    value_vector = observation['self_value_vector']
    value_vector = f'The value of each pepper is {value_vector[0]} for you, each strawberry is {value_vector[1]} for you, ' \
                f'each cherry is {value_vector[2]} for you.'
    
    most_recent_utterance = observation['most_recent_utterance']
    if most_recent_utterance is not None:
        last_utterance_prompt = f'Last time, the proposal of the opponent was to take ' \
                                f'{most_recent_utterance[0]} peppers, {most_recent_utterance[1]} strawberries, ' \
                                f'and {most_recent_utterance[2]} cherries from the item pool.'
    else:
        last_utterance_prompt = ''

    prompt = f"""You are negotiating the division of Peppers, Strawberries, and Cherries with the opponent. Different values these items hold for both you and your opponent. 
Now, you are in the Proposal Stage: you communicate to your opponent what you want, again in the format [a, b, c]. This proposal is your strategic communication and doesn't necessarily have to reflect your actual desires or the proposal you formulated in the first stage. It's a tool for negotiation, potentially used to mislead, bluff, or strategically reveal information to your opponent.
{item_pool_prompt}
{value_vector}
{last_utterance_prompt}

The opponent's evaluation of the value of each item is:
Opponent Value Inference: 
{infered_values}

Instructions:
1. Propose the three Proposals with the largest rewards.
2. If you don't agree with the opponent's proposal, you can propose a new proposal, and the proposal format is: "[a, b, c]".
2. This also includes agreeing if you agree with your opponent's Proposal, , and the proposal format is: "agree".
2. Calculate the Payoff for each Proposal (a number);Calculate the Opponent Payoff for each Proposal (a number); calculate the probability (normalized between 0 and 1) to win the negotiatino (which mean your payoff is greater than opponent), it is necessary to consider the degree of satisfaction the opponent has with the proposal.


Sample Output Format:
Proposals:
[{{
    "Proposal": "<proposal>",
    "Payoff": "<payoff>",
    "OpponentPayoff": "<opponent_payoff>",
    "Probability": "<probability>"
}},
{{
    "Proposal": "<proposal>",
    "Payoff": "<payoff>",
    "Opponent Payoff": "<opponent_payoff>",
    "Probability": "<probability>"
}},
{{
    "Proposal": "<proposal>",
    "Payoff": "<payoff>",
    "Opponent Payoff": "<opponent_payoff>",
    "Probability": "<probability>"
}}
] 
"""

    return {
        'prompt': prompt,
        'sep': ("Proposals:", False)
    }