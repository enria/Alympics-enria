import os
import json

from player import *
from game import Negotiation
import autogen

# Fill in your config information to conduct experiments.

class LLMClient:
    # def __init__(self, client, model) -> None:
    #     self.client = client
    #     self.model = model

    def __init__(self, config, model):
        self.client = autogen.ConversableAgent(name="client", llm_config=config, human_input_mode="NEVER")
        self.client._oai_system_message=[]
        self.model = model
        
     
    def chat_completion(self, messages, temperature=0.7, max_tokens=800, top_p=0.95, frequency_penalty=0,  presence_penalty=0, stop=None):

        message = self.client.generate_reply(messages)

        return message

def build_client(model):
    from azure.identity import AzureCliCredential, get_bearer_token_provider
    llm_config = [
    ]
    config =  autogen.filter_config(llm_config,  {"tags": [model]}) # 这里都需要使用列表
    assert len(config) == 1
    config = {
        # "cache_seed": None,
        "temperature": 0.7,
        "config_list": config
    }
    return LLMClient(config, model=model)

def build_player(strategy, name, persona, model, mean=50, std=0, player_names = [], player_k=2):
    """
    Player Factory
    """

    llm_client = build_client(model)

    if strategy=="agent":
        return AgentPlayer(name, persona, llm_client)
    elif strategy=="cot":
        return CoTAgentPlayer(name, persona, llm_client)
    elif strategy=="persona":
        return PersonaAgentPlayer(name, persona, llm_client)
    elif strategy=="reflect":
        return ReflectionAgentPlayer(name, persona, llm_client)
    elif strategy=="refine":
        return SelfRefinePlayer(name, persona, llm_client)
    elif strategy=="pcot":
        return PredictionCoTAgentPlayer(name, persona, llm_client)
    elif strategy=="kr":
        return KLevelReasoningPlayer(name, persona, llm_client, player_names, player_k=player_k)
    elif strategy=="bidder":
        return BIDDERPlayer(name, persona, llm_client, player_names, player_k=player_k)
    elif strategy in ["fix", "last", "mono", "monorand"]:
        return ProgramPlayer(name, strategy, mean, std)
    else:
        raise NotImplementedError


def main(args):
    #Predefined Persona information
    PERSONA_A = "You are Alex and involved in a negotiation. "
    PERSONA_B = "You are Bob and involved in a negotiation. "

    for exp_no in range(args.start_exp, args.exp_num):
        players=[]
        player_names = ["Alex", "Bob"]

        # build player
        A = build_player(args.player_strategy, "Alex", PERSONA_A, args.player_model, player_names=player_names, player_k=args.player_k)
        # Modify PlayerA's settings for ablation experiments.
        # if args.player_engine: A.engine = args.player_engine
        if args.player_k:  A.k_level = args.player_k
        players.append(A)

        # build opponent
        for program_name, persona in [("Bob", PERSONA_B)]:
            players.append(build_player(args.computer_strategy, program_name, persona, args.computer_model, args.init_mean, args.norm_std, player_names=player_names, player_k=args.computer_k))

        # run multi-round game (default 10)
        Game = Negotiation(players, seed=1000+exp_no)
        Game.run_multi_round(args.max_round)

        # export game records

        def format_kr(strategy, k):
            if strategy in ["kr", "bidder"] and k!=1:
                return f"{strategy}-{k}"
            return strategy

        prefix = f"{format_kr(args.player_strategy, args.player_k)}" \
            + "_VS_" + \
            format_kr(args.computer_strategy, args.computer_k) \
            + f"_{exp_no}"

        output_file = f"{args.output_dir}/{prefix}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file,"w") as fout:
            messages = {}
            biddings = {}
            logs = {}
            for agent in Game.all_players:
                if agent.is_agent:
                     messages[agent.name] = agent.message
                biddings[agent.name] = agent.biddings
                if agent.logs:
                    logs[agent.name] = agent.logs

            debug_info = {
                "setting": Game.setting,
                "winners": Game.result,
                "biddings": biddings,
                "message": messages,
                "logs":logs
            }

            json.dump(debug_info, fout, indent=4)

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--player_strategy', type=str, default="cot", choices=["agent","cot","pcot","kr","reflect", "persona", "refine", "spp","bidder"])
    parser.add_argument('--computer_strategy', type=str,choices=["agent", "fix", "last", "mono", "monorand","cot","pcot","kr","reflect", "persona", "refine", "spp","bidder"], default="fix")
    parser.add_argument("--output_dir", type=str, default="result")
    parser.add_argument("--init_mean", type=int, default=40, help="init mean value for computer player")
    parser.add_argument("--norm_std", type=int, default=5, help="standard deviation of the random distribution of computer gamers")
    parser.add_argument('--max_round', type=int, default=10)
    parser.add_argument('--start_exp', type=int, default=0)
    parser.add_argument('--exp_num', type=int, default=10)
    parser.add_argument('--player_model', type=str, default="gpt4", help="player's OpenAI api engine", 
                        choices=["gpt35prod", "gpt4", "meta-llama/Llama-2-7b-chat-hf"])
    parser.add_argument('--computer_model', type=str, default="gpt4", help="player's OpenAI api engine", 
                        choices=["gpt35prod", "gpt4", "meta-llama/Llama-2-7b-chat-hf"])
    parser.add_argument('--player_k', type=int, default=2, help="player's k-level (default 2)")
    parser.add_argument('--computer_k', type=int, default=2, help="opponent's k-level (default 2)")

    args = parser.parse_args()
    main(args)