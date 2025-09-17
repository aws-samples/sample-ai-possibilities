
import re
from langfuse import Langfuse
import openai

from langfuse import observe
from langfuse import get_client
import os
from datetime import datetime
from langfuse import Langfuse
from datetime import datetime, timedelta
import os
import math
import openai
from langchain.evaluation import load_evaluator
from langchain_openai import ChatOpenAI
from langchain.evaluation import EvaluatorType
import json, sys

local_public_key = os.environ["LANGFUSE_PUBLIC_KEY"]
local_secret_key = os.environ["LANGFUSE_SECRET_KEY"]
langfuse_url = os.environ["LANGFUSE_HOST"]

judge_model_url = os.environ["JUDGE_MODEL_GATEWAY_URL"]
judge_model_key = os.environ["JUDGE_MODEL_KEY"]

judge_model = "bedrock-llama-32"

llm = ChatOpenAI( model=judge_model, temperature=0, 
                   api_key=judge_model_key, base_url=judge_model_url)

langfuse = Langfuse(
    secret_key=local_secret_key,
    public_key=local_public_key,
    host=langfuse_url
)




def conciseness_evaluation(user_input, user_output) -> str:
    evaluator = load_evaluator(EvaluatorType.CRITERIA, criteria="conciseness", llm=llm,)
    eval_result2 = evaluator.evaluate_strings(
        input=user_input,
        prediction=user_output,
    )
    print(json.dumps(eval_result2, indent=2, default=str))  
    
    return eval_result2['value']





def harmfulness_evaluation(user_input, user_output) -> str:
    evaluator = load_evaluator(EvaluatorType.CRITERIA, criteria="harmfulness", llm=llm,)
    eval_result2 = evaluator.evaluate_strings(
        input=user_input,
        prediction=user_output,
    )
    print("HARMFULNESS EVALUATION (Potentially Harmful Response):")
    print(json.dumps(eval_result2, indent=2, default=str))  
    
    return eval_result2['value']

BATCH_SIZE=10

now = datetime.now()
five_pm_today = datetime(now.year, now.month, now.day, 17, 0)
ten_days = five_pm_today - timedelta(days=10)


# Use the correct API structure for langfuse 3.x
try:
    # Try different possible method names
    traces_response = langfuse.api.trace.list(
        page=1,
        limit=BATCH_SIZE,
        from_timestamp=ten_days,
        to_timestamp=datetime.now()
    )
    traces_batch = traces_response.data if hasattr(traces_response, 'data') else traces_response
    
except Exception as e:
    print(f"Error accessing traces: {e}")
    print(f"Error type: {type(e)}")
    exit(1)

print(f"Traces in first batch: {len(traces_batch)}")

for trace in traces_batch:
    print(f"Processing {trace.name}")

    if trace.output is None:
        print(f"Warning: \n Trace {trace.name} had no generated output, \
        it was skipped")
        continue
    
    print(trace)
    
    
    input_text = trace.input['messages'][0]['content'][0]['text']
    print(input_text)
    
    
    output_text = trace.output['content']    
    print(output_text)

    
    
    langfuse.create_score(
        trace_id=trace.id,
        name="harmfulness_evaluation",
        value=harmfulness_evaluation(input_text, output_text),
    )

    langfuse.create_score(
        trace_id=trace.id,
        name="conciseness_evaluation",
        value=conciseness_evaluation(input_text, output_text),
    )

    
    exit(0)






