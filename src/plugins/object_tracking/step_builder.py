"""
Step Builder for Object Tracking scenarios.

Generates step sequences for object tracking tests, including:
- Initial object placement in container at location
- Pre-inversion distractor steps
- Critical inversion step (container flips, object falls)
- Post-inversion container moves
- Post-inversion distractor steps

Gender-aware: accepts ``subject_gender`` ("m"/"f") and resolves
Ukrainian verb forms + ES/FR/DE articles via grammar_utils.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.grammar_utils import (
    article,
    pick_templates,
    resolve_vocab,
    vocab_gender,
)


@dataclass
class ScenarioStep:
    """Represents a single step in the object tracking scenario."""
    step_number: int
    action_type: str  # 'place', 'move', 'invert', 'distractor', 'interact'
    description: str
    affects_object: bool
    object_location_after: str  # Location of object after this step ('container' or location name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'step_number': self.step_number,
            'action_type': self.action_type,
            'description': self.description,
            'affects_object': self.affects_object,
            'object_location_after': self.object_location_after
        }


@dataclass
class Scenario:
    """Complete generated scenario."""
    object: str
    container: str
    subject: str
    initial_location: str
    steps: List[ScenarioStep]
    final_object_location: str
    inversion_step_index: int
    post_inversion_container_location: str
    is_sticky: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'object': self.object,
            'container': self.container,
            'subject': self.subject,
            'initial_location': self.initial_location,
            'steps': [s.to_dict() for s in self.steps],
            'final_object_location': self.final_object_location,
            'inversion_step_index': self.inversion_step_index,
            'post_inversion_container_location': self.post_inversion_container_location,
            'is_sticky': self.is_sticky
        }


# English-only template collections (kept for backward compatibility with
# code that references these module-level constants directly)
PLACEMENT_TEMPLATES = [
    "{subject} put a {object} in a {container} and sit the {container} on the {location}.",
    "{subject} place a {object} into a {container} on the {location}.",
    "{subject} drop a {object} in a {container} sitting on the {location}.",
    "{subject} put a {object} inside a {container} that is on the {location}.",
]

INVERSION_TEMPLATES = [
    "{subject} turn the {container} upside down.",
    "{subject} flip the {container} over.",
    "{subject} invert the {container}.",
    "{subject} tip the {container} upside down.",
    "{subject} turn the {container} over.",
]

MOVE_TEMPLATES = [
    "{subject} then place the {container} in the {location}.",
    "{subject} move the {container} to the {location}.",
    "{subject} put the {container} on the {location}.",
    "{subject} carry the {container} over to the {location}.",
    "{subject} set the {container} down on the {location}.",
]

INTERACT_TEMPLATES = [
    "{subject} then start the {appliance}.",
    "{subject} close the {appliance} door.",
    "{subject} turn on the {appliance}.",
    "{subject} press a button on the {appliance}.",
]

DISTRACTOR_TEMPLATES = {
    'irrelevant': [
        "{subject} set the timer on a microwave to {time} seconds.",
        "{subject} look at {possessive} phone.",
        "{subject} scratch {possessive} head.",
        "{subject} take a deep breath.",
        "{subject} hear a noise outside.",
        "{subject} think about what to have for dinner.",
        "{subject} check the time.",
        "{subject} yawn briefly.",
        "{subject} stretch {possessive} arms.",
        "{subject} hum a little tune.",
    ],
    'spatial': [
        "{subject} walk to the {room}.",
        "{subject} look at the {nearby_object}.",
        "{subject} step back from the {location}.",
        "{subject} glance at the window.",
        "{subject} turn around.",
        "{subject} walk around the room.",
    ],
    'temporal': [
        "{subject} wait for {time} seconds.",
        "{subject} pause for a moment.",
        "{subject} count to {number}.",
        "{subject} wait briefly.",
        "{subject} take a short break.",
    ]
}

QUESTION_TEMPLATES = [
    "Where is the {object}?",
    "Where is the {object} now?",
]

# Vocabulary for template filling
ROOMS = ['living room', 'kitchen', 'bedroom', 'hallway', 'bathroom']
NEARBY_OBJECTS = ['clock', 'picture', 'plant', 'lamp', 'chair', 'window']
APPLIANCES = ['microwave', 'oven', 'dishwasher', 'refrigerator']
TIMES = [10, 15, 20, 30, 45, 60]
NUMBERS = [3, 5, 10]

# Additional locations for post-inversion moves
MOVE_LOCATIONS = ['microwave', 'refrigerator', 'oven', 'sink', 'drawer', 'cabinet']


# ── Helpers for Spanish contracted articles ──────────────────────────────

def _es_a_article(gender: str) -> str:
    """Return 'al' (a + el) for masculine, 'a la' for feminine."""
    return "al" if gender == "m" else "a la"


def _es_de_article(gender: str) -> str:
    """Return 'del' (de + el) for masculine, 'de la' for feminine."""
    return "del" if gender == "m" else "de la"


def _de_zu_article(gender: str) -> str:
    """Return 'zum' (zu + dem) for m/n, 'zur' (zu + der) for f."""
    return "zur" if gender == "f" else "zum"


class StepBuilder:
    """Builds object tracking scenarios with configurable complexity."""

    def __init__(self, seed: Optional[int] = None, language: str = "en",
                 subject_gender: str = "m"):
        """Initialize with optional random seed for reproducibility.

        Args:
            seed: Random seed.
            language: Language code.
            subject_gender: Grammatical gender of the subject ('m' or 'f').
                Used for Ukrainian verb agreement and French past-participle
                agreement.
        """
        self.rng = random.Random(seed)
        self.language = language
        self.subject_gender = subject_gender
        from src.plugins.object_tracking import step_i18n
        self._i18n = step_i18n

    def _loc(self, en_word: str, vocab_dict: dict, case: str = "nom") -> str:
        """Localize an English vocabulary word, optionally with case."""
        return resolve_vocab(en_word, vocab_dict, self.language, case)

    def _templates(self, template_dict: dict) -> list:
        """Get templates for current language and subject gender."""
        return pick_templates(template_dict, self.language, self.subject_gender)

    def _get_subject_possessive(self, subject: str) -> str:
        """Get possessive form for subject in current language."""
        _, poss = self._i18n.get_subject_forms(subject, self.language)
        return poss

    def _format_subject(self, subject: str, capitalize: bool = True) -> str:
        """Format subject for sentence use in current language."""
        formatted, _ = self._i18n.get_subject_forms(subject, self.language)
        if capitalize and formatted[0].islower():
            return formatted.capitalize()
        return formatted

    def _article_vars(self, obj_en: str, container_en: str,
                      location_en: str = "",
                      loc_vocab: dict = None) -> Dict[str, str]:
        """Compute all article placeholder values for the current language.

        Returns a dict of ``{art_def_obj: ..., art_indef_cont: ..., ...}``
        that can be passed as ``**kwargs`` to ``str.format()``.
        """
        lang = self.language
        i18n = self._i18n
        if loc_vocab is None:
            loc_vocab = i18n.LOCATIONS

        obj_g = vocab_gender(obj_en, i18n.OBJECTS, lang)
        cont_g = vocab_gender(container_en, i18n.CONTAINERS, lang)
        loc_g = vocab_gender(location_en, loc_vocab, lang) if location_en else "m"

        d: Dict[str, str] = {}
        # --- definite / indefinite articles (ES, FR) ---
        for prefix, g, label in [
            ("obj", obj_g, "obj"),
            ("cont", cont_g, "cont"),
            ("loc", loc_g, "loc"),
        ]:
            d[f"art_def_{label}"] = article(lang, g, definite=True)
            d[f"art_indef_{label}"] = article(lang, g, definite=False)

        # --- German articles need case ---
        for case in ("nom", "acc", "dat"):
            for g, label in [(obj_g, "obj"), (cont_g, "cont"), (loc_g, "loc")]:
                d[f"art_def_{label}_{case}"] = article(lang, g, definite=True, case=case)
                d[f"art_indef_{label}_{case}"] = article(lang, g, definite=False, case=case)

        # --- Spanish contracted articles: a + el = al, de + el = del ---
        d["art_def_cont_a"] = _es_a_article(cont_g)
        d["art_def_loc_a"] = _es_a_article(loc_g)
        d["art_def_cont_de"] = _es_de_article(cont_g)
        d["art_def_loc_de"] = _es_de_article(loc_g)

        # --- German zu + article contractions ---
        d["art_def_loc_zu"] = _de_zu_article(loc_g)

        return d

    def _resolve_list_item(self, item: Any, case: str = "nom") -> str:
        """Resolve a list-vocab item (str or dict) to the requested form."""
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            return item.get(case, item.get("nom", item.get("word", str(item))))
        return str(item)

    def _item_gender(self, item: Any) -> str:
        """Get gender from a list-vocab item."""
        if isinstance(item, dict):
            return item.get("gender", "m")
        return "m"

    def _fill_template(
        self,
        template: str,
        subject: str,
        *,
        obj_en: str = "",
        container_en: str = "",
        location_en: str = "",
        loc_vocab: dict = None,
        appliance_en: str = "",
        room_item: Any = "",
        nearby_item: Any = "",
        **extra_kwargs,
    ) -> str:
        """Fill a template with variables, resolving articles and cases.

        This is the central method that injects:
        - localized noun forms (``{object}``, ``{container}``, ``{location}``)
        - case-inflected forms (``{object_acc}``, ``{container_loc}``, etc.)
        - article placeholders (``{art_def_obj}``, ``{art_indef_cont_acc}``, etc.)
        """
        lang = self.language
        i18n = self._i18n
        if loc_vocab is None:
            loc_vocab = i18n.LOCATIONS

        possessive = self._get_subject_possessive(subject)
        formatted_subject = self._format_subject(subject)

        # --- Build all substitution values ---
        vals: Dict[str, Any] = {
            "subject": formatted_subject,
            "possessive": possessive,
        }

        # Object forms
        if obj_en:
            vals["object"] = resolve_vocab(obj_en, i18n.OBJECTS, lang, "nom")
            vals["object_nom"] = resolve_vocab(obj_en, i18n.OBJECTS, lang, "nom")
            vals["object_acc"] = resolve_vocab(obj_en, i18n.OBJECTS, lang, "acc")
            vals["object_loc"] = resolve_vocab(obj_en, i18n.OBJECTS, lang, "loc")

        # Container forms
        if container_en:
            vals["container"] = resolve_vocab(container_en, i18n.CONTAINERS, lang, "nom")
            vals["container_nom"] = resolve_vocab(container_en, i18n.CONTAINERS, lang, "nom")
            vals["container_acc"] = resolve_vocab(container_en, i18n.CONTAINERS, lang, "acc")
            vals["container_loc"] = resolve_vocab(container_en, i18n.CONTAINERS, lang, "loc")

        # Location forms
        if location_en:
            vals["location"] = resolve_vocab(location_en, loc_vocab, lang, "nom")
            vals["location_nom"] = resolve_vocab(location_en, loc_vocab, lang, "nom")
            vals["location_acc"] = resolve_vocab(location_en, loc_vocab, lang, "acc")
            vals["location_loc"] = resolve_vocab(location_en, loc_vocab, lang, "loc")

        # Appliance forms
        if appliance_en:
            vals["appliance"] = resolve_vocab(appliance_en, i18n.APPLIANCES, lang, "nom")
            vals["appliance_nom"] = resolve_vocab(appliance_en, i18n.APPLIANCES, lang, "nom")
            vals["appliance_acc"] = resolve_vocab(appliance_en, i18n.APPLIANCES, lang, "acc")

            # Appliance articles for ES/FR/DE
            appl_g = vocab_gender(appliance_en, i18n.APPLIANCES, lang)
            vals["art_def_appl"] = article(lang, appl_g, definite=True)
            vals["art_def_appl_acc"] = article(lang, appl_g, definite=True, case="acc")
            vals["art_def_appl_gen"] = article(lang, appl_g, definite=True, case="dat")  # DE genitive approximation
            vals["art_def_appl_de"] = _es_de_article(appl_g)
            vals["art_def_appl_a"] = _es_a_article(appl_g)

        # Room forms (list items, not keyed dicts)
        if room_item:
            vals["room"] = self._resolve_list_item(room_item, "nom")
            vals["room_gen"] = self._resolve_list_item(room_item, "gen")
            vals["room_loc"] = self._resolve_list_item(room_item, "loc")
            room_g = self._item_gender(room_item)
            vals["art_def_room"] = article(lang, room_g, definite=True)
            vals["art_def_room_acc"] = article(lang, room_g, definite=True, case="acc")
            vals["art_def_room_zu"] = _de_zu_article(room_g)

        # Nearby object forms (list items)
        if nearby_item:
            vals["nearby_object"] = self._resolve_list_item(nearby_item, "nom")
            vals["nearby_object_acc"] = self._resolve_list_item(nearby_item, "acc")
            nearby_g = self._item_gender(nearby_item)
            vals["art_def_nearby"] = article(lang, nearby_g, definite=True)
            vals["art_def_nearby_acc"] = article(lang, nearby_g, definite=True, case="acc")

        # Articles for obj/cont/loc
        if obj_en or container_en or location_en:
            art_vars = self._article_vars(
                obj_en or "", container_en or "", location_en or "",
                loc_vocab=loc_vocab,
            )
            vals.update(art_vars)

        # Extra pass-through kwargs (time, number, etc.)
        vals.update(extra_kwargs)

        return template.format(**vals)

    def _create_placement_step(
        self,
        subject: str,
        obj: str,
        container: str,
        location: str
    ) -> ScenarioStep:
        """Create the initial placement step."""
        template = self.rng.choice(self._templates(self._i18n.PLACEMENT))
        description = self._fill_template(
            template, subject,
            obj_en=obj, container_en=container, location_en=location,
        )

        return ScenarioStep(
            step_number=1,
            action_type='place',
            description=description,
            affects_object=True,
            object_location_after='container'  # Object is in the container
        )

    def _create_inversion_step(
        self,
        subject: str,
        container: str,
        step_number: int,
        current_location: str,
        is_sticky: bool
    ) -> Tuple[ScenarioStep, str]:
        """Create the inversion step.

        Returns:
            Tuple of (step, new_object_location)
        """
        template = self.rng.choice(self._templates(self._i18n.INVERSION))
        description = self._fill_template(
            template, subject,
            container_en=container,
        )

        # After inversion, object falls to current location (unless sticky)
        new_object_location = 'container' if is_sticky else current_location

        return ScenarioStep(
            step_number=step_number,
            action_type='invert',
            description=description,
            affects_object=not is_sticky,
            object_location_after=new_object_location
        ), new_object_location

    def _create_move_step(
        self,
        subject: str,
        container: str,
        new_location: str,
        step_number: int,
        object_location: str
    ) -> ScenarioStep:
        """Create a container move step."""
        template = self.rng.choice(self._templates(self._i18n.MOVEMENT))
        description = self._fill_template(
            template, subject,
            container_en=container, location_en=new_location,
            loc_vocab=self._i18n.MOVE_LOCATIONS,
        )

        return ScenarioStep(
            step_number=step_number,
            action_type='move',
            description=description,
            affects_object=False,
            object_location_after=object_location
        )

    def _create_interact_step(
        self,
        subject: str,
        appliance: str,
        step_number: int,
        object_location: str
    ) -> ScenarioStep:
        """Create an interaction step with an appliance."""
        template = self.rng.choice(self._templates(self._i18n.INTERACT))
        description = self._fill_template(
            template, subject,
            appliance_en=appliance,
        )

        return ScenarioStep(
            step_number=step_number,
            action_type='interact',
            description=description,
            affects_object=False,
            object_location_after=object_location
        )

    def _create_distractor_step(
        self,
        subject: str,
        step_number: int,
        distractor_type: str,
        object_location: str
    ) -> ScenarioStep:
        """Create a distractor step."""
        distractor_map = {
            'irrelevant': self._i18n.DISTRACTOR_IRRELEVANT,
            'spatial': self._i18n.DISTRACTOR_SPATIAL,
            'temporal': self._i18n.DISTRACTOR_TEMPORAL,
        }
        templates = self._templates(
            distractor_map.get(distractor_type, self._i18n.DISTRACTOR_IRRELEVANT)
        )
        template = self.rng.choice(templates)

        # Pick room and nearby_object as full items (may be dicts)
        rooms_list = pick_templates(self._i18n.ROOMS, self.language, self.subject_gender)
        nearby_list = pick_templates(self._i18n.NEARBY_OBJECTS, self.language, self.subject_gender)

        room_item = self.rng.choice(rooms_list)
        nearby_item = self.rng.choice(nearby_list)

        description = self._fill_template(
            template, subject,
            room_item=room_item,
            nearby_item=nearby_item,
            time=self.rng.choice(TIMES),
            number=self.rng.choice(NUMBERS),
            # Provide fallback plain-text values for templates that use
            # bare {room}, {nearby_object}, {location} without article
            # placeholders (e.g. ZH, EN)
            room=self._resolve_list_item(room_item),
            nearby_object=self._resolve_list_item(nearby_item),
            location=self._resolve_list_item(room_item),
        )

        return ScenarioStep(
            step_number=step_number,
            action_type='distractor',
            description=description,
            affects_object=False,
            object_location_after=object_location
        )

    def _pick_new_location(self, current_location: str, initial_location: str) -> str:
        """Pick a new location different from current and initial (English keys)."""
        available = [loc for loc in MOVE_LOCATIONS
                     if loc != current_location and loc != initial_location]
        if not available:
            available = MOVE_LOCATIONS
        return self.rng.choice(available)

    def build_scenario(
        self,
        obj: str,
        container: str,
        subject: str,
        initial_location: str,
        pre_inversion_distractors: int = 0,
        post_inversion_distractors: int = 0,
        post_inversion_moves: int = 0,
        distractor_types: Optional[List[str]] = None,
        is_sticky: bool = False,
        add_final_interact: bool = True
    ) -> Scenario:
        """
        Generate a complete object tracking scenario.

        Args:
            obj: The object being tracked (e.g., 'grape')
            container: The container (e.g., 'cup')
            subject: The actor (e.g., 'I', 'you', 'John')
            initial_location: Where container starts (e.g., 'counter')
            pre_inversion_distractors: Number of distractors before inversion
            post_inversion_distractors: Number of distractors after inversion
            post_inversion_moves: Number of container moves after inversion
            distractor_types: Types of distractors to use
            is_sticky: Whether object sticks to container (doesn't fall)
            add_final_interact: Add a final interaction step (e.g., start microwave)

        Returns:
            Complete Scenario object
        """
        if distractor_types is None:
            distractor_types = ['irrelevant']

        steps: List[ScenarioStep] = []
        current_container_location = initial_location
        object_location = 'container'  # Initially in container
        step_number = 1

        # Step 1: Always start with placement
        placement_step = self._create_placement_step(
            subject, obj, container, initial_location
        )
        steps.append(placement_step)
        step_number += 1

        # Pre-inversion distractors
        for _ in range(pre_inversion_distractors):
            dtype = self.rng.choice(distractor_types)
            step = self._create_distractor_step(
                subject, step_number, dtype, object_location
            )
            steps.append(step)
            step_number += 1

        # Critical inversion step
        inversion_step, object_location = self._create_inversion_step(
            subject, container, step_number,
            current_container_location, is_sticky
        )
        steps.append(inversion_step)
        inversion_index = len(steps) - 1  # 0-indexed
        step_number += 1

        # Object now at current_container_location (if not sticky)
        # Post-inversion container moves
        for _ in range(post_inversion_moves):
            new_location = self._pick_new_location(
                current_container_location, initial_location
            )
            step = self._create_move_step(
                subject, container, new_location, step_number, object_location
            )
            steps.append(step)
            current_container_location = new_location
            step_number += 1

        # Post-inversion distractors
        for _ in range(post_inversion_distractors):
            dtype = self.rng.choice(distractor_types)
            step = self._create_distractor_step(
                subject, step_number, dtype, object_location
            )
            steps.append(step)
            step_number += 1

        # Optional final interaction (e.g., "start the microwave")
        if add_final_interact and current_container_location in APPLIANCES:
            interact_step = self._create_interact_step(
                subject, current_container_location, step_number, object_location
            )
            steps.append(interact_step)

        return Scenario(
            object=obj,
            container=container,
            subject=subject,
            initial_location=initial_location,
            steps=steps,
            final_object_location=object_location,
            inversion_step_index=inversion_index,
            post_inversion_container_location=current_container_location,
            is_sticky=is_sticky
        )

    def format_steps_narrative(self, steps: List[ScenarioStep]) -> str:
        """Format steps as a flowing narrative."""
        descriptions = [step.description for step in steps]
        return ' '.join(descriptions)

    def format_steps_numbered(self, steps: List[ScenarioStep]) -> str:
        """Format steps as a numbered list."""
        lines = [f"{step.step_number}. {step.description}" for step in steps]
        return '\n'.join(lines)

    def generate_question(self, obj: str) -> str:
        """Generate the question about object location in current language."""
        i18n = self._i18n
        lang = self.language
        templates = self._templates(i18n.QUESTION)
        template = self.rng.choice(templates)

        # Build substitution values including article placeholders
        obj_g = vocab_gender(obj, i18n.OBJECTS, lang)
        vals: Dict[str, str] = {
            "object": resolve_vocab(obj, i18n.OBJECTS, lang, "nom"),
            "object_nom": resolve_vocab(obj, i18n.OBJECTS, lang, "nom"),
            "art_def_obj": article(lang, obj_g, definite=True),
            "art_def_obj_nom": article(lang, obj_g, definite=True, case="nom"),
        }
        return template.format(**vals)
