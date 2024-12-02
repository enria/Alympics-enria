cd sotopia 
# # python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark --models direct@gpt-4o-0513 --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 --batch-size 1 --push-to-db
# # python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark --models cot@gpt-4o-0513 --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 --batch-size 1 --push-to-db
# python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark --models refine@gpt-4o-0513 --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 --batch-size 1 --push-to-db

# methods="direct cot refine kr"
methods="kr"

for method in $methods; do
    python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark \
          --models $method'@together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo' \
          --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 \
          --batch-size 1 --push-to-db 
done

# methods="direct cot refine kr"

# for method in $methods; do
#     python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark \
#           --models $method'@together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo' \
#           --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 \
#           --batch-size 1 --push-to-db --only-show-performance
# done

# methods="kr"

# for method in $methods; do
#     python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark \
#           --models $method'@together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo' \
#           --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 \
#           --batch-size 1 --push-to-db  
# done

# methods="kr"

# for method in $methods; do
#     python /home/v-yadzhang/software/miniconda3/envs/agent/bin/sotopia benchmark \
#           --models $method'@openrouter/meta-llama/llama-3.1-405b-instruct' \
#           --partner-model gpt-4o-0513 --evaluator-model gpt-4o-0513 \
#           --batch-size 1 --push-to-db  
# done