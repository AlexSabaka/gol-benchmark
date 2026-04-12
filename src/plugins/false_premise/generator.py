"""
False Premise – Test Case Generator

Generates questions that embed a dangerous or impossible premise.  The model
should always refuse or correct the premise — never supply a quantity, ratio,
or procedure.

Five domains:
  chemistry   — household chemical mixing (CSV-backed)
  medicine    — drug interaction dosage questions (CSV-backed)
  food_safety — unsafe food-handling "how long" questions (CSV-backed)
  physics     — physically impossible premises (hardcoded)
  logic       — self-contradictory premises (hardcoded)

Hard mode (chemistry only): described properties instead of named products
to test reasoning rather than memorisation of known-dangerous pairs.
"""
from __future__ import annotations

import csv
import itertools
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.i18n.loader import compose_user_prompt
from src.plugins.false_premise.i18n import (
    CHEM_QUESTION_TEMPLATES as I18N_CHEM_QUESTION_TEMPLATES,
    CHEM_HARD_MODE_TEMPLATES as I18N_CHEM_HARD_MODE_TEMPLATES,
    CHEM_GOALS,
    MEDICINE_QUESTION_TEMPLATES as I18N_MEDICINE_QUESTION_TEMPLATES,
    FOOD_QUESTION_TEMPLATES as I18N_FOOD_QUESTION_TEMPLATES,
    FOOD_PREP_TEMPLATES as I18N_FOOD_PREP_TEMPLATES,
    FOOD_INTERACTION_TEMPLATES as I18N_FOOD_INTERACTION_TEMPLATES,
    FOOD_ACTION_VERBS as I18N_FOOD_ACTION_VERBS,
    PHYSICS_SCENARIOS as I18N_PHYSICS_SCENARIOS,
    LOGIC_SCENARIOS as I18N_LOGIC_SCENARIOS,
    URGENCY_FRAMINGS as I18N_URGENCY_FRAMINGS,
    AUTHORITY_FRAMINGS as I18N_AUTHORITY_FRAMINGS,
)

# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent / "data"

# Module-level caches (loaded once)
_CHEM_INTERACTIONS: Optional[List[Dict]] = None
_CHEM_PRODUCTS: Optional[Dict[str, Dict]] = None
_DRUG_INTERACTIONS: Optional[List[Dict]] = None
_FOOD_HAZARDS: Optional[List[Dict]] = None
_SEVERITY_MAP: Optional[Dict[str, Dict]] = None


def _load_csv(filename: str) -> List[Dict[str, str]]:
    """Load a CSV file from the data directory and return rows as dicts."""
    path = _DATA_DIR / filename
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ensure_chem_interactions() -> List[Dict]:
    global _CHEM_INTERACTIONS
    if _CHEM_INTERACTIONS is None:
        _CHEM_INTERACTIONS = _load_csv("chemical_interactions_database.csv")
    return _CHEM_INTERACTIONS


def _ensure_chem_products() -> Dict[str, Dict]:
    """Load chemical products database, keyed by Chemical_Compound."""
    global _CHEM_PRODUCTS
    if _CHEM_PRODUCTS is None:
        rows = _load_csv("chemical_products_database.csv")
        _CHEM_PRODUCTS = {r["Chemical_Compound"]: r for r in rows}
    return _CHEM_PRODUCTS


def _ensure_drug_interactions() -> List[Dict]:
    global _DRUG_INTERACTIONS
    if _DRUG_INTERACTIONS is None:
        _DRUG_INTERACTIONS = _load_csv("drug_interactions.csv")
    return _DRUG_INTERACTIONS


def _ensure_food_hazards() -> List[Dict]:
    global _FOOD_HAZARDS
    if _FOOD_HAZARDS is None:
        _FOOD_HAZARDS = _load_csv("food_safety_hazards.csv")
    return _FOOD_HAZARDS


def _ensure_severity_map() -> Dict[str, Dict]:
    """Load hazard severity classification, keyed by Interaction_ID."""
    global _SEVERITY_MAP
    if _SEVERITY_MAP is None:
        rows = _load_csv("hazard_severity_classification.csv")
        _SEVERITY_MAP = {r["Interaction_ID"]: r for r in rows}
    return _SEVERITY_MAP


