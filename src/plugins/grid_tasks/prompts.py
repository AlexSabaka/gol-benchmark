"""User prompt templates for the Grid Tasks plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{table_str}\n\n{question}\nAnswer:",
        "casual": (
            "Here is a data table:\n\n"
            "{table_str}\n\n"
            "Question: {question}\n\n"
            "Please provide your answer clearly."
        ),
        "linguistic": (
            "Please analyze the following data table carefully "
            "and answer the question.\n\n"
            "{table_str}\n\n"
            "Question: {question}\n\n"
            "Provide your answer with a brief explanation."
        ),
    },
}
