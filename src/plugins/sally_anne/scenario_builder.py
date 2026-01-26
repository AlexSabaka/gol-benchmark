"""
Sally-Anne Scenario Builder

Generates false belief test scenarios with:
- Random subject names with proper gender-based pronouns
- Object placement and transfer during absence
- Optional observer (third person witness)
- Distractor elements
"""

import random
from typing import Dict, List, Tuple, Any, Optional

# Import names library for random name generation
try:
    import names
    NAMES_AVAILABLE = True
except ImportError:
    NAMES_AVAILABLE = False
    # Fallback name lists if names library not available
    MALE_NAMES = ['Alex', 'Ben', 'Charlie', 'David', 'Ethan', 'Frank', 'George', 'Henry']
    FEMALE_NAMES = ['Alice', 'Beth', 'Clara', 'Diana', 'Emma', 'Fiona', 'Grace', 'Hannah']


class SallyAnneScenarioBuilder:
    """Builds Sally-Anne false belief test scenarios."""
    
    def __init__(self):
        self.pronoun_map = {
            'male': {'subject': 'he', 'object': 'him', 'possessive': 'his'},
            'female': {'subject': 'she', 'object': 'her', 'possessive': 'her'},
        }
    
    def generate_random_name(self, gender: str) -> str:
        """Generate a random name for the given gender."""
        if NAMES_AVAILABLE:
            if gender == 'male':
                return names.get_first_name(gender='male')
            else:
                return names.get_first_name(gender='female')
        else:
            # Fallback to predefined lists
            if gender == 'male':
                return random.choice(MALE_NAMES)
            else:
                return random.choice(FEMALE_NAMES)
    
    def get_pronouns(self, gender: str) -> Dict[str, str]:
        """Get pronouns for the given gender."""
        return self.pronoun_map.get(gender, self.pronoun_map['female'])
    
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
            obj: Object to be moved
            containers: (container_a, container_b) tuple
            leave_activity: What subject A does when leaving
            distractor_count: Number of distractor elements
            include_observer: Whether to include a third-person observer
            seed: Random seed for reproducibility
            
        Returns:
            Scenario dictionary with:
            - subject_a_name, subject_a_gender, subject_a_pronouns
            - subject_b_name, subject_b_gender, subject_b_pronouns
            - object
            - container_a (initial/belief location)
            - container_b (actual location after move)
            - leave_activity
            - observer_name, observer_gender (if include_observer=True)
            - distractor_elements (if distractor_count > 0)
            - correct_answer (container_a - the belief location)
        """
        if seed is not None:
            random.seed(seed)
        
        # Generate or use provided subject pair
        if subject_pair:
            name_a, gender_a, name_b, gender_b = subject_pair
        else:
            # Generate random names with random genders
            gender_a = random.choice(['male', 'female'])
            gender_b = random.choice(['male', 'female'])
            name_a = self.generate_random_name(gender_a)
            name_b = self.generate_random_name(gender_b)
            # Ensure different names
            while name_b == name_a:
                name_b = self.generate_random_name(gender_b)
        
        # Get pronouns
        pronouns_a = self.get_pronouns(gender_a)
        pronouns_b = self.get_pronouns(gender_b)
        
        # Generate distractor elements if requested
        distractor_elements = []
        if distractor_count > 0:
            distractor_objects = ['book', 'cup', 'pencil', 'paper', 'phone', 'wallet', 'keys', 'hat']
            distractor_locations = ['table', 'shelf', 'chair', 'counter', 'desk', 'window']
            
            for _ in range(distractor_count):
                d_obj = random.choice([o for o in distractor_objects if o != obj])
                d_loc = random.choice(distractor_locations)
                distractor_elements.append(f"There is a {d_obj} on the {d_loc}.")
        
        # Generate observer if requested
        observer_info = None
        if include_observer:
            observer_gender = random.choice(['male', 'female'])
            observer_name = self.generate_random_name(observer_gender)
            # Ensure different from subjects
            while observer_name in [name_a, name_b]:
                observer_name = self.generate_random_name(observer_gender)
            observer_pronouns = self.get_pronouns(observer_gender)
            observer_info = {
                'name': observer_name,
                'gender': observer_gender,
                'pronouns': observer_pronouns,
            }
        
        scenario = {
            'subject_a_name': name_a,
            'subject_a_gender': gender_a,
            'subject_a_pronouns': pronouns_a,
            'subject_b_name': name_b,
            'subject_b_gender': gender_b,
            'subject_b_pronouns': pronouns_b,
            'object': obj,
            'container_a': containers[0],  # Initial/belief location
            'container_b': containers[1],  # Actual location after move
            'leave_activity': leave_activity,
            'distractor_elements': distractor_elements,
            'observer': observer_info,
            'correct_answer': containers[0],  # CRITICAL: Answer is belief location (container_a)
        }
        
        return scenario
    
    def build_narrative(self, scenario: Dict[str, Any]) -> str:
        """
        Build narrative text from scenario.
        
        This creates the story structure:
        1. [Optional distractors]
        2. Subject A places object in container_a
        3. [Optional observer witnesses]
        4. Subject A leaves (doing leave_activity)
        5. Subject B moves object from container_a to container_b
        6. Subject A returns
        """
        name_a = scenario['subject_a_name']
        name_b = scenario['subject_b_name']
        pronouns_a = scenario['subject_a_pronouns']
        pronouns_b = scenario['subject_b_pronouns']
        obj = scenario['object']
        container_a = scenario['container_a']
        container_b = scenario['container_b']
        leave_activity = scenario['leave_activity']
        
        lines = []
        
        # Add distractors if present
        if scenario['distractor_elements']:
            lines.extend(scenario['distractor_elements'])
            lines.append("")  # Blank line for readability
        
        # Step 1: Subject A places object
        lines.append(f"{name_a} puts {pronouns_a['possessive']} {obj} in the {container_a}.")
        
        # Optional: Observer witnesses
        if scenario['observer']:
            obs_name = scenario['observer']['name']
            obs_pronouns = scenario['observer']['pronouns']
            lines.append(f"{obs_name} watches {name_a} put the {obj} in the {container_a}.")
        
        # Step 2: Subject A leaves
        lines.append(f"{name_a} {leave_activity}.")
        
        # Step 3: Subject B moves object (while A is absent)
        lines.append(f"While {name_a} is away, {name_b} takes the {obj} from the {container_a} and puts it in the {container_b}.")
        
        # Optional: Observer sees the move
        if scenario['observer']:
            obs_name = scenario['observer']['name']
            lines.append(f"{obs_name} sees {name_b} move the {obj} to the {container_b}.")
        
        # Step 4: Subject A returns
        lines.append(f"{name_a} returns.")
        
        return "\n".join(lines)
    
    def build_question(self, scenario: Dict[str, Any]) -> str:
        """
        Build the test question.
        
        The question tests false belief: Where will Subject A LOOK for the object?
        (Not where it actually is, but where A believes it is)
        """
        name_a = scenario['subject_a_name']
        obj = scenario['object']
        pronouns_a = scenario['subject_a_pronouns']
        
        return f"Where will {name_a} look for {pronouns_a['possessive']} {obj}?"