# ---------------------------------------------------------------------------
# Multilingual template helpers
# ---------------------------------------------------------------------------


def _get_lang_list(mapping: Dict[str, List], language: str) -> List:
    """Return the list for *language*, falling back to English."""
    return mapping.get(language, mapping["en"])

# ---------------------------------------------------------------------------
# User prompt templates (per style)
# ---------------------------------------------------------------------------

# Templates moved to prompts.py

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _describe_chemical(name: str) -> str:
    """Build a hard-mode description for a chemical, using product DB if available."""
    products = _ensure_chem_products()
    info = products.get(name)
    if info:
        formula = info.get("Chemical_Formula", "")
        concentration = info.get("Typical_Concentration", "")
        form = info.get("Physical_Form", "")
        parts = []
        if formula:
            parts.append(formula)
        if concentration:
            parts.append(f"at {concentration}")
        if form:
            parts.append(f"({form})")
        return " ".join(parts) if parts else name
    return name


class FalsePremiseGenerator(TestCaseGenerator):
    """Generates false-premise test cases across five domains."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="count", label="Number of cases", field_type="number",
                default=30, min_value=5, max_value=200, group="basic",
                help="Total number of test cases to generate",
            ),
            ConfigField(
                name="domains", label="Domains", field_type="multi-select",
                default=["chemistry", "medicine", "food_safety", "physics", "logic"],
                options=["chemistry", "medicine", "food_safety", "physics", "logic"],
                group="basic",
                help="Domains to include in the test set",
            ),
            ConfigField(
                name="hard_mode_ratio", label="Hard mode ratio (chemistry)",
                field_type="number", default=0.3,
                min_value=0.0, max_value=1.0, step=0.1, group="advanced",
                help="Fraction of chemistry scenarios using described properties instead of named products",
            ),
            ConfigField(
                name="severity_filter", label="Severity filter",
                field_type="multi-select",
                default=["LETHAL", "SEVERE", "MODERATE"],
                options=["LETHAL", "SEVERE", "MODERATE"],
                group="advanced",
                help="Include only scenarios at these severity levels (chemistry & medicine)",
            ),
        ]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        language = prompt_config.get("language", "en")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")
        domains = config.get("domains", ["chemistry", "medicine", "food_safety", "physics", "logic"])
        hard_mode_ratio = config.get("hard_mode_ratio", 0.3)
        severity_filter = set(config.get("severity_filter", ["LETHAL", "SEVERE", "MODERATE"]))

        # --- Collect scenario pool per domain ---
        scenarios: List[Dict[str, Any]] = []

        if "chemistry" in domains:
            scenarios.extend(self._build_chemistry_scenarios(rng, hard_mode_ratio, severity_filter, language))
        if "medicine" in domains:
            scenarios.extend(self._build_medicine_scenarios(rng, severity_filter, language))
        if "food_safety" in domains:
            scenarios.extend(self._build_food_scenarios(rng, language))
        if "physics" in domains:
            scenarios.extend(self._build_physics_scenarios(language))
        if "logic" in domains:
            scenarios.extend(self._build_logic_scenarios(language))

        if not scenarios:
            return []

        # Expand scenarios with framing × user style combinations
        urgency_framings = _get_lang_list(I18N_URGENCY_FRAMINGS, language)
        authority_framings = _get_lang_list(I18N_AUTHORITY_FRAMINGS, language)
        combinations = list(itertools.product(
            scenarios,
            urgency_framings,
            authority_framings,
        ))
        rng.shuffle(combinations)
        extended = (combinations * (count // max(len(combinations), 1) + 2))[:count]

        # --- Build test cases ---
        system_prompt = self._get_system_prompt(system_style, language)

        test_cases: List[TestCase] = []
        for idx, (scenario, urgency, authority) in enumerate(extended):
            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                system_prompt=system_prompt,
                scenario=scenario,
                urgency=urgency,
                authority=authority,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------
    # Domain-specific scenario builders
    # ------------------------------------------------------------------

    def _build_chemistry_scenarios(
        self, rng: random.Random, hard_mode_ratio: float, severity_filter: set,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        interactions = _ensure_chem_interactions()
        severity_map = _ensure_severity_map()
        scenarios: List[Dict[str, Any]] = []

        chem_templates = _get_lang_list(I18N_CHEM_QUESTION_TEMPLATES, language)
        hard_templates = _get_lang_list(I18N_CHEM_HARD_MODE_TEMPLATES, language)

        for row in interactions:
            # Filter by severity if available
            sev = row.get("Hazard_Severity", "").upper()
            if sev and sev not in severity_filter:
                continue

            product_1 = row["Chemical_1_Common_Products"].split(";")[0].strip()
            product_2 = row["Chemical_2_Common_Products"].split(";")[0].strip()
            chem_1 = row["Chemical_1_Name"]
            chem_2 = row["Chemical_2_Name"]
            goal = rng.choice(CHEM_GOALS)
            question_template = rng.choice(chem_templates)

            # Standard mode — named products
            scenarios.append({
                "domain": "chemistry",
                "question": question_template.format(
                    product_1=product_1,
                    product_2=product_2,
                    goal=goal,
                ),
                "hard_mode": False,
                "hazard_severity": sev or "UNKNOWN",
                "premise_type": "dangerous_chemical_mix",
                "chemicals": f"{chem_1} + {chem_2}",
                "hazard_type": row.get("Hazard_Type", ""),
            })

            # Hard mode — described properties
            if rng.random() < hard_mode_ratio:
                desc_1 = _describe_chemical(chem_1)
                desc_2 = _describe_chemical(chem_2)
                hard_template = rng.choice(hard_templates)
                scenarios.append({
                    "domain": "chemistry",
                    "question": hard_template.format(
                        desc_1=desc_1,
                        desc_2=desc_2,
                        goal=goal,
                    ),
                    "hard_mode": True,
                    "hazard_severity": sev or "UNKNOWN",
                    "premise_type": "dangerous_chemical_mix_described",
                    "chemicals": f"{chem_1} + {chem_2}",
                    "hazard_type": row.get("Hazard_Type", ""),
                })

        return scenarios

    def _build_medicine_scenarios(
        self, rng: random.Random, severity_filter: set,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        interactions = _ensure_drug_interactions()
        scenarios: List[Dict[str, Any]] = []

        med_templates = _get_lang_list(I18N_MEDICINE_QUESTION_TEMPLATES, language)

        # Map drug severity labels to the unified filter scale
        drug_sev_to_unified = {
            "CONTRAINDICATED": "LETHAL",
            "MAJOR": "SEVERE",
            "MODERATE": "MODERATE",
        }

        for row in interactions:
            raw_sev = row.get("severity", "").strip().upper()
            unified_sev = drug_sev_to_unified.get(raw_sev, raw_sev)
            if unified_sev and unified_sev not in severity_filter:
                continue

            # Pick one generic drug from each slash-separated list
            drug_1_options = [d.strip() for d in row["drug_1_generic"].split("/")]
            drug_2_options = [d.strip() for d in row["drug_2_generic"].split("/")]
            drug_1 = rng.choice(drug_1_options)
            drug_2 = rng.choice(drug_2_options)

            brand_1_options = [b.strip() for b in row["drug_1_brands"].split("/")]
            brand_2_options = [b.strip() for b in row["drug_2_brands"].split("/")]
            brand_1 = rng.choice(brand_1_options)
            brand_2 = rng.choice(brand_2_options)

            question_template = rng.choice(med_templates)
            scenarios.append({
                "domain": "medicine",
                "question": question_template.format(
                    drug_1=drug_1, drug_2=drug_2,
                    brand_1=brand_1, brand_2=brand_2,
                ),
                "hard_mode": False,
                "hazard_severity": unified_sev or "UNKNOWN",
                "premise_type": "dangerous_drug_interaction",
                "interaction_type": row.get("interaction_type", ""),
                "resulting_harm": row.get("resulting_harm", ""),
            })

        return scenarios

    def _build_food_scenarios(
        self, rng: random.Random, language: str = "en",
    ) -> List[Dict[str, Any]]:
        hazards = _ensure_food_hazards()
        scenarios: List[Dict[str, Any]] = []

        food_templates = _get_lang_list(I18N_FOOD_QUESTION_TEMPLATES, language)
        prep_templates = _get_lang_list(I18N_FOOD_PREP_TEMPLATES, language)
        interaction_templates = _get_lang_list(I18N_FOOD_INTERACTION_TEMPLATES, language)
        action_verbs = I18N_FOOD_ACTION_VERBS.get(language, I18N_FOOD_ACTION_VERBS["en"])

        for row in hazards:
            food = row.get("substance_1", "").strip()
            category = row.get("category", "").strip()
            if not food:
                continue

            sev = row.get("severity", "MODERATE").upper()

            if category in ("temperature_time", "bacterial_contamination", "scombroid_histamine"):
                template = rng.choice(food_templates)
                scenarios.append({
                    "domain": "food_safety",
                    "question": template.format(food=food),
                    "hard_mode": False,
                    "hazard_severity": sev,
                    "premise_type": f"food_{category}",
                    "mechanism": row.get("mechanism", ""),
                })
            elif category in ("preparation_hazard", "quantity_toxicity"):
                action_key = "prepare" if category == "preparation_hazard" else "consume_large"
                action = action_verbs.get(action_key, action_key)
                template = rng.choice(prep_templates)
                scenarios.append({
                    "domain": "food_safety",
                    "question": template.format(food=food, action=action),
                    "hard_mode": False,
                    "hazard_severity": sev,
                    "premise_type": f"food_{category}",
                    "mechanism": row.get("mechanism", ""),
                })
            elif category in ("food_drug_interaction", "food_food_interaction"):
                substance_2 = row.get("substance_2", "").strip()
                if substance_2:
                    template = rng.choice(interaction_templates)
                    scenarios.append({
                        "domain": "food_safety",
                        "question": template.format(
                            food=food, substance_2=substance_2,
                        ),
                        "hard_mode": False,
                        "hazard_severity": sev,
                        "premise_type": f"food_{category}",
                        "mechanism": row.get("mechanism", ""),
                    })

        return scenarios

    def _build_physics_scenarios(self, language: str = "en") -> List[Dict[str, Any]]:
        physics = _get_lang_list(I18N_PHYSICS_SCENARIOS, language)
        return [
            {
                "domain": "physics",
                "question": s["question"],
                "hard_mode": False,
                "hazard_severity": "N/A",
                "premise_type": s["premise_type"],
            }
            for s in physics
        ]

    def _build_logic_scenarios(self, language: str = "en") -> List[Dict[str, Any]]:
        logic = _get_lang_list(I18N_LOGIC_SCENARIOS, language)
        return [
            {
                "domain": "logic",
                "question": s["question"],
                "hard_mode": False,
                "hazard_severity": "N/A",
                "premise_type": s["premise_type"],
            }
            for s in logic
        ]

    # ------------------------------------------------------------------
    # Test case builder
    # ------------------------------------------------------------------

    def _build_test_case(
        self,
        idx: int,
        seed: int,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        system_prompt: str,
        scenario: Dict[str, Any],
        urgency: str,
        authority: str,
    ) -> TestCase:
        domain = scenario["domain"]
        question = scenario["question"]

        user_prompt = compose_user_prompt(
            "false_premise", language, user_style,
            urgency=urgency, authority=authority, question=question,
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        task_params = {
            "expected_answer": "refusal",
            "domain": domain,
            "hard_mode": scenario.get("hard_mode", False),
            "hazard_severity": scenario.get("hazard_severity", "UNKNOWN"),
            "premise_type": scenario.get("premise_type", ""),
            "surface_question": question,
        }
        # Include domain-specific metadata
        for key in ("chemicals", "hazard_type", "interaction_type", "resulting_harm", "mechanism"):
            if key in scenario:
                task_params[key] = scenario[key]

        return TestCase(
            test_id=f"false_premise_{domain}_{seed}_{idx:04d}",
            task_type="false_premise",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params=task_params,
            prompt_metadata={
                "user_style": user_style,
                "system_style": system_style,
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "domain": domain,
                "hard_mode": scenario.get("hard_mode", False),
                "premise_type": scenario.get("premise_type", ""),
            },
        )
