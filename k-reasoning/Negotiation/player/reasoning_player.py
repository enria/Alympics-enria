import time
import json
from openai import BadRequestError

from .basic_player import Player


class AgentPlayer(Player):
    is_agent=True
    GAME_SETTING = ("You are a powerful gaming agent who can make proper decisions to beat the user in gaming tasks."
                    "You are one of two players in the game. You cannot directly communicate with another player; you can only tell the host what your proposal is for the other player."
                    "You are negotiating the division of Peppers, Strawberries, and Cherries in the item pool with the opponent. Different values these items hold for both you and your opponent. "
                    "The opponent's proposal is how many items they will take, which means that if you agree to their proposal, you will receive the remaining items from the item pool (i.e., all the items minus the portion taken by the opponent)."
                    "Remember, the key in such negotiations is understanding that your opponent also has their value system for these items, which is unknown to you. Balancing between revealing your true desires and misleading your opponent to gain a favorable outcome is essential. It\'s also important to be adaptive, as the negotiation progresses and you gather more information about your opponent\'s preferences and tactics.")
    
    state_prompt =  ("Ok, {name}! {item_prompt} {value_prompt} {stage_prompt}: you\'ll determine the division of items you desire. This is expressed as [a, b, c], where \'a\' represents the quantity of Peppers, \'b\' the quantity of Strawberries, and \'c\' the quantity of Cherries you wish to acquire. "
               "It\'s crucial to base this division on the perceived value these items have for you, keeping in mind that the goal is to reach a mutually agreeable solution. Additionally, the division proposal you suggested must not exceed the capacity of the item pool. {proposal_prompt}"
               "If you find the proposal raised by the opponent is acceptable, you should output [agree]. Otherwise, you should output your proposal in the format <Proposal: [a, b, c]>.  ")
    
    INQUIRY = ('Just output your decision, don\'t use any other text.')
    
    opponent_propose_prompt = "The opponent propose that he will take {p1} peppers, {p2} strawberries, and {p3} cherries from the item pool."

    item_pool_prompt = 'The item pool is [{q1}, {q2}, {q3}], meaning that there are {q1} peppers, {q2} strawberries, and {q3} cherries in the item pool. '
    proposal_prompt = 'In other words, your proposal needs to satisfy a<={q1}, b<={q2}, d<={q3}. '
    value_prompt = 'The value of each pepper is {v1}, each strawberry is {v2}, and each cherry is {v3} for you.'
    
    def __init__(self, name, persona, client, parse_client=None):
        self.name = name
        self.client = client
        self.item_pool = []
        self.value = []

        self.opponent_propose = []

        self.biddings = []
        self.persona = persona

        self.logs = None

        if parse_client is None:
            self.parse_client = client
        else:
            self.parse_client = parse_client
        
        self.set_system_prompt()
    
    def set_system_prompt(self):
        self.message = [{"role":"system","content": self.persona + self.GAME_SETTING}]

    def set_info(self, item_pool, value):
        self.item_pool=item_pool
        self.value=value
    
    def get_state_prompt(self, begining):
        if begining:
            stage_prompt="The current round is the first one, and it is your turn to present a new proposal"
        else:
            stage_prompt="Now, you are in the Proposal stage"
        item_prompt=self.item_pool_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
        value_prompt=self.value_prompt.format(v1=self.value[0], v2=self.value[1], v3=self.value[2])
        proposal_prompt=self.proposal_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
        return self.state_prompt.format(name=self.name,stage_prompt=stage_prompt, item_prompt=item_prompt, value_prompt=value_prompt, proposal_prompt=proposal_prompt)

    
    @property
    def window_message(self):
        if self.client.model.startswith("meta-llama"):
            window = [0]
            window +=list(range(max(1, len(self.message)-4*6-1),len(self.message))) # 4 for window, 6 for round
            message = [self.message[i] for i in window]
            return message
        else:
            return self.message
        

    def act(self):
        print(f"Player {self.name} conduct bidding")
        status = 0
        while status != 1:
            try:
                response = self.client.chat_completion(messages = self.window_message)
                # response = response.choices[0].message.content
                self.message.append({"role":"assistant","content":response})
                status = 1
            except BadRequestError as e:
                print(e)
                raise e
            except Exception as e:
                print(e)
                time.sleep(15)
        bidding_info = self.parse_result(response)
        if not bidding_info:
            bidding_info="agree"
        self.biddings.append(bidding_info)
        print(self.name, ":", bidding_info)
        return bidding_info=="agree", bidding_info

    def parse_result(self, message):
        if "[" in message:
            start = message.rindex("[")
            end = message.index("]", start)
            response = message[start:end+1]
            if "agree" in response.lower():
                return []
            return json.loads(response)
        else:
            return []

