"""User prompt templates for the Carwash Paradox plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{setup} The carwash is {distance}. {question}",
        "casual": "Hey, quick question: {setup}  The carwash is {distance}.  {question}",
        "linguistic": (
            "I have an everyday logistics question and I'd appreciate your honest advice.\n\n"
            "{setup}  The carwash is {distance}.  {weather}{urgency}{transport}\n\n{question}"
        ),
    },
}
