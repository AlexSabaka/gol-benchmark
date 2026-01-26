"""
Step Builder for Object Tracking scenarios.

Generates step sequences for object tracking tests, including:
- Initial object placement in container at location
- Pre-inversion distractor steps
- Critical inversion step (container flips, object falls)
- Post-inversion container moves
- Post-inversion distractor steps
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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


# Template collections for generating diverse scenarios
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


class StepBuilder:
    """Builds object tracking scenarios with configurable complexity."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize with optional random seed for reproducibility."""
        self.rng = random.Random(seed)

    def _get_subject_possessive(self, subject: str) -> str:
        """Get possessive form for subject."""
        subject_lower = subject.lower()
        if subject_lower == 'i':
            return 'my'
        elif subject_lower == 'you':
            return 'your'
        else:
            # Assume it's a name
            return f"{subject}'s"

    def _format_subject(self, subject: str, capitalize: bool = True) -> str:
        """Format subject for sentence use."""
        if subject.lower() == 'i':
            return 'I'
        elif capitalize:
            return subject.capitalize()
        return subject

    def _fill_template(
        self,
        template: str,
        subject: str,
        **kwargs
    ) -> str:
        """Fill a template with variables."""
        possessive = self._get_subject_possessive(subject)
        formatted_subject = self._format_subject(subject)

        return template.format(
            subject=formatted_subject,
            possessive=possessive,
            **kwargs
        )

    def _create_placement_step(
        self,
        subject: str,
        obj: str,
        container: str,
        location: str
    ) -> ScenarioStep:
        """Create the initial placement step."""
        template = self.rng.choice(PLACEMENT_TEMPLATES)
        description = self._fill_template(
            template,
            subject,
            object=obj,
            container=container,
            location=location
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
        """
        Create the inversion step.

        Returns:
            Tuple of (step, new_object_location)
        """
        template = self.rng.choice(INVERSION_TEMPLATES)
        description = self._fill_template(
            template,
            subject,
            container=container
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
        template = self.rng.choice(MOVE_TEMPLATES)
        description = self._fill_template(
            template,
            subject,
            container=container,
            location=new_location
        )

        return ScenarioStep(
            step_number=step_number,
            action_type='move',
            description=description,
            affects_object=False,  # Object no longer in container (after inversion)
            object_location_after=object_location  # Object stays where it fell
        )

    def _create_interact_step(
        self,
        subject: str,
        appliance: str,
        step_number: int,
        object_location: str
    ) -> ScenarioStep:
        """Create an interaction step with an appliance."""
        template = self.rng.choice(INTERACT_TEMPLATES)
        description = self._fill_template(
            template,
            subject,
            appliance=appliance
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
        templates = DISTRACTOR_TEMPLATES.get(distractor_type, DISTRACTOR_TEMPLATES['irrelevant'])
        template = self.rng.choice(templates)

        # Fill in template variables
        description = self._fill_template(
            template,
            subject,
            time=self.rng.choice(TIMES),
            number=self.rng.choice(NUMBERS),
            room=self.rng.choice(ROOMS),
            nearby_object=self.rng.choice(NEARBY_OBJECTS),
            location=self.rng.choice(ROOMS)
        )

        return ScenarioStep(
            step_number=step_number,
            action_type='distractor',
            description=description,
            affects_object=False,
            object_location_after=object_location
        )

    def _pick_new_location(self, current_location: str, initial_location: str) -> str:
        """Pick a new location different from current and initial."""
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
        """Generate the question about object location."""
        template = self.rng.choice(QUESTION_TEMPLATES)
        return template.format(object=obj)
