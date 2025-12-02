import boto3
import json
from prompt_template_manager import PromptTemplateManager
from validator import Validator
from model_invoker import ModelInvoker
from rag import SimpleRAG
import time

# Initialize clients
s3 = boto3.client('s3')
prompt_template_manager = PromptTemplateManager()
validator = Validator()
invoker = ModelInvoker()
rag = SimpleRAG()

def process_document(bucket, key, model_id='amazon.nova-micro-v1:0', validation_models=None):
    # Metrics
    start_time = time.time()
    
    # Defaults
    if validation_models is None:
        validation_models = [model_id, 'amazon.nova-lite-v1:0']

    # Get document from S3
    response = s3.get_object(Bucket=bucket, Key=key)
    document_text = response['Body'].read().decode('utf-8')
    
    # Create prompt for information extraction
    prompt = prompt_template_manager.get_prompt("extract_info", document_text=document_text)
    
    # Invoke Bedrock model
    extracted_info = invoker.invoke_text(
        prompt_text=prompt,
        model_id=model_id,
        max_tokens=1000,
        temperature=0.0
    )
    
    # --- Validation Step ---
    validation_prompt = "Extract key information from this document (Name, Policy, Date, Amount)."
    validation_results = validator.validate_with_models(
        document_text=document_text, 
        extraction_goal=validation_prompt,
        models=validation_models
    )
    consensus_msg = validator.consensus_check(validation_results)
    # -----------------------

    # --- RAG Step ---
    policy_context = rag.retrieve(document_text)
    # ----------------
    
    # Generate summary
    summary_input = f"EXTRACTED DATA:\n{extracted_info}\n\nRELEVANT POLICIES:\n{policy_context}"
    summary_prompt = prompt_template_manager.get_prompt("generate_summary", extracted_info=summary_input)
    
    summary = invoker.invoke_text(
        prompt_text=summary_prompt,
        model_id=model_id,
        max_tokens=500,
        temperature=0.7
    )
    
    # Processing metrics
    total_time = time.time() - start_time
    
    return {
        "file": key, # Added file key for tracking
        "model": model_id, # Added model ID for tracking
        "extracted_info": extracted_info,
        "relevant_policies": policy_context,
        "summary": summary,
        "validation": {
            "consensus": consensus_msg,
            "details": validation_results
        },
        "metrics": {
            "total_processing_time_sec": round(total_time, 2)
        }
    }

def run_batch_test(bucket, files, model_ids):
    results = []
    print(f"Starting batch test on {len(files)} files with {len(model_ids)} models...\n")
    
    # Optimization: S3 is called only once per file inside process_document. 
    # If we wanted to optimize further, we could read S3 once outside the loop.
    
    for file_key in files:
        for model in model_ids:
            print(f"Processing {file_key} with {model}...")
            try:
                # Pass specific validation models if needed, or default to comparing current model vs Lite
                val_models = [model, 'amazon.nova-lite-v1:0']
                result = process_document(bucket, file_key, model_id=model, validation_models=val_models)
                results.append(result)
            except Exception as e:
                print(f"Error processing {file_key} with {model}: {e}")
    
    return results

if __name__ == "__main__":
    # Configuration
    BUCKET = 'claim-documents-poc-ars'
    TEST_FILES = ['claims/claim1.txt', 'claims/claim2.txt']
    MODELS_TO_TEST = ['amazon.nova-micro-v1:0', 'amazon.nova-lite-v1:0']
    
    # Run comparison
    final_results = run_batch_test(BUCKET, TEST_FILES, MODELS_TO_TEST)
    
    # Output detailed report
    print("\n--- FINAL REPORT ---")
    print(json.dumps(final_results, indent=2))
