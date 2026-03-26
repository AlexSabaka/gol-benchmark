"""User prompt templates for the Object Tracking plugin.

Object tracking is special: the prompt body depends on scenario steps
formatted by a StepBuilder.  The templates below wrap that steps text.
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{steps_text}\n\n{question}\nAnswer:",
        "casual": "{steps_text} {question} Give single word answer.",
        "linguistic": (
            "{steps_text}\n\n"
            "Based on the sequence of actions described above, determine the "
            "current location of the {object}.\n\n"
            "Apply logical reasoning to track the object through each step:\n"
            "1. Identify where the object was initially placed\n"
            "2. Track any movements or transfers\n"
            "3. Pay special attention to any inversion or flipping of containers\n"
            "4. Determine the final resting location\n\n"
            "{question}\n"
            "Provide your answer as a single word indicating the location."
        ),
    },
}
