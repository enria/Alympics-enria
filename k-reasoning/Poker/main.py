import os
import json

import rlcard
from rlcard import models
from rlcard.agents import LeducholdemHumanAgent as HumanAgent


from player import *
from game import JudgerAgent


# Fill in your config information to conduct experiments.
import os, json
os.environ["OAI_CONFIG_LIST"] = json.dumps([{
    "model": "gpt-4-latest",
    "api_key": os.getenv("MTUTOR_TURBO_OPENAI_API_KEY"),
    "api_type": "azure",
    "base_url": "https://mtutor-experiment-frcentral2.openai.azure.com/",
    "api_version": "2023-07-01-preview",
}])

llm_config = {"temperature": 0.0, "config_list": autogen.config_list_from_json("OAI_CONFIG_LIST")}

def build_player(judger, strategy, name, k_level, max_turn=10):
    """
    Player Factory
    """

    if strategy=="agent":
        return PokerPlayerAgent(
            name=name,
            engine=HumanAgent(judger.env.num_actions),
            judger_agent=judger,
            max_turns=max_turn,
            llm_config=llm_config
        )
    elif strategy=="cot":
        return CoTPlayerAgent(
            name=name,
            engine=HumanAgent(judger.env.num_actions),
            judger_agent=judger,
            max_turns=max_turn,
            llm_config=llm_config
        )
    elif strategy=="user":
        return UserAgent(
            name=name,
            engine=HumanAgent(judger.env.num_actions),
            judger_agent=judger,
            max_turns=max_turn,
            llm_config=llm_config
        )
    elif strategy=="rule":
        return RuleAgent(
            name=name,
            engine=models.load('limit-holdem-rule-v1').agents[0],
            judger_agent=judger,
            max_turns=max_turn,
            llm_config=False,
        )
    else:
        raise NotImplementedError


def main(args):
    # Predefined character information
    Player_names = ["Alex", "Bob", "Cindy", "David", "Eric", "Frank"]
    
    for exp_no in range(args.start_exp, args.exp_num):
        env = rlcard.make('limit-holdem', { 'game_num_players': len(args.computer_strategy)+1})
        judger_agent = JudgerAgent(env=env)
        players = []

        # build player
        A = build_player(judger_agent, args.player_strategy, Player_names[0], args.player_k)
        players.append(A)

        # build opponent
        for program_name, strategy in zip(Player_names[1:], args.computer_strategy):
            players.append(build_player(judger_agent, strategy, program_name, args.computer_k))
        print("Initial players done.")

        # for i in range(5):
        win_player_id, payoffs = judger_agent.start_game(agents=players)

        # Export game records
        prefix = f"{args.player_strategy}_VS_{'+'.join(args.computer_strategy)}_{exp_no}"
        output_file = f"{args.output_dir}/{prefix}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file,"w") as fout:
            messages = {}

            for agent in players:
                if not hasattr(agent, "logs"): continue
                messages[agent.name] = agent.logs

            debug_info = {
                "winner": players[win_player_id].name,
                "payoffs": {player.name:payoff for player, payoff in zip(players, payoffs)},
                "message": messages
            }

            json.dump(debug_info, fout, indent=4, ensure_ascii=False)

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--player_strategy', type=str, default="agent", choices=["agent","cot","pcot","kr","reflect","tot", "persona", "refine", "spp"])
    parser.add_argument('--computer_strategy', type=str, default="agent")
    parser.add_argument("--output_dir", type=str, default="result")
    parser.add_argument('--start_exp', type=int, default=0)
    parser.add_argument('--exp_num', type=int, default=1)
    parser.add_argument('--player_engine', type=str, default=None, help="player's OpenAI api engine")
    parser.add_argument('--player_k', type=int, default=2, help="player's k-level (default 2)")
    parser.add_argument('--computer_k', type=int, default=2, help="computer's k-level (default 2)")

    args = parser.parse_args()
    args.computer_strategy = args.computer_strategy.split(",")
    main(args)