"""User prompt templates for the Arithmetic plugin.

Placeholders: {expression}, {examples}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": (
            "Given the mathematical expression: {expression}\n\n"
            "Follow these EXACT steps:\n"
            "1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)\n"
            "2. Calculate each sub-expression step by step\n"
            "3. Show your work for every intermediate calculation\n"
            "4. Provide the final numerical result\n\n"
            "Expression: {expression}\n"
            "Step-by-step solution:\n"
            "[Show your work here]\n\n"
            "Final answer: [number only]"
        ),
        "casual": (
            "Hey! Can you solve this math expression for me? "
            "Just work through it step by step.\n"
            "{expression}\n\n"
            "Show me how you get to the answer:\n"
            "[Your work here]\n\n"
            "Final answer: [just the number]"
        ),
        "minimal": "{expression}\n\nAnswer: ",
    },
}
