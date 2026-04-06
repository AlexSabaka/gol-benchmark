"""
Sally-Anne Scenario Builder

Generates false belief test scenarios with:
- Random subject names with proper gender-based pronouns
- Object placement and transfer during absence
- Optional observer (third person witness)
- Distractor elements
- Full multilingual support (en, es, fr, de, zh, ua)

Gender-aware grammar:
- French possessives depend on OBJECT gender (son/sa), not speaker
- Ukrainian possessives depend on OBJECT gender (свій/свою)
- German possessives depend on SUBJECT gender but articles on NOUN gender
- Ukrainian/French narrative verbs inflect for SUBJECT gender
- Articles in ES/FR/DE resolved via grammar_utils.article()
"""

import random
from typing import Dict, List, Tuple, Any, Optional

from src.plugins.sally_anne import scenario_i18n
from src.plugins.grammar_utils import (
    article,
    pick_templates,
    resolve_vocab,
    vocab_gender,
)


def _gender_code(gender_str: str) -> str:
    """Normalise ``'male'``/``'female'`` to ``'m'``/``'f'``."""
    if gender_str in ("m", "f", "n"):
        return gender_str
    return "m" if gender_str == "male" else "f"


class SallyAnneScenarioBuilder:
    """Builds Sally-Anne false belief test scenarios."""

    def __init__(self, language: str = "en", subject_gender: str = "m"):
        """
        Args:
            language: ISO language code (en/es/fr/de/zh/ua).
            subject_gender: Short gender of character A (``'m'`` or ``'f'``).
                Used for verb inflection in UA/FR narratives.
        """
        self.language = language if language in scenario_i18n.PRONOUNS else "en"
        self.subject_gender = _gender_code(subject_gender)
        self._i18n = scenario_i18n

    # ── helpers ──────────────────────────────────────────────────────────

    def _names(self, gender: str) -> List[str]:
        """Return the name list for the current language and gender."""
        return self._i18n.NAMES[self.language][gender]

    def _pronouns(self, gender: str) -> Dict[str, str]:
        """Return pronoun dict for the current language and gender.

        Accepts both short (``'m'``/``'f'``) and long (``'male'``/``'female'``)
        gender codes.
        """
        lang_prons = self._i18n.PRONOUNS[self.language]
        # Try exact key first, then map short→long
        if gender in lang_prons:
            return lang_prons[gender]
        long = "male" if gender == "m" else "female"
        return lang_prons.get(long, lang_prons["female"])

    def _obj_word(self, obj_key: str, case: str = "nom") -> str:
        """Return the localised object noun in the requested case."""
        return resolve_vocab(obj_key, self._i18n.OBJECTS, self.language, case)

    def _cont_word(self, cont_key: str, case: str = "nom") -> str:
        """Return the localised container noun in the requested case."""
        return resolve_vocab(cont_key, self._i18n.CONTAINERS, self.language, case)

    def _obj_gender(self, obj_key: str) -> str:
        """Grammatical gender of the localised object noun."""
        return vocab_gender(obj_key, self._i18n.OBJECTS, self.language)

    def _cont_gender(self, cont_key: str) -> str:
        """Grammatical gender of the localised container noun."""
        return vocab_gender(cont_key, self._i18n.CONTAINERS, self.language)

    # ── possessive resolution (object-gender-aware) ─────────────────────

    def _possessive(self, subject_gender: str, obj_key: str) -> str:
        """Return the possessive pronoun appropriate for the language.

        - EN: depends on subject gender (his / her)
        - ES: always ``su``
        - FR: depends on OBJECT gender (son / sa)
        - DE: depends on SUBJECT gender + OBJECT case/gender (resolved at
              template-fill time via ``{poss_dat}``)
        - ZH: depends on subject gender (\u4ed6\u7684 / \u5979\u7684)
        - UA: depends on OBJECT gender (\u0441\u0432\u0456\u0439 / \u0441\u0432\u043e\u044e)
        """
        subj_g = _gender_code(subject_gender)
        lang = self.language

        if lang in ("fr", "ua"):
            obj_g = self._obj_gender(obj_key)
            if lang == "fr":
                return "son" if obj_g == "m" else "sa"
            # UA
            return "\u0441\u0432\u0456\u0439" if obj_g == "m" else "\u0441\u0432\u043e\u044e"

        # EN, ES, ZH, DE: use subject-gender possessive from PRONOUNS
        pronouns = self._pronouns(subj_g)
        return pronouns["possessive"]

    def _de_possessive(self, subject_gender: str, obj_key: str, case: str = "nom") -> str:
        """German possessive: sein/ihr + case/gender ending.

        Depends on SUBJECT gender (sein-/ihr-) and OBJECT gender + case.
        """
        subj_g = _gender_code(subject_gender)
        obj_g = self._obj_gender(obj_key)
        stem = "sein" if subj_g == "m" else "ihr"

        # Endings by case and object gender:
        # nom: m='' f='e' n=''
        # acc: m='en' f='e' n=''
        # dat: m='em' f='er' n='em'
        _endings = {
            "nom": {"m": "",   "f": "e",  "n": ""},
            "acc": {"m": "en", "f": "e",  "n": ""},
            "dat": {"m": "em", "f": "er", "n": "em"},
        }
        ending = _endings.get(case, _endings["nom"]).get(obj_g, "")
        return stem + ending

    # ── article helpers ─────────────────────────────────────────────────

    def _art_def(self, noun_key: str, vocab_dict, case: str = "nom") -> str:
        """Definite article for a noun in the current language."""
        g = vocab_gender(noun_key, vocab_dict, self.language)
        return article(self.language, g, definite=True, case=case)

    def _art_indef(self, noun_key: str, vocab_dict, case: str = "nom") -> str:
        """Indefinite article for a noun in the current language."""
        g = vocab_gender(noun_key, vocab_dict, self.language)
        return article(self.language, g, definite=False, case=case)

    def _fr_prep_from(self, cont_key: str) -> str:
        """French ``du`` (m) / ``de la`` (f) preposition."""
        g = self._cont_gender(cont_key)
        return "du" if g == "m" else "de la"

    def _es_prep_from(self, cont_key: str) -> str:
        """Spanish ``del`` (m) / ``de la`` (f) preposition (de + article)."""
        g = self._cont_gender(cont_key)
        return "del" if g == "m" else "de la"

    def _fr_obj_pronoun(self, obj_key: str) -> str:
        """French object pronoun ``le`` (m) / ``la`` (f)."""
        g = self._obj_gender(obj_key)
        return "le" if g == "m" else "la"

    def _de_obj_pronoun(self, obj_key: str) -> str:
        """German accusative pronoun ``ihn`` (m) / ``sie`` (f) / ``es`` (n)."""
        g = self._obj_gender(obj_key)
        return {"m": "ihn", "f": "sie", "n": "es"}.get(g, "es")

    def _es_obj_pronoun(self, obj_key: str) -> str:
        """Spanish object pronoun ``lo`` (m) / ``la`` (f)."""
        g = self._obj_gender(obj_key)
        return "lo" if g == "m" else "la"

    # ── leave activity translation ──────────────────────────────────────

    def _translate_leave_activity(self, activity: str, gender: str) -> str:
        """Translate an English leave activity, respecting gender for UA."""
        en_activities = self._i18n.LEAVE_ACTIVITIES["en"]
        lang_activities = self._i18n.LEAVE_ACTIVITIES.get(self.language, en_activities)

        # UA has gender-split activities
        if isinstance(lang_activities, dict):
            g = _gender_code(gender)
            lang_activities = lang_activities.get(g, lang_activities.get("m", en_activities))

        if activity in en_activities:
            idx = en_activities.index(activity)
            if idx < len(lang_activities):
                return lang_activities[idx]
        return activity

    # ── name generation ──────────────────────────────────────────────────

    def generate_random_name(self, gender: str) -> str:
        """Generate a random name for the given gender (language-aware)."""
        return random.choice(self._names(gender))

    def get_pronouns(self, gender: str) -> Dict[str, str]:
        """Get pronouns for the given gender (language-aware)."""
        return self._pronouns(gender)

    # ── scenario generation ──────────────────────────────────────────────

    def generate_scenario(
        self,
        subject_pair: Optional[Tuple[str, str, str, str]] = None,
        obj: Optional[str] = None,
        containers: Optional[Tuple[str, str]] = None,
        leave_activity: Optional[str] = None,
        distractor_count: int = 0,
        include_observer: bool = False,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a Sally-Anne scenario.

        Args:
            subject_pair: (name_a, gender_a, name_b, gender_b) or None for random
            obj: Object key (English canonical, e.g. 'marble')
            containers: (container_a_key, container_b_key) -- English canonical keys
            leave_activity: English leave activity string (translated internally)
            distractor_count: Number of distractor elements
            include_observer: Whether to include a third-person observer
            seed: Random seed for reproducibility

        Returns:
            Scenario dictionary.
        """
        if seed is not None:
            random.seed(seed)

        # Generate or use provided subject pair
        if subject_pair:
            name_a, gender_a, name_b, gender_b = subject_pair
        else:
            gender_a = random.choice(["male", "female"])
            gender_b = random.choice(["male", "female"])
            name_a = self.generate_random_name(gender_a)
            name_b = self.generate_random_name(gender_b)
            while name_b == name_a:
                name_b = self.generate_random_name(gender_b)

        # Update builder subject_gender from actual character A gender
        self.subject_gender = _gender_code(gender_a)

        pronouns_a = self.get_pronouns(gender_a)
        pronouns_b = self.get_pronouns(gender_b)

        # Translate objects and containers (nominative for display)
        obj_display = self._obj_word(obj) if obj else obj
        container_a_display = self._cont_word(containers[0]) if containers else None
        container_b_display = self._cont_word(containers[1]) if containers else None
        leave_activity_display = (
            self._translate_leave_activity(leave_activity, gender_a)
            if leave_activity else leave_activity
        )

        # Generate distractor elements
        distractor_elements: List[str] = []
        if distractor_count > 0:
            distractor_elements = self._build_distractors(distractor_count, obj_display)

        # Generate observer if requested
        observer_info = None
        if include_observer:
            observer_gender = random.choice(["male", "female"])
            observer_name = self.generate_random_name(observer_gender)
            while observer_name in [name_a, name_b]:
                observer_name = self.generate_random_name(observer_gender)
            observer_pronouns = self.get_pronouns(observer_gender)
            observer_info = {
                "name": observer_name,
                "gender": observer_gender,
                "pronouns": observer_pronouns,
            }

        scenario = {
            "subject_a_name": name_a,
            "subject_a_gender": gender_a,
            "subject_a_pronouns": pronouns_a,
            "subject_b_name": name_b,
            "subject_b_gender": gender_b,
            "subject_b_pronouns": pronouns_b,
            # English canonical keys (for evaluator / task_params)
            "object": obj,
            "container_a": containers[0] if containers else None,
            "container_b": containers[1] if containers else None,
            # Localized display strings (for narrative / question text)
            "object_display": obj_display,
            "container_a_display": container_a_display,
            "container_b_display": container_b_display,
            "leave_activity": leave_activity,
            "leave_activity_display": leave_activity_display,
            "distractor_elements": distractor_elements,
            "observer": observer_info,
            "correct_answer": containers[0] if containers else None,
        }

        return scenario

    # ── distractor builder ──────────────────────────────────────────────

    def _build_distractors(self, count: int, obj_display: Optional[str]) -> List[str]:
        """Build ``count`` distractor sentences with correct articles."""
        lang = self.language
        d_objects = self._i18n.DISTRACTOR_OBJECTS.get(lang, self._i18n.DISTRACTOR_OBJECTS["en"])
        d_locations = self._i18n.DISTRACTOR_LOCATIONS.get(lang, self._i18n.DISTRACTOR_LOCATIONS["en"])
        d_template = self._i18n.DISTRACTOR_TEMPLATE.get(lang, self._i18n.DISTRACTOR_TEMPLATE["en"])

        # Filter out the scenario object from distractor pool
        def _word(entry):
            return entry["word"] if isinstance(entry, dict) else entry

        filtered = [o for o in d_objects if _word(o) != obj_display]
        if not filtered:
            filtered = d_objects

        results: List[str] = []
        for _ in range(count):
            d_o = random.choice(filtered)
            d_l = random.choice(d_locations)

            d_obj_word = _word(d_o)
            d_loc_word = _word(d_l)

            if lang in ("en", "zh", "ua"):
                results.append(d_template.format(d_obj=d_obj_word, d_loc=d_loc_word))
            else:
                # Resolve articles
                d_obj_g = d_o.get("gender", "m") if isinstance(d_o, dict) else "m"
                d_loc_g = d_l.get("gender", "m") if isinstance(d_l, dict) else "m"

                if lang == "es":
                    d_art = article("es", d_obj_g, definite=False)       # un / una
                    d_loc_art = article("es", d_loc_g, definite=True)    # el / la
                elif lang == "fr":
                    d_art = article("fr", d_obj_g, definite=False)       # un / une
                    d_loc_art = article("fr", d_loc_g, definite=True)    # le / la
                elif lang == "de":
                    d_art = article("de", d_obj_g, definite=False, case="acc")    # einen/eine/ein
                    d_loc_art = article("de", d_loc_g, definite=True, case="dat") # dem/der
                else:
                    d_art = ""
                    d_loc_art = ""

                results.append(d_template.format(
                    d_obj=d_obj_word, d_loc=d_loc_word,
                    d_art=d_art, d_loc_art=d_loc_art,
                ))
        return results

    # ── narrative / question builders ────────────────────────────────────

    def build_narrative(self, scenario: Dict[str, Any]) -> str:
        """
        Build narrative text from scenario using localized templates.

        Story structure:
        1. [Optional distractors]
        2. Subject A places object in container_a
        3. [Optional observer witnesses]
        4. Subject A leaves (doing leave_activity)
        5. Subject B moves object from container_a to container_b
        6. [Optional observer sees the move]
        7. Subject A returns
        """
        lang = self.language
        gender_a = _gender_code(scenario["subject_a_gender"])
        gender_b = _gender_code(scenario["subject_b_gender"])
        name_a = scenario["subject_a_name"]
        name_b = scenario["subject_b_name"]
        obj_key = scenario["object"]
        cont_a_key = scenario["container_a"]
        cont_b_key = scenario["container_b"]
        leave_activity = scenario["leave_activity_display"]

        # Pick gender-aware templates (UA/FR have m/f sub-dicts)
        templates_a = self._pick_narrative(gender_a)
        templates_b = self._pick_narrative(gender_b)

        # Pre-compute all substitution values
        fmt_place = self._narrative_vars_place(gender_a, obj_key, cont_a_key)
        fmt_move = self._narrative_vars_move(
            gender_b, obj_key, cont_a_key, cont_b_key, absent_gender=gender_a,
        )

        lines: List[str] = []

        # Add distractors if present
        if scenario["distractor_elements"]:
            lines.extend(scenario["distractor_elements"])
            lines.append("")  # Blank line for readability

        # Step 1: Subject A places object
        lines.append(templates_a["place"].format(
            name=name_a, leave_activity=leave_activity, **fmt_place,
        ))

        # Optional: Observer witnesses
        if scenario["observer"]:
            obs_name = scenario["observer"]["name"]
            obs_gender = _gender_code(scenario["observer"]["gender"])
            obs_templates = self._pick_narrative(obs_gender)
            lines.append(obs_templates["witness"].format(
                name=obs_name, name_a=name_a, **fmt_place,
            ))

        # Step 2: Subject A leaves
        lines.append(templates_a["leave"].format(
            name=name_a, leave_activity=leave_activity, **fmt_place,
        ))

        # Step 3: Subject B moves object (while A is absent)
        lines.append(templates_b["move"].format(
            name_a=name_a, name_b=name_b, **fmt_move,
        ))

        # Optional: Observer sees the move
        # witness_move: observer verb (бачив/бачила) agrees with observer gender;
        # mover verb (переклав/переклала) is in fmt_move via {moved} placeholder.
        if scenario["observer"]:
            obs_name = scenario["observer"]["name"]
            obs_gender = _gender_code(scenario["observer"]["gender"])
            obs_templates = self._pick_narrative(obs_gender)
            lines.append(obs_templates["witness_move"].format(
                name=obs_name, name_b=name_b, **fmt_move,
            ))

        # Step 4: Subject A returns
        lines.append(templates_a["return"].format(name=name_a))

        return "\n".join(lines)

    def _pick_narrative(self, gender: str) -> Dict[str, str]:
        """Select narrative templates for the given gender."""
        raw = self._i18n.NARRATIVE_TEMPLATES.get(
            self.language, self._i18n.NARRATIVE_TEMPLATES["en"]
        )
        # If sub-dicts by gender exist, pick the right one
        if isinstance(raw, dict) and gender in raw and isinstance(raw[gender], dict):
            return raw[gender]
        return raw

    def _narrative_vars_place(self, subj_gender: str, obj_key: str, cont_key: str) -> Dict[str, str]:
        """Build template variables for 'place' / 'witness' sentences."""
        lang = self.language
        obj_g = self._obj_gender(obj_key)
        cont_g = self._cont_gender(cont_key)
        poss = self._possessive(subj_gender, obj_key)

        v: Dict[str, str] = {
            "poss": poss,
            "obj": self._obj_word(obj_key),
            "container": self._cont_word(cont_key),
        }

        if lang == "ua":
            v["obj_acc"] = self._obj_word(obj_key, "acc")
            v["container_acc"] = self._cont_word(cont_key, "acc")

        if lang == "es":
            v["art_def_obj"] = article("es", obj_g, definite=True)
            v["art_def_cont"] = article("es", cont_g, definite=True)

        if lang == "fr":
            v["art_def"] = article("fr", cont_g, definite=True)
            v["art_def_obj"] = article("fr", obj_g, definite=True)

        if lang == "de":
            v["art_acc_obj"] = article("de", obj_g, definite=True, case="acc")
            v["art_acc_cont"] = article("de", cont_g, definite=True, case="acc")
            v["poss_acc"] = self._de_possessive(subj_gender, obj_key, case="acc")

        return v

    def _narrative_vars_move(self, subj_gender: str, obj_key: str,
                             cont_a_key: str, cont_b_key: str,
                             absent_gender: str = "m") -> Dict[str, str]:
        """Build template variables for 'move' / 'witness_move' sentences.

        ``absent_gender`` is the gender of the *absent* character (name_a),
        needed for French ``absent`` / ``absente``.
        """
        lang = self.language
        obj_g = self._obj_gender(obj_key)
        cont_a_g = self._cont_gender(cont_a_key)
        cont_b_g = self._cont_gender(cont_b_key)

        v: Dict[str, str] = {
            "obj": self._obj_word(obj_key),
            "container_a": self._cont_word(cont_a_key),
            "container_b": self._cont_word(cont_b_key),
        }

        if lang == "ua":
            v["obj_acc"] = self._obj_word(obj_key, "acc")
            v["container_a_gen"] = self._cont_word(cont_a_key, "gen")
            v["container_b_acc"] = self._cont_word(cont_b_key, "acc")
            v["container_b_gen"] = self._cont_word(cont_b_key, "gen")
            # Verbs in move/witness_move agree with name_b (the mover)
            mover_g = _gender_code(subj_gender)
            v["took"] = "\u0432\u0437\u044f\u0432" if mover_g == "m" else "\u0432\u0437\u044f\u043b\u0430"
            v["put"] = "\u043f\u043e\u043a\u043b\u0430\u0432" if mover_g == "m" else "\u043f\u043e\u043a\u043b\u0430\u043b\u0430"
            v["moved"] = "\u043f\u0435\u0440\u0435\u043a\u043b\u0430\u0432" if mover_g == "m" else "\u043f\u0435\u0440\u0435\u043a\u043b\u0430\u043b\u0430"

        if lang == "es":
            v["art_def_obj"] = article("es", obj_g, definite=True)
            v["prep_from"] = self._es_prep_from(cont_a_key)
            v["art_def_cont_b"] = article("es", cont_b_g, definite=True)
            v["pron_obj"] = self._es_obj_pronoun(obj_key)

        if lang == "fr":
            v["art_def_obj"] = article("fr", obj_g, definite=True)
            v["prep_from"] = self._fr_prep_from(cont_a_key)
            v["pron_obj"] = self._fr_obj_pronoun(obj_key)
            v["art_def_cont_b"] = article("fr", cont_b_g, definite=True)
            v["absent"] = "absent" if absent_gender == "m" else "absente"

        if lang == "de":
            v["art_acc_obj"] = article("de", obj_g, definite=True, case="acc")
            v["art_dat_cont_a"] = article("de", cont_a_g, definite=True, case="dat")
            v["art_acc_cont_b"] = article("de", cont_b_g, definite=True, case="acc")
            v["pron_obj"] = self._de_obj_pronoun(obj_key)

        return v

    def build_question(self, scenario: Dict[str, Any]) -> str:
        """
        Build the test question using a localized template.

        The question tests false belief: Where will Subject A LOOK for the object?
        """
        lang = self.language
        gender_a = _gender_code(scenario["subject_a_gender"])
        name_a = scenario["subject_a_name"]
        obj_key = scenario["object"]
        poss = self._possessive(gender_a, obj_key)

        # Pick gender-aware question template
        raw = self._i18n.QUESTION_TEMPLATES.get(lang, self._i18n.QUESTION_TEMPLATES["en"])
        if isinstance(raw, dict) and gender_a in raw:
            template = raw[gender_a]
        elif isinstance(raw, str):
            template = raw
        else:
            template = self._i18n.QUESTION_TEMPLATES["en"]

        fmt: Dict[str, str] = {
            "name": name_a,
            "poss": poss,
            "obj": self._obj_word(obj_key),
        }

        if lang == "ua":
            fmt["obj_acc"] = self._obj_word(obj_key, "acc")

        if lang == "de":
            fmt["poss_dat"] = self._de_possessive(gender_a, obj_key, case="dat")

        return template.format(**fmt)
