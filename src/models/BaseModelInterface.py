"""Base class for all model provider interfaces.

All interfaces follow a lightweight pattern:
    interface = SomeInterface(model_name, ...)
    result = interface.query(prompt, params)

Where ``params`` is a dict with keys like ``temperature``, ``max_tokens``,
``system_prompt``, ``timeout_seconds``, etc.  The return value is always a
dict with at least ``response`` (str) and ``duration`` (float) keys. On
failure the dict contains ``error`` instead of ``response``.
"""

from typing import Any, Dict


class ModelInterface:
    """Abstract base for all model provider interfaces.

    Subclasses must implement :meth:`query`.
    """

    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Send *prompt* to the model and return a result dict.

        Parameters
        ----------
        prompt : str
            The user prompt text.
        params : dict
            Sampling / execution parameters.  Common keys:
            ``temperature``, ``max_tokens``, ``top_k``, ``top_p``,
            ``min_p``, ``system_prompt``, ``timeout_seconds``.

        Returns
        -------
        dict
            On success: ``{"response": str, "tokens_generated": int,
            "tokens_input": int, "duration": float, "model_info": dict}``
            On error: ``{"error": str, "duration": float, "model_info": dict}``
        """
        raise NotImplementedError


# Backward-compatible alias used in older code / docs.
BaseModelInterface = ModelInterface