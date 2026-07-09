JUDGE_PROMPT = """
        You are a senior AI evaluator.
        
        The first evaluator was uncertain.
        
        User Query:
        {query}
        
        Response A:
        {response_a}
        
        Response B:
        {response_b}
        
        Evaluator Decision:
        Winner: {winner}
        Score A: {score_a}
        Score B: {score_b}
        Confidence: {confidence}
        Reason: {reason}
        
        Review both responses carefully.
        
        Either agree with the evaluator or override the decision.
        If you are still uncertain, provide feedback (in the reason field) for the evaluator to reconsider and set is_resolved to false.
        

        Return ONLY valid JSON matching this exact structure:
        
        {{
        "is_resolved": true,
        "winner": "A",
        "confidence": 0.95,
        "reason": "..."
        }}
        """


EVALUATOR_PROMPT = """
        You are an expert LLM evaluator.
        
        Compare the following two responses.
        
        User Question:
        {query}
        
        Response A:
        {response_a}
        
        Response B:
        {response_b}
        
        Evaluate on
        
        - Accuracy
        - Completeness
        - Helpfulness
        - Reasoning
        - Hallucination
        
        CRITICAL INSTRUCTIONS FOR CONFIDENCE SCORING:
        Be extremely strict and highly critical. Do NOT default to high confidence.
        If both responses are similar in quality, or if you have ANY hesitation, you MUST assign a confidence score below 0.80.
        Only assign a confidence score of 0.80 or higher if one response is objectively, significantly, and undeniably superior to the other.
        
        Return ONLY valid JSON.
        
        {{
        "winner":"A",
        "score_a":8.5,
        "score_b":7.9,
        "confidence":0.87,
        "reason":"..."
        }}
        """