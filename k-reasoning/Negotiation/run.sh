# python main.py  --player_strategy agent --computer_strategy agent --exp_num 10 --max_round 10
# python main.py  --player_strategy cot --computer_strategy agent --exp_num 10 --max_round 10
# python main.py  --player_strategy persona --computer_strategy agent --exp_num 1 --max_round 10
# python main.py  --player_strategy reflect --computer_strategy agent --exp_num 1 --max_round 10
agents="bidder"
opponents="agent cot reflect"

for i in {1..100}
do
  for agent in $agents
    do
        for oppo in $opponents
        do  
            python main.py  --player_strategy $agent --computer_strategy $oppo --exp_num ${i} --start_exp $((i - 1)) --max_round 10
            python main.py  --player_strategy $oppo --computer_strategy $agent --exp_num ${i} --start_exp $((i - 1)) --max_round 10 
        done
    done
done
