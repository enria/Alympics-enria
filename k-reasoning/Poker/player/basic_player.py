from typing import Any, Dict, List, Optional, Union

import autogen
# from ..game import JudgerAgent, PokerState

class RuleAgent(autogen.AssistantAgent):
    def __init__(
        self,
        name,
        engine,
        judger_agent,
        max_turns: int,
        **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_turns,
            **kwargs,
        )
        self.register_reply(type(judger_agent), RuleAgent._generate_reply_for_judger, config=judger_agent.state)
        self.engine = engine

        self.payoffs = []
    
    def add_payoff(self, payoff):
        self.payoffs.append(payoff)

    def _generate_reply_for_judger(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[autogen.Agent] = None,
        # config: Optional[PokerState] = None,
        config = None,
    ) -> Union[str, Dict, None]:
        last_message = messages[-1]
        if last_message["content"].startswith("Error"):
            return True, None
        elif last_message["content"].startswith("Your turn"):
            state = config.state
            action, _ = self.engine.eval_step(state)
            return True, action
        elif last_message["content"].startswith("Game Over"):
            return True, None
        else:
            return True, None

class UserAgent(autogen.UserProxyAgent):
    def __init__(
        self,
        name,
        engine,
        judger_agent,
        max_turns: int,
        **kwargs,
    ):
        super().__init__(
            name=name,
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=max_turns,
            code_execution_config=False,
            **kwargs,
        )
        self.register_reply(type(judger_agent), UserAgent._generate_reply_for_judger, config=judger_agent.state)
        self.engine = engine

        self.payoffs = []
    
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
        last_message = messages[-1]
        if last_message["content"].startswith("Error") or last_message["content"].startswith("Your turn"):
            message = self.get_human_input(state_msg)
            if message is None:
                return True, None
            return True, message
        elif last_message["content"].startswith("Game Over"):
            return True, None
        else:
            return True, None