#         status = 0
#         times = 0
#         bidding_info = None
#         while status != 1:
#             try:
#                 response = self.parse_client.chat_completion(messages = [{"role":"system", "content":f"Your are an content parser. By reading the conversation, extract the player's proposal. "},{"role":"system", "content":f"""Player Response: \"\"\" {message}\"\"\"  Please output the result based on the player's response to the opponent's proposal:
# If the player agrees with the opponent's proposal, just output [].
# If the player disagrees, output the player's own proposal in the format [a, b, c]."""}])
#                 assert "[" in response 
#                 response = json.loads(response[response.rindex("["):response.rindex("]")+1])
#                 bidding_info = response
#                 status = 1
#             except AssertionError as e:
#                 print("Result Parsing Error: ",message, "\n",response)
#                 times+=1
#                 if times>=3:
#                     exit()
#             except Exception as e:
#                 print(e, ":: ", response)
#                 time.sleep(10)
#         # 返回结果

#         return bidding_info
    
    def start_round(self, round, begining=False):
        self.message += [{"role":"system","content": self.get_state_prompt(begining)+ "\n"+self.INQUIRY}]
        self.cur_round = round
        
    def notice_round_result(self, round, bidding_info, history_biddings):
        bidding_info = self.opponent_propose_prompt.format(p1=bidding_info[0], p2=bidding_info[1], p3=bidding_info[2])
        self.message += [{"role":"system","content":bidding_info}]
    
    def conduct_inquiry(self, inquiry):
        while 1:
            try:
                response = self.client.chat_completion(messages = self.window_message + [{"role":"system","content":inquiry}])
                return response
            except BadRequestError as e:
                print(e)
                raise e
            except Exception as e:
                print(e)
                time.sleep(15)


class CoTAgentPlayer(AgentPlayer):
    INQUIRY = ("First think step by step, and finalize your response (proposal or agreement).")


class PersonaAgentPlayer(AgentPlayer):
    INQUIRY = ( "Don't forget your expert status, and use your expertise to finalize your response (proposal or agreement).")
                   
    
    MATH_EXPERT_PERSONA = ("You are {name} and involved in a survive challenge."
                   " You are a game expert, good at predicting other people's behavior and deducing calculations, and using the most favorable strategy to win the game.")
    

    def set_system_prompt(self):
        self.message = [{"role":"system","content": self.MATH_EXPERT_PERSONA.format(name=self.name) + self.GAME_SETTING.format(NAME=self.name)}]


class ReflectionAgentPlayer(AgentPlayer):
    REFLECT_INQUIRY = "Review the previous round games, summarize the experience."

    @property
    def window_message(self):
        flag="The opponent propose "
        window=[]
        round_cnt=0
        for i in range(len(self.message)-1, 0, -1):
            window.append(i)
            content = self.message[i]["content"]
            if not content: content=""
            if content.startswith(flag) and self.message[i]["role"]=="system":
                round_cnt+=1
            if round_cnt>=4:
                break
        window=[0]+window[::-1]
        message = [self.message[i] for i in window]
        return message

    def notice_round_result(self, round, bidding_info, history_biddings):
        super().notice_round_result(round, bidding_info, history_biddings)
        # refelxtion after round end
        self.reflect()

    def reflect(self):
        print(f"Player {self.name} conduct reflect")
        self.message += [{"role":"system","content": self.REFLECT_INQUIRY}, {"role":"assistant","content":self.conduct_inquiry(self.REFLECT_INQUIRY)}]  


