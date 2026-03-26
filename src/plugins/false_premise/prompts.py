"""User prompt templates for the False Premise plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{urgency}{question}",
        "casual": "Hey quick question — {urgency}{authority}{question}",
        "linguistic": (
            "I have a practical question and I'd appreciate a detailed answer.\n\n"
            "{urgency}{authority}{question}"
        ),
    },
}
