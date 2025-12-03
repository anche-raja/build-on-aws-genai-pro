import boto3
import json
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime')

# Models to evaluate
models = [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "amazon.titan-text-express-v1"
]

# Test cases with ground truth answers
test_cases = [
    {
        "question": "What is a 401(k) retirement plan?",
        "context": "Financial services",
        "ground_truth": "A 401(k) is a tax-advantaged retirement savings plan offered by employers."
    },
    # Add more test cases...
]

def invoke_model(model_id, prompt, max_tokens=500):
    """Invoke a model with the given prompt and return the response and metrics."""
    start_time = time.time()
    
    # Prepare request body based on model provider
    if "anthropic" in model_id:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    elif "amazon" in model_id:
        body = json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": 0.7,
                "topP": 0.9
            }
        })
    # Add more model providers as needed
    
    try:
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode())
        
        if "anthropic" in model_id:
            output = response_body['content'][0]['text']
        elif "amazon" in model_id:
            output = response_body['results'][0]['outputText']
        
        # Calculate metrics
        latency = time.time() - start_time
        token_count = len(output.split())  # Rough estimate
        
        return {
            "success": True,
            "output": output,
            "latency": latency,
            "token_count": token_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency": time.time() - start_time
        }

def evaluate_models():
    """Evaluate all models on all test cases and return results."""
    results = []
    
    for test_case in test_cases:
        prompt = f"Question: {test_case['question']}\nContext: {test_case['context']}"
        
        for model_id in models:
            print(f"Evaluating {model_id} on: {test_case['question']}")
            response = invoke_model(model_id, prompt)
            
            if response["success"]:
                # Calculate similarity score with ground truth (simplified)
                similarity = calculate_similarity(response["output"], test_case["ground_truth"])
                
                results.append({
                    "model_id": model_id,
                    "question": test_case["question"],
                    "output": response["output"],
                    "latency": response["latency"],
                    "token_count": response["token_count"],
                    "similarity_score": similarity
                })
            else:
                results.append({
                    "model_id": model_id,
                    "question": test_case["question"],
                    "error": response["error"],
                    "latency": response["latency"]
                })
    
    return pd.DataFrame(results)

def calculate_similarity(output, ground_truth):
    """Calculate similarity between model output and ground truth (simplified)."""
    # In a real implementation, use more sophisticated NLP techniques
    # This is a very simplified version
    output_words = set(output.lower().split())
    truth_words = set(ground_truth.lower().split())
    
    if not truth_words:
        return 0.0
        
    common_words = output_words.intersection(truth_words)
    return len(common_words) / len(truth_words)


def create_model_selection_strategy(results_df):
    """Create a model selection strategy based on evaluation results."""
    # Calculate overall scores
    model_scores = results_df.groupby("model_id").agg({
        "latency": "mean",
        "similarity_score": "mean"
    }).reset_index()
    
    # Normalize scores (lower latency is better, higher similarity is better)
    max_latency = model_scores["latency"].max()
    model_scores["latency_score"] = 1 - (model_scores["latency"] / max_latency)
    
    # Calculate weighted score (adjust weights based on priorities)
    model_scores["overall_score"] = (
        0.7 * model_scores["similarity_score"] + 
        0.3 * model_scores["latency_score"]
    )
    
    # Sort by overall score
    model_scores = model_scores.sort_values("overall_score", ascending=False)
    
    # Create strategy
    strategy = {
        "primary_model": model_scores.iloc[0]["model_id"],
        "fallback_models": model_scores.iloc[1:]["model_id"].tolist(),
        "model_scores": model_scores.to_dict(orient="records")
    }
    
    return strategy

# Run evaluation
if __name__ == "__main__":
    import os
    
    # Get directory of this script to determine output location
    # Output to parent directory (01_1.2_resilient_dynamic_routing_system)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.dirname(script_dir)
    
    results_df = evaluate_models()
    
    # Save results to CSV
    csv_path = os.path.join(output_dir, "model_evaluation_results.csv")
    results_df.to_csv(csv_path, index=False)
    print(f"Results saved to: {csv_path}")
    
    # Generate strategy
    strategy = create_model_selection_strategy(results_df)
    print(json.dumps(strategy, indent=2))

    # Save strategy to file for AppConfig
    strategy_path = os.path.join(output_dir, "model_selection_strategy.json")
    with open(strategy_path, "w") as f:
        json.dump(strategy, f, indent=2)
    print(f"Strategy saved to: {strategy_path}")
    
    # Print summary
    print("\nEvaluation Summary:")
    summary = results_df.groupby("model_id").agg({
        "latency": "mean",
        "similarity_score": "mean",
        "token_count": "mean"
    }).reset_index()
    
    print(summary)
