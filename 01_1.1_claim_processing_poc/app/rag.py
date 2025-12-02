import json

class SimpleRAG:
    def __init__(self, policy_path="policies/policy_snippets.json"):
        self.policies = self._load_policies(policy_path)

    def _load_policies(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Policy file not found at {path}")
            return []

    def retrieve(self, claim_text):
        """
        Naive retrieval: Find policies that share keywords with the claim text.
        In production, you would use Vector Search (Embeddings).
        """
        claim_words = set(claim_text.lower().split())
        relevant_policies = []

        for policy in self.policies:
            # Check if any keyword from the policy metadata is in the claim text
            # Or simple word overlap
            policy_text = policy.get('text', '').lower()
            keywords = policy.get('keywords', [])
            
            # Score based on keyword matches
            score = 0
            for kw in keywords:
                if kw.lower() in claim_text.lower():
                    score += 1
            
            if score > 0:
                relevant_policies.append((score, policy['text']))

        # Sort by score (relevance) and return top 3 text snippets
        relevant_policies.sort(key=lambda x: x[0], reverse=True)
        return "\n\n".join([p[1] for p in relevant_policies[:3]])

