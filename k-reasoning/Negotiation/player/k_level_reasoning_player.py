import time
from copy import deepcopy
from openai import BadRequestError


from .reasoning_player import AgentPlayer

round_number = round

class KLevelReasoningPlayer(AgentPlayer):
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

    def start_round(self, round, begining):
        prediction = self.predict(round, begining)
        if not prediction:
            query = self.INQUIRY_COT
        else:
            round_simulated_msg=self.PREDICTION_SUMMARY.format(my=prediction[self.name], opponent=prediction[self.opponent_name] if prediction[self.opponent_name]=="agree" else "propose "+str(prediction[self.opponent_name]))
            query = self.INQUIRY_KR.format(prediction=round_simulated_msg)

        self.message += [{"role":"user","content":self.get_state_prompt(begining)+ "\n" + query}]
    
    def notice_round_result(self, round, bidding_info, history_biddings):
        super().notice_round_result(round, bidding_info, history_biddings)
        self.opponent_biddings = [biddings for player, biddings in history_biddings.items() if player!=self.name][0]

    def predict(self, round, begining=False):
        def self_act(message):
            window_message = message
            if self.client.model.startswith("meta-llama"):
                window = [0]
                window +=list(range(max(1, len(message)-4*6-1),len(message))) # 4 for window, 6 for round
                window_message = [message[i] for i in window]
            status = 0
            while status != 1:
                try:
                    response = self.client.chat_completion(window_message)
                    status = 1

                except BadRequestError as e:
                    print(e)
                    raise e
                except Exception as e:
                    print(e)
                    time.sleep(15)
            return self.parse_result(response)

        def get_opponent_state_prompt(begining=False):
            if begining:
                stage_prompt="The current round is the first one, and it is your turn to present a new proposal"
            else:
                stage_prompt="Now, you are in the Proposal stage"
            item_prompt=self.item_pool_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
            proposal_prompt=self.proposal_prompt.format(q1=self.item_pool[0], q2=self.item_pool[1], q3=self.item_pool[2])
            return self.state_prompt.format(name=self.opponent_name, stage_prompt=stage_prompt, item_prompt=item_prompt, value_prompt="", proposal_prompt=proposal_prompt)
        
        opponent_first_hand = self.name!="Alex"
        my_biddings = deepcopy(self.biddings)
        opponent_biddings = deepcopy(self.opponent_biddings)
        self_message = deepcopy(self.message)
        
        prediction = {}
        logs = {}

        for k in range(self.k_level):

            if k==0:
                # Self Simulation
                self_message +=[{"role":"system","content": self.get_state_prompt(begining and k==0)+ "\n"+self.INQUIRY_COT}]
                my_action = self_act(self_message)
            else:
                # Self Simulation
                round_simulated_msg=self.PREDICTION_SUMMARY.format(my=prediction[self.name], opponent=prediction[self.opponent_name] if prediction[self.opponent_name]=="agree" else "propose "+str(prediction[self.opponent_name]))
                query = self.INQUIRY_KR.format(prediction=round_simulated_msg)
                self_message +=[{"role":"system","content": self.get_state_prompt(begining and k==0)+ "\n"+query}]
                my_action=self_act(self_message)
            
            if not my_action:
                break
            
            prediction[self.name]=my_action
            my_biddings.append(my_action)

            print(f"Player {self.name} conduct predict {self.opponent_name}")
            message = [{
                "role": "system",
                "content": f"You are {self.opponent_name} and involved in a negotiation. "+self.GAME_SETTING
            }]

            for r in range(len(opponent_biddings)):

                if opponent_first_hand:
                    if r>0:
                        bidding=my_biddings[r-1]
                        message.append({
                            "role": "user",
                            "content": self.opponent_propose_prompt.format(p1=bidding[0], p2=bidding[1], p3=bidding[2])
                        })
                else:
                    bidding=my_biddings[r]
                    message.append({
                        "role": "user",
                        "content": self.opponent_propose_prompt.format(p1=bidding[0], p2=bidding[1], p3=bidding[2])
                    })
                message.append({
                    "role": "user",
                    "content": get_opponent_state_prompt(opponent_first_hand and r==0)+ "\n"+self.PREDICTION_INQUIRY
                })
                message.append({
                    "role": "assistant",
                    "content": self.PREDICTION_RESPONSE.format(bidding=opponent_biddings[r])
                })
            
            # Predict the opponent's next move based on their historical information.
            message.append({
                "role": "user",
                "content": self.opponent_propose_prompt.format(p1=my_biddings[-1][0], p2=my_biddings[-1][1], p3=my_biddings[-1][2])
            })
            message.append({
                "role": "user",
                "content": get_opponent_state_prompt()+ "\n"+self.PREDICTION_INQUIRY
            })
            next_bidding = self.agent_simulate(message)
            message.append({
                "role": "assistant",
                "content": next_bidding
            })
            opponent_action = self.parse_result(next_bidding)
            prediction[self.opponent_name] = "agree" if not opponent_action else opponent_action
            logs[self.opponent_name ] = message

            if k==self.k_level-2: break

        self.logs[f"round{round}"] = {
            "prediction": prediction,
            "logs": logs
        }
        return prediction
    
    # @staticmethod
    def agent_simulate(self, message):
        window_message = message
        if self.client.model.startswith("meta-llama"):
            window = [0]
            window +=list(range(max(1, len(message)-4*6-1),len(message))) # 4 for window, 6 for round
            window_message = [message[i] for i in window]
        while 1:
            try:
                response = self.client.chat_completion(window_message)
                return response
            except Exception as e:
                print(e)
                time.sleep(15)


