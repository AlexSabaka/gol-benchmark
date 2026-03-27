"""User prompt templates for the encoding_cipher plugin (EN-only v1).

Nested dict: ``{"en": {"minimal": "...", ...}}`` following the project convention
(see carwash, inverted_cup plugins for reference).
Each template receives ``{instruction}`` and ``{encoded}`` variables.
"""

TEMPLATES = {
    "en": {
        # ── minimal ───────────────────────────────────────────────
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Answer: "
        ),

        # ── casual ────────────────────────────────────────────────
        "casual": (
            "Hey, quick one — {instruction}\n\n"
            "{encoded}"
        ),

        # ── linguistic ────────────────────────────────────────────
        "linguistic": (
            "I have an encoding task for you.\n\n"
            "{instruction}\n\n"
            "Here is the encoded payload:\n\n"
            "{encoded}\n\n"
            "Please provide your answer."
        ),
    },
}
