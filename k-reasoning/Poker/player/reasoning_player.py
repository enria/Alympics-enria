from typing import Any, Dict, List, Optional, Union
import autogen

# from ..game import JudgerAgent, PokerState

sys_msg_tmpl = """You are {name} and you are a Leduc Hold’em player.
Texas Hold’em is a popular betting game. 
Each player is dealt two face-down cards, called hole cards. 
Then 5 community cards are dealt in three stages (the flop, the turn and the river). 
Each player seeks the five best cards among the hole cards and community cards. 
There are 4 betting rounds. 
During each round each player can choose “call”, “check”, “raise”, or “fold”."""


class PokerPlayerAgent(autogen.AssistantAgent):
    query_msg = "Just give me your action."

    def __init__(
        self,
        name,
        engine,
        judger_agent,
        max_turns: int,
        **kwargs,
    ):
        sys_msg = sys_msg_tmpl.format(
            name=name,
        )
        super().__init__(
            name=name,
            system_message=sys_msg,
            max_consecutive_auto_reply=max_turns,
            **kwargs,
        )
        self.register_reply(type(judger_agent), PokerPlayerAgent._generate_reply_for_judger, config=judger_agent.state)

        self.last_state_message = ""
        self.engine = engine

        self.payoffs = []
        self.logs = []
    
    def add_payoff(self, payoff):
        self.payoffs.append(payoff)

    def _generate_reply_for_judger(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        # config: Optional[PokerState] = None,
        config = None
    ) -> Union[str, Dict, None]:
        state_msg = config.game_state_msg()
        # add a system message about the current state of the board.
        board_state_msg = [{"role": "system", "content": f"{state_msg}\n{self.query_msg}"}]
        last_message = messages[-1]
        if last_message["content"].startswith("Error") or last_message["content"].startswith("Your turn"):
            message = self.generate_reply(
                messages + board_state_msg, sender, exclude=[PokerPlayerAgent._generate_reply_for_judger]
            )
            if message is None:
                return True, None
            self.logs.extend(board_state_msg+[{"role": "assistant", "content": message}])
            return True, message
        elif last_message["content"].startswith("Game Over"):
            return True, None
        else:
            return True, None

class CoTPlayerAgent(PokerPlayerAgent):
    query_msg = "Let's think step by step, which action would bring the maximum benefit (or minimize the loss)."