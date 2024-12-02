from copy import deepcopy
from rlcard.utils import print_card
from rlcard.utils.utils import elegent_form
import autogen

from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import autogen

class PokerState(object):
    action_prompte = """The current state is:
1. The Public Card is {public_card}, and your hand is {hand}.
2. You have bet {my_bid} chip, and the opponent has bet {oppo_bid} chip.
You can choose one of the following actions: {actions}."""
    def __init__(self, env) -> None:
        self.env = env
        self.state = {}
    
    def change_state(self, state):
        self.state.clear()
        for key, value in state.items():
            self.state[key] = deepcopy(value)
    
    def game_state_msg(self):
        state = self.state["raw_obs"]
        def card_string(cs):
            if cs:
                return ", ".join([elegent_form(c) for c in cs])
            else:
                return "not available"

        current_player_bid = state["my_chips"]
        current_player_id = state["all_chips"].index(current_player_bid)
        opponent_bid = [bid for i,bid in enumerate(state["all_chips"]) if i!=current_player_id]

        return self.action_prompte.format(
            public_card=card_string(state["public_cards"]),
            hand=card_string(state["hand"]),
            my_bid=current_player_bid,
            oppo_bid=opponent_bid[0],
            actions = ", ".join(state["legal_actions"])
        )
    
    def decode_action(self, action):
        return self.env._decode_action(action)

class JudgerAgent(autogen.AssistantAgent):
    sys_msg = """You are an AI-powered Poker Judger.
You translate the user's natural language input into legal Poker moves.
You should only reply with a Poker action string extracted from the user's input.
Action can only be one of the following four:"raise","fold","check","call" """

    action_prompte = """The current state is:
1. The Public Card is {public_card}, and your hand is {hand}.
2. You have bet {my_bid} chip, and the Opponent has bet {oppo_bid} chip.
You can choose one of the following actions: {actions}."""
    correct_move_messages: Dict[autogen.Agent, List[Dict]]
    state: PokerState

    def __init__(self, env):
        super().__init__(
            name="Judger",
            system_message=self.sys_msg,
            llm_config={"temperature": 0.0, 
                        "config_list": autogen.config_list_from_json("OAI_CONFIG_LIST")},
            max_consecutive_auto_reply=3,
        )
        self.register_reply(autogen.ConversableAgent, JudgerAgent._generate_judger_reply)
        self.env = env
        
        self.state = PokerState(env)
        self._current_player_id = None
        self.correct_move_messages = defaultdict(list)

    
    def start_game(self, agents):
        print(">> Start a new game")
        self.env.default_game_config = { 'game_num_players': len(agents)}
        self.env.set_agents([agent.engine for agent in agents])
        self.correct_move_messages = defaultdict(list)

        state, player_id = self.env.reset()
        self.state.change_state(state)
        self._current_player_id = player_id

        # Loop to play the game
        while not self.env.is_over():
            # Agent plays
            self.initiate_chat(agents[self._current_player_id], message="Your turn. ")

        # Add a final state to all the players
        # for player_id in range(self.num_players):
        #     state = self.env.get_state(player_id)

        # Payoffs
        payoffs = self.env.get_payoffs()

        print('===============     Community Card    ===============')
        print_card(self.env.get_perfect_information()['public_card'])

        for i in range(len(agents)):
            # Let's take a look at what the agent card is
            print(f'===============     {agents[i].name} Hand Card    ===============')
            print_card(self.env.get_perfect_information()['hand_cards'][i])

        win_player_id = -1
        print('===============     Result     ===============')
        for i in range(len(agents)):
            payoff_message = ""
            if payoffs[i] > 0:
                payoff_message = 'Game Over: You win {} chips!'.format(payoffs[i])
                win_player_id = i
            elif payoffs[i] == 0:
                payoff_message = 'Game Over: It is a tie.'
            else:
                payoff_message ='Game Over: You lose {} chips!'.format(-payoffs[i])
            
            agents[i].add_payoff(payoffs[i])
            self.initiate_chat(agents[i], message=payoff_message)
        return win_player_id, payoffs

    def _generate_judger_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        config: Optional[Any] = None,
    ) -> Union[str, Dict, None]:
        message = messages[-1]
        if message["content"] in self.state.state["raw_legal_actions"]:
            action = message["content"]
        else:
            # extract a Poker move from player's message
            action = self.generate_reply(
                [message], sender, exclude=[JudgerAgent._generate_judger_reply]
            )

        if action not in self.state.state["raw_legal_actions"]:
            print(f"Error: {action}")
            return True, f"Error: {action}"
        else:
            state, self._current_player_id = self.env.step(action, raw_action=True)
            self.state.change_state(state)
            return True, None