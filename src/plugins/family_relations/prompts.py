"""User prompt templates for the Family Relations plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{puzzle}\n\nAnswer with a single integer.",
        "casual": (
            "Hey, here's a quick family puzzle:\n\n"
            "{puzzle}\n\n"
            "What's the answer?  Just give me the number."
        ),
        "linguistic": (
            "Please solve the following family-relations reasoning problem. "
            "Think carefully about who is counted and from whose perspective.\n\n"
            "{puzzle}\n\n"
            "Provide your final answer as a single integer."
        ),
    },
}
