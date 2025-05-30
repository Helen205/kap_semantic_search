prompt = """
Query {query}

You are an expert in KAP (Public Disclosure Platform) data. Your task is to analyze the query and match it with the correct data type and context. 
There are two main categories:

1. "financial statement": Related to numerical or structured financial data such as income, profit/loss, balance sheet items, financial ratios.
2. "general KAP statement": Related to text-based disclosures such as audit opinions, board decisions, risk factors, strategies, management discussions.

Your job is to:
- Identify the query's intention (is it asking for a number, a textual opinion, a date, etc.)
- Extract the key elements of the query: company name, keywords, expected answer type
- Determine whether the query relates to financial figures or textual KAP disclosures

Examples of general KAP statement queries:
- “What was the audit opinion in 2025 Q1 for company X?”
- “Did the board approve dividends in 2024?”
- “What are the key risks mentioned in the report?”

Examples of financial statement queries:
- “What is the net profit of company Y in 2023?”
- “Total assets in 2024 Q4?”

Return ONLY the following JSON format:

{{
    "query_type": "financial statement" or "general KAP statement",
    "args": {{
        "query": "original query",
        "company": "company name",
        "keywords": ["key", "words"],
        "required_operations": ["sum", "subtraction"]
    }}
}}
"""
