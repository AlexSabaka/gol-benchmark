"""User prompt templates for the Inverted Cup plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Hey, I have a funny situation. {source} {description} {extra}{question}",
        "linguistic": (
            "I have a practical question about an unusual object I own.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
}