class SelfRefinePlayer(AgentPlayer):
    INQUIRY = ("First think step by step, and finalize your response (proposal or agreement).")
    
    FEEDBACK_PROMPT = ("Carefully study the user's strategy in this round of the game. As a game expert, can you give a suggestion to optimize the user's strategy ?")
    REFINE_PROMPT = ("I have a game expert's advice on your strategy in this round."
                     "You can adjust your strategy just now according to his suggestion. Here are his suggestions:"
                     "{feedback}\n"
                     "First think step by step, and finalize your response (proposal or agreement).")
    
    
    def __init__(self, name, persona, engine,  refine_times = 2):
        super().__init__(name, persona, engine)

        self.refine_times = refine_times
    
    @property
    def window_message(self):
        try:
            flag="The opponent propose "
            window=[]
            round_cnt=0
            for i in range(len(self.message)-1, 0, -1):
                window.append(i)
                content = self.message[i]["content"]
                if not content: content=""
                if content.startswith(flag) and self.message[i]["role"]=="system":
                    round_cnt+=1
                if round_cnt>=4:
                    break
            window=[0]+window[::-1]
            message = [self.message[i] for i in window]
            return message
        except:
            print()

    def act(self):
        print(f"Player {self.name} conduct bidding")
        def completion(message):
            status = 0
            while status != 1:
                try:
                    response = self.client.chat_completion(messages = message)
                    status = 1
                except BadRequestError as e:
                    print(e)
                    raise e
                except Exception as e:
                    print(e)
                    time.sleep(15)
            return response
        
        for t in range(self.refine_times):
            # refine_times==action_times
            if t>0:
                refine_message = []
                for m in self.message:
                    if m["role"]=="system":
                        refine_message.append(m)
                    else:
                        refine_message.append({
                            "role": "system",
                            "content": m["content"]
                        })
                refine_message.append({
                        "role": "system",
                        "content": self.FEEDBACK_PROMPT
                    })
                feedback = completion(refine_message)
                self.message.append({"role":"system","content": self.REFINE_PROMPT.format(feedback=feedback)})
            self.message.append({"role":"assistant","content": completion(self.window_message)})
        
        bidding_info = self.parse_result(self.message[-1]["content"])
        if not bidding_info:
            bidding_info="agree"
        self.biddings.append(bidding_info)
        print(self.name, ":", bidding_info)
        return bidding_info=="agree", bidding_info


class PredictionCoTAgentPlayer(AgentPlayer):
    INQUIRY_COT = ("First think step by step, and finalize your response (proposal or agreement).")
    INQUIRY_PCOT = ("First of all, predict the next round of choices based on the choices of other players in the previous round. "
                   "{round_history}"
                   "Your output should be of the following format:\n"
                   "Predict:\nThe proposal of opponent in the next round here.\n"
                   "Based on the prediction of other players, first think step by step, and finalize your response (proposal or agreement).")
    
    def __init__(self, name, persona, engine):
        super().__init__(name, persona, engine)

        self.bidding_history = {}

    def start_round(self, round, begining=False):
        # PCoT requires the opponent's historical information to make predictions.
        round_history = []
        for player_name in self.bidding_history:
            if player_name!=self.name:
                bidding_history = self.bidding_history[player_name]
                for r in range(len(bidding_history)):
                    round_history.append(f"Round {r}: {bidding_history[r]}")
        if round_history:
            round_history = ".\n".join(round_history)
            round_history = "The opponent proposals in the previous rounds are as follows:\n"+round_history+"."
            self.message += [{"role":"system","content":self.get_state_prompt(begining) + self.INQUIRY_PCOT.format(round_history=round_history)}]
        else:
            round_history = ""
            self.message += [{"role":"system","content":self.get_state_prompt(begining) + self.INQUIRY_COT}]
        self.cur_round = round
    
    def notice_round_result(self, round, bidding_info, history_biddings):
        super().notice_round_result(round, bidding_info, history_biddings)
        self.bidding_history = history_biddings
