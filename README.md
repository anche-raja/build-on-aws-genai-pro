# Build on AWS GenAI Pro

A collection of Proof of Concepts (PoCs) and hands-on labs designed to help you master the domains of the **AWS Certified Generative AI Developer - Professional** exam.

## Repository Structure

### Domain 1: Fundamentals of Generative AI

*   **[01_1.1_claim_processing_poc](./01_1.1_claim_processing_poc/README.md)**:
    *   **Scenario**: Insurance Claim Processing.
    *   **Skills**: Designing architectures, implementing PoCs, and creating reusable components (Skills 1.1.1 - 1.1.3).
    *   **Tech Stack**: Amazon Bedrock, Python (Boto3), Prompt Engineering, Simple RAG.

*   **[01_1.2_resilient_dynamic_routing_system](./01_1.2_resilient_dynamic_routing_system/README.md)**:
    *   **Scenario**: Resilient Dynamic Routing System.
    *   **Skills**: Model selection, resilient architecture, and continuous evaluation (Skills 1.2.1 - 1.2.3).
    *   **Tech Stack**: Amazon Bedrock, AWS Step Functions, AWS AppConfig, AWS Lambda, Terraform.

### Reference Materials

*   **[pdfs](./pdfs/)**: Contains relevant AWS guides and exam preparation materials.
    *   AWS WA Tool Generative AI Lens
    *   AWS Certified Generative AI Developer Pro Exam Guide
    *   Bedrock User Guide

## Getting Started

1.  **Prerequisites**:
    *   AWS Account with access to Amazon Bedrock models (ensure Nova Micro/Lite are enabled).
    *   Python 3.9+ installed.
    *   AWS CLI configured with appropriate credentials.

2.  **Navigation**:
    *   Go to the specific PoC directory (e.g., `cd 01_1.1_claim_processing_poc`).
    *   Follow the `README.md` instructions in that directory for detailed setup and execution steps.
