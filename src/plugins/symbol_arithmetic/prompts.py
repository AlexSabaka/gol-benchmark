"""User prompt templates for the Symbol Arithmetic plugin.

Placeholders: {operation_table}, {expression}, {operator_symbol}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": (
            "A custom binary operation {operator_symbol} is defined on the set "
            "{{{symbol_set}}} by the following table:\n\n"
            "{operation_table}\n\n"
            "Evaluate: {expression}\n\n"
            "Answer: "
        ),
        "casual": (
            "Hey! I've made up a new operation called {operator_symbol}. "
            "It works on the symbols {{{symbol_set}}} and here's the complete "
            "lookup table that defines it:\n\n"
            "{operation_table}\n\n"
            "Using ONLY this table (no normal math rules apply!), "
            "what does this evaluate to?\n\n"
            "{expression}\n\n"
            "Just give me the final symbol."
        ),
        "linguistic": (
            "Consider a binary operation {operator_symbol} defined on the "
            "finite set {{{symbol_set}}}. The operation is specified entirely "
            "by the lookup table below — no algebraic properties "
            "(commutativity, associativity, identity) should be assumed "
            "unless they are evident from the table.\n\n"
            "{operation_table}\n\n"
            "Evaluate the following expression step by step, resolving "
            "the innermost parentheses first and performing each lookup "
            "against the table:\n\n"
            "{expression}\n\n"
            "Show your working, then state the final result as a single "
            "symbol from the set."
        ),
    },
}
