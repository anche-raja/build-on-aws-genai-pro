import time
from model_invoker import ModelInvoker

class Validator:
    def __init__(self):
        self.invoker = ModelInvoker()

    def validate_with_models(self, document_text, extraction_goal, models=['amazon.nova-micro-v1:0', 'amazon.nova-lite-v1:0']):
        """
        Validates the extraction quality by running the same prompt against multiple models
        and comparing their outputs.
        """
        results = {}
        
        for model in models:
            start_time = time.time()
            
            try:
                output = self.invoker.invoke_text(
                    prompt_text=f"{extraction_goal}\n\nDocument:\n{document_text}",
                    model_id=model,
                    max_tokens=1000,
                    temperature=0.0
                )
                
                # Calculate metrics
                elapsed_time = time.time() - start_time
                
                results[model] = {
                    "status": "success",
                    "time_seconds": round(elapsed_time, 3),
                    "output_length": len(output),
                    "output": output
                }
                
            except Exception as e:
                results[model] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results

    def consensus_check(self, results):
        """
        Simple check to see if models returned similar length outputs (naive consensus).
        In production, you might use embeddings to check semantic similarity.
        """
        successful_outputs = [r['output_length'] for r in results.values() if r['status'] == 'success']
        
        if not successful_outputs:
            return "No successful model runs."
            
        avg_length = sum(successful_outputs) / len(successful_outputs)
        # Check if any output deviates significantly from average length
        deviations = [abs(l - avg_length) for l in successful_outputs]
        max_deviation = max(deviations) if deviations else 0
        
        if max_deviation > (avg_length * 0.2): # 20% tolerance
            return "Warning: Models produced significantly different output lengths."
        
        return "Consensus: Models produced similar output lengths."

