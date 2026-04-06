#!/usr/bin/env python3
"""
Linda Conjunction Fallacy Benchmark for LLMs
Based on Tversky & Kahneman's classic conjunction fallacy experiments

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the plugin-based architecture instead:

    from src.plugins import PluginRegistry
    plugin = PluginRegistry.get('linda_fallacy')
    generator = plugin.get_generator()
    parser = plugin.get_parser()
    evaluator = plugin.get_evaluator()

Or use the 3-stage pipeline:
    python src/stages/generate_testset.py configs/testsets/linda_config.yaml
    python src/stages/run_testset.py testset_*.json.gz --model <model>
    python src/stages/analyze_results.py results_*.json.gz
"""

import warnings
warnings.warn(
    "src.benchmarks.linda_eval is deprecated. "
    "Use the plugin-based architecture (src.plugins.linda_fallacy) "
    "or the 3-stage pipeline (src.stages) instead.",
    DeprecationWarning,
    stacklevel=2
)

import argparse
import ollama
import json
import random
import time
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import re

from src.plugins.linda_fallacy.i18n import (
    PERSONA_TEMPLATES,
    CONJUNCTION_CONNECTORS,
    ACTIVITIES_CONNECTORS,
    resolve_background_key,
    get_component_templates,
    get_distractor_pool,
)

@dataclass
class PersonaTemplate:
    """Template for generating Linda-style personas"""
    name: str
    age: int
    personality_traits: List[str]
    background: List[str]
    activities: List[str]
    culture: str # Added culture field

@dataclass
class TestItem:
    """Individual test item with options to rank"""
    description: str
    conjunction_item: str  # The item that combines two elements (trap item)
    component_a: str       # First component of conjunction
    component_b: str       # Second component of conjunction  
    distractors: List[str] # Other plausible options
    all_items: List[str]   # All items shuffled

@dataclass
class TestResult:
    """Results for a single test"""
    persona: PersonaTemplate
    test_item: TestItem
    model_response: str
    parsed_rankings: List[str]
    conjunction_rank: int
    component_a_rank: int
    component_b_rank: int
    fallacy_detected: bool
    confidence_score: float
    response_time: float
    timestamp: str

class LindaBenchmark:
    def __init__(self, ollama_host: str = "http://localhost:11434", language: str = "en", num_options: int = 8, culture_filter: Optional[str] = None):
        self.client = ollama.Client(host=ollama_host)
        self.language = language
        self.num_options = num_options
        self.culture_filter = culture_filter
        self.persona_templates = self._load_persona_templates()
        # Filter personas based on culture if specified
        if self.culture_filter:
             self.persona_templates = [p for p in self.persona_templates if p.culture == self.culture_filter]
             if not self.persona_templates:
                 print(f"Warning: No personas found for culture '{self.culture_filter}'. Using all personas.")

        # Define prompts in different languages (basic example)
        self.prompts = {
            "en": {
                "intro": "Consider the following description:",
                "instruction": "Based on this description, please rank the following statements from MOST probable (1) to LEAST probable ({num_options}):",
                "format": "Please provide your ranking as a numbered list, starting with the most probable option. Also, briefly explain your reasoning for the top 3 rankings.",
                "response_format": "RANKING:\n1. [most probable option]\n2. [second most probable]\n3. [third most probable]\n... (continue for all items)\n\nREASONING:\n[Your explanation for the top 3 choices]"
            },
            "es": {
                "intro": "Considere la siguiente descripción:",
                "instruction": "Basándose en esta descripción, por favor ordene las siguientes afirmaciones de MÁS probable (1) a MENOS probable ({num_options}):",
                "format": "Por favor, proporcione su clasificación como una lista numerada, comenzando con la opción más probable. Explique brevemente su razonamiento para las 3 primeras clasificaciones.",
                "response_format": "CLASIFICACIÓN:\n1. [opción más probable]\n2. [segunda más probable]\n3. [tercera más probable]\n... (continúe para todos los elementos)\n\nRAZONAMIENTO:\n[Su explicación para las 3 primeras opciones]"
            },
             "fr": {
                "intro": "Considérez la description suivante :",
                "instruction": "Sur la base de cette description, veuillez classer les affirmations suivantes de la PLUS probable (1) à la MOINS probable ({num_options}) :",
                "format": "Veuillez fournir votre classement sous forme de liste numérotée, en commençant par l'option la plus probable. Expliquez brièvement votre raisonnement pour les 3 premiers classements.",
                "response_format": "CLASSEMENT :\n1. [option la plus probable]\n2. [deuxième plus probable]\n3. [troisième plus probable]\n... (continuez pour tous les éléments)\n\nRAISONNEMENT :\n[Votre explication pour les 3 premiers choix]"
            },
            # Add more languages as needed
        }

    def _get_prompt_text(self, key: str) -> str:
        """Get localized prompt text."""
        return self.prompts.get(self.language, self.prompts["en"]).get(key, self.prompts["en"][key])
    def _load_persona_templates(self) -> List[PersonaTemplate]:
        """Load predefined persona templates for different cultures and languages"""
        # Base templates with English names/descriptions for logic, but tagged with culture/language
        templates = [
            # --- Western ---
            PersonaTemplate(
                name="Linda", # Classic name from the study
                age=31,
                personality_traits=["outspoken", "very bright", "deeply concerned with issues of discrimination and social justice"],
                background=["majored in philosophy", "as a student, she was deeply involved in anti-nuclear demonstrations"],
                activities=["read books on social issues", "attended rallies"],
                culture="western"
            ),
            PersonaTemplate(
                name="Alex",
                age=28,
                personality_traits=["outspoken", "very bright", "idealistic"],
                background=["majored in environmental science", "concerned with climate change"],
                activities=["participated in climate protests", "volunteers at animal shelter"],
                culture="western"
            ),
            PersonaTemplate(
                name="Jordan",
                age=32,
                personality_traits=["analytical", "introverted", "detail-oriented"],
                background=["studied computer science", "works in tech industry"],
                activities=["contributes to open source projects", "plays chess competitively"],
                culture="western"
            ),
            PersonaTemplate(
                name="Marie Dubois",
                age=33,
                personality_traits=["artistic", "independent", "politically active"],
                background=["studied fine arts", "involved in local politics"],
                activities=["paints murals", "attends philosophy meetups"],
                culture="european" # Western subgroup
            ),
             # --- East Asian ---
            PersonaTemplate(
                name="佐藤宏樹", # Sato Hiroshi
                age=30,
                personality_traits=["思慮深い", "勤勉", "集団の調和を重視"], # Thoughtful, hardworking, values group harmony
                background=["工学を学んだ", "大手企業で働いている"], # Studied engineering, works for a large corporation
                activities=["書道を習っている", "社内のチームビルディングに参加している"], # Practices calligraphy, participates in company team-building
                culture="east_asian"
            ),
            # --- South Asian ---
            PersonaTemplate(
                name="प्रिया शर्मा", # Priya Sharma
                age=27,
                personality_traits=["意志坚定", "家族志向", "創造的"], # Determined, family-oriented, creative
                background=["経営学を学んだ", "家族の店を手伝っている"], # Studied business administration, helps manage the family store
                activities=["地元の寺院の祭りに参加する", "子供に古典舞踊を教えている"], # Attends local temple festivals, teaches classical dance to children
                culture="south_asian"
            ),
            # --- African ---
            PersonaTemplate(
                name="Emeka Okafor", # Name kept as is, common anglophone African name
                age=29,
                personality_traits=["カリスマ的", "地域社会志向", "語り部への情熱"], # Charismatic, community-minded, passionate about storytelling
                background=["文学を学んだ", "コミュニティラジオで働いている"], # Studied literature, works in community radio
                activities=["地元の文化イベントを企画する", "伝統的な太鼓を演奏する"], # Organizes local cultural events, plays traditional drums
                culture="african"
            ),
             # --- Middle Eastern ---
            PersonaTemplate(
                name="أحمد المنصوري", # Ahmed Al-Mansouri
                age=35,
                personality_traits=["もてなし好き", "知識豊富", "伝統を尊重"], # Hospitable, knowledgeable, respects tradition
                background=["歴史を学んだ", "博物館のガイドをしている"], # Studied history, works as a museum guide
                activities=["遺産ツアーを案内する", "集まりで詩を朗詠する"], # Leads heritage tours, recites poetry at gatherings
                culture="middle_eastern"
            ),
            # --- Latin American (using Spanish/Portuguese names, descriptions in target language context) ---
            PersonaTemplate(
                name="Sofía Morales", # Common Latin name
                age=26,
                personality_traits=["apasionada", "comunitaria", "optimista"], # Passionate, community-oriented, optimistic
                background=["estudió comunicación social", "trabaja en una ONG ambiental"], # Studied social communication, works at an environmental NGO
                activities=["organiza ferias comunitarias", "baila salsa en su tiempo libre"], # Organizes community fairs, dances salsa in her free time
                culture="latin_american"
            ),
             # --- Additional Western (to show variety within culture) ---
            PersonaTemplate(
                name="Elena Vasquez",
                age=34,
                personality_traits=["disciplined", "health-conscious", "competitive"],
                background=["studied kinesiology", "former college athlete"],
                activities=["teaches yoga classes", "runs marathons"],
                culture="western" # Or could be "european"
            ),
            # Add more personas for other cultures (Scandinavian, Southeast Asian, etc.)...
        ]
        return templates

    def _generate_distractors(self, persona: PersonaTemplate, num_distractors: int) -> List[str]:
        """Generate distractor items based on persona and language.

        Uses the centralised ``i18n`` distractor pools.  English retains
        background-specific pools; all other languages use a generic pool.
        """
        lang = self.language or "en"
        bg_key = resolve_background_key(" ".join(persona.background))
        pool_templates = get_distractor_pool(lang, bg_key)

        # Substitute {name} in every template
        distractors_pool = [t.format(name=persona.name) for t in pool_templates]

        # Ensure we don't exceed the pool size
        sample_size = min(num_distractors, len(distractors_pool))
        # Handle case where num_distractors is 0 or pool is empty
        if sample_size <= 0:
             return []
        return random.sample(distractors_pool, sample_size)

    def generate_test_item(self, persona: PersonaTemplate) -> TestItem:
        """Generate a test item based on a persona.

        Uses ``i18n`` module for multilingual component statements,
        conjunction connectors, and persona descriptions.
        """
        lang = self.language or "en"

        # Create description using i18n persona template
        traits_str = ", ".join(persona.personality_traits)
        background_str = ". ".join(persona.background)
        activities_connector = ACTIVITIES_CONNECTORS.get(lang, ACTIVITIES_CONNECTORS["en"])
        activities_str = activities_connector.join(persona.activities)

        template = PERSONA_TEMPLATES.get(lang, PERSONA_TEMPLATES["en"])
        description = template.format(
            name=persona.name, age=persona.age,
            traits=traits_str, background=background_str, activities=activities_str,
        )

        # Resolve background keyword from persona data
        bg_key = resolve_background_key(background_str)

        # Get language-appropriate component statements
        comp = get_component_templates(lang, bg_key)
        component_a = comp["a"].format(name=persona.name)
        component_b = comp["b"].format(name=persona.name)

        # Build conjunction with language-appropriate connector
        connector = CONJUNCTION_CONNECTORS.get(lang, CONJUNCTION_CONNECTORS["en"])
        conjunction = f"{component_a}{connector}{component_b}"

        # Calculate number of distractors needed
        num_distractors = self.num_options - 3  # 3 items: A, B, A&B
        if num_distractors < 0:
            raise ValueError("Number of options must be at least 3")

        distractors = self._generate_distractors(persona, num_distractors)

        # Combine and shuffle all items
        all_items = [component_a, component_b, conjunction] + distractors
        random.shuffle(all_items)

        return TestItem(
            description=description,
            conjunction_item=conjunction,
            component_a=component_a,
            component_b=component_b,
            distractors=distractors,
            all_items=all_items
        )

    def create_prompt(self, test_item: TestItem) -> str:
        """Create the prompt for the LLM"""
        items_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(test_item.all_items)])

        prompt_text = self._get_prompt_text
        intro = prompt_text("intro")
        instruction = prompt_text("instruction").format(num_options=self.num_options)
        format_text = prompt_text("format")
        # response_format = prompt_text("response_format") # Not used in prompt, just for reference

        prompt = f"""{intro}

{test_item.description}

{instruction}

{items_list}

{format_text}"""

        return prompt

    def query_model(self, model_name: str, prompt: str) -> Tuple[str, float]:
        """Query the specified model via Ollama"""
        start_time = time.time()

        try:
            response = self.client.chat(
                model=model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.7,
                    'top_k': 40,
                    'min_k': 2,
                    'min_p': 0.1,
                    'num_ctx': 2048,
                    'num_predict': 1024,
                }
            )

            response_time = time.time() - start_time
            return response['message']['content'], response_time

        except Exception as e:
            print(f"Error querying model {model_name}: {e}")
            return f"ERROR: {str(e)}", time.time() - start_time

    def parse_response(self, response: str, test_item: TestItem) -> Tuple[List[str], bool, float]:
        """Parse the model's response to extract rankings and detect conjunction fallacy"""

        # Extract ranking section - More robust regex
        ranking_match = re.search(r'(?:RANKING|CLASIFICACIÓN|CLASSEMENT):\s*(.*?)(?=(?:REASONING|RAZONAMIENTO|RAISONNEMENT):|$)', response, re.DOTALL | re.IGNORECASE)
        if not ranking_match:
            # Fallback: Try to find a numbered list anywhere
            lines = response.split('\n')
            parsed_rankings = []
            for line in lines:
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    item_text = re.sub(r'^\d+\.\s*', '', line).strip()
                    parsed_rankings.append(item_text)
            if not parsed_rankings:
                 return [], False, 0.0
        else:
            ranking_text = ranking_match.group(1).strip()
            # Parse individual rankings
            parsed_rankings = []
            lines = ranking_text.split('\n')

            for line in lines:
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    # Extract the text after the number
                    item_text = re.sub(r'^\d+\.\s*', '', line).strip()
                    # Basic cleanup of common artifacts
                    item_text = re.sub(r'\s*\([^)]*\)\s*$', '', item_text) # Remove trailing (explanation)
                    parsed_rankings.append(item_text)

        if len(parsed_rankings) == 0: # No rankings found even with fallback
             return [], False, 0.0

        # Find positions of key items
        conjunction_rank = -1
        component_a_rank = -1
        component_b_rank = -1

        for i, ranked_item in enumerate(parsed_rankings):
            # Use a stricter matching for the conjunction itself
            if ranked_item == test_item.conjunction_item:
                 conjunction_rank = i + 1
            elif self._items_match(ranked_item, test_item.component_a):
                component_a_rank = i + 1
            elif self._items_match(ranked_item, test_item.component_b):
                component_b_rank = i + 1

        # Detect conjunction fallacy (conjunction ranked higher than *both* components if they exist)
        # Or ranked higher than at least one if the other is not found in the ranking
        fallacy_detected = False
        # Check if both components are ranked
        if component_a_rank > 0 and component_b_rank > 0 and conjunction_rank > 0:
            if conjunction_rank < component_a_rank and conjunction_rank < component_b_rank:
                fallacy_detected = True
        elif component_a_rank > 0 and conjunction_rank > 0:
             if conjunction_rank < component_a_rank:
                 fallacy_detected = True
        elif component_b_rank > 0 and conjunction_rank > 0:
             if conjunction_rank < component_b_rank:
                 fallacy_detected = True


        # Calculate a simple confidence score based on how clear the fallacy is
        confidence = 0.0
        if fallacy_detected and conjunction_rank > 0:
            # More confident if conjunction is ranked much higher than components
            if component_a_rank > 0:
                confidence = max(confidence, (component_a_rank - conjunction_rank) / self.num_options)
            if component_b_rank > 0:
                confidence = max(confidence, (component_b_rank - conjunction_rank) / self.num_options)

        return parsed_rankings, fallacy_detected, confidence

    def _items_match(self, item1: str, item2: str, threshold: float = 0.8) -> bool:
        """Check if two items match (allowing for minor formatting differences)"""
        # Normalize strings for comparison
        norm1 = re.sub(r'[^\w\s]', '', item1.lower()).strip()
        norm2 = re.sub(r'[^\w\s]', '', item2.lower()).strip()

        # Check for exact match first (important for conjunction)
        if norm1 == norm2:
            return True

        # Check for substantial overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if len(words1) == 0 or len(words2) == 0:
            return False

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union >= threshold # Adjusted threshold

    def run_single_test(self, model_name: str, persona: PersonaTemplate) -> TestResult:
        """Run a single test with the specified model and persona"""

        test_item = self.generate_test_item(persona)
        prompt = self.create_prompt(test_item)

        response, response_time = self.query_model(model_name, prompt)
        parsed_rankings, fallacy_detected, confidence = self.parse_response(response, test_item)

        # Find ranks for analysis
        conjunction_rank = -1
        component_a_rank = -1
        component_b_rank = -1

        for i, ranked_item in enumerate(parsed_rankings):
            if ranked_item == test_item.conjunction_item: # Strict match for conjunction
                conjunction_rank = i + 1
            elif self._items_match(ranked_item, test_item.component_a):
                component_a_rank = i + 1
            elif self._items_match(ranked_item, test_item.component_b):
                component_b_rank = i + 1

        return TestResult(
            persona=persona,
            test_item=test_item,
            model_response=response,
            parsed_rankings=parsed_rankings,
            conjunction_rank=conjunction_rank,
            component_a_rank=component_a_rank,
            component_b_rank=component_b_rank,
            fallacy_detected=fallacy_detected,
            confidence_score=confidence,
            response_time=response_time,
            timestamp=datetime.now().isoformat()
        )

    def run_benchmark(self, model_names: List[str], trials_per_model: int = 5, delay: float = 0.5) -> Dict[str, List[TestResult]]:
        """Run the full benchmark across multiple models"""

        results = {model: [] for model in model_names}

        for model_name in model_names:
            print(f"\nTesting model: {model_name}")

            # Use available personas, cycling if trials exceed persona count
            available_personas = self.persona_templates if self.persona_templates else [PersonaTemplate("Default", 30, ["default"], ["default background"], ["default activity"], "default")]
            num_personas = len(available_personas)

            for trial in range(trials_per_model):
                # Cycle through personas
                persona = available_personas[trial % num_personas]
                print(f"  Trial {trial + 1}/{trials_per_model} with {persona.name} ({persona.culture})...")

                try:
                    result = self.run_single_test(model_name, persona)
                    results[model_name].append(result)

                    if result.fallacy_detected:
                        print(f"    🚨 Conjunction fallacy detected! (Rank: {result.conjunction_rank}, confidence: {result.confidence_score:.2f})")
                    else:
                        print(f"    ✅ No fallacy detected")
                    if not result.parsed_rankings:
                         print(f"    ⚠️  Warning: Could not parse rankings from response.")

                except Exception as e:
                    print(f"    ❌ Error in trial {trial + 1}: {e}")

                # Brief pause between requests
                if delay > 0:
                     time.sleep(delay)

        return results

    def analyze_results(self, results: Dict[str, List[TestResult]]) -> Dict[str, Any]:
        """Analyze the benchmark results"""
        analysis = {}

        for model_name, model_results in results.items():
            if not model_results:
                continue

            total_tests = len(model_results)
            fallacies_detected = sum(1 for r in model_results if r.fallacy_detected)
            fallacy_rate = fallacies_detected / total_tests if total_tests > 0 else 0

            avg_response_time = sum(r.response_time for r in model_results) / total_tests if total_tests > 0 else 0
            avg_confidence = sum(r.confidence_score for r in model_results if r.fallacy_detected)
            if fallacies_detected > 0:
                avg_confidence /= fallacies_detected
            else:
                avg_confidence = 0

            parsing_failures = sum(1 for r in model_results if not r.parsed_rankings)
            parsing_success_rate = 1 - (parsing_failures / total_tests) if total_tests > 0 else 0

            # Analyze rank positions
            conjunction_ranks = [r.conjunction_rank for r in model_results if r.conjunction_rank > 0]
            component_a_ranks = [r.component_a_rank for r in model_results if r.component_a_rank > 0]
            component_b_ranks = [r.component_b_rank for r in model_results if r.component_b_rank > 0]

            avg_conjunction_rank = sum(conjunction_ranks) / len(conjunction_ranks) if conjunction_ranks else -1
            avg_component_a_rank = sum(component_a_ranks) / len(component_a_ranks) if component_a_ranks else -1
            avg_component_b_rank = sum(component_b_ranks) / len(component_b_ranks) if component_b_ranks else -1

            analysis[model_name] = {
                'total_tests': total_tests,
                'fallacy_rate': fallacy_rate,
                'fallacies_detected': fallacies_detected,
                'avg_response_time': avg_response_time,
                'avg_fallacy_confidence': avg_confidence,
                'parsing_success_rate': parsing_success_rate,
                'parsing_failures': parsing_failures,
                'avg_conjunction_rank': avg_conjunction_rank,
                'avg_component_a_rank': avg_component_a_rank,
                'avg_component_b_rank': avg_component_b_rank,
                'conjunction_ranks': conjunction_ranks, # Detailed data
                'component_a_ranks': component_a_ranks,
                'component_b_ranks': component_b_ranks
            }

        return analysis

    def save_results(self, results: Dict[str, List[TestResult]], filename: str = None):
        """Save results to JSON file"""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linda_benchmark_results_{timestamp}.json"

        # Convert results to serializable format
        serializable_results = {}
        for model_name, model_results in results.items():
            serializable_results[model_name] = []
            for result in model_results:
                # Convert dataclass to dict, handling nested dataclasses
                result_dict = asdict(result)
                # Persona and TestItem are also dataclasses, asdict handles them recursively
                serializable_results[model_name].append(result_dict)

        with open(filename, 'w', encoding='utf-8') as f: # Specify encoding
            json.dump(serializable_results, f, indent=2, ensure_ascii=False) # Ensure non-ascii chars are saved correctly

        print(f"\n💾 Results saved to: {filename}")
        return filename

def parse_arguments():
    """Parse command line arguments for shell scripting support"""
    parser = argparse.ArgumentParser(
        description="Linda Conjunction Fallacy Benchmark for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with default settings
  python linda_benchmark.py --models llama3.2:3b qwen2.5:7b

  # Test in Spanish with 15 options per question
  python linda_benchmark.py --models gemma2:9b --language es --num-options 15

  # Stress test with 20 options and specific culture
  python linda_benchmark.py --models qwen3:1.7b --num-options 20 --trials 20 --culture east_asian

  # Multi-language matrix test
  for lang in en es fr; do
    python linda_benchmark.py --models llama3.2:3b --language $lang --trials 5 --output "results_${lang}.json"
  done
        """
    )

    parser.add_argument(
        "--models", "-m", nargs="+", required=True,
        help="List of model names to test (e.g., llama3.2:3b qwen2.5:7b)"
    )

    parser.add_argument(
        "--language", "-l", default="en",
        choices=["en", "es", "fr", "de", "zh", "ja", "hi", "ar"],
        help="Language for prompts (default: en)"
    )

    parser.add_argument(
        "--num-options", "-n", type=int, default=8,
        help="Number of options in each test (3-20, default: 8)"
    )

    parser.add_argument(
        "--trials", "-t", type=int, default=10,
        help="Number of trials per model (default: 10)"
    )

    parser.add_argument(
        "--culture", "-c",
        choices=["western", "east_asian", "middle_eastern", "south_asian",
                "latin_american", "european", "african", "north_american",
                "scandinavian", "southeast_asian", "oceanic", "eastern_european"],
        help="Filter personas by culture (optional)"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output filename (default: auto-generated with timestamp)"
    )

    parser.add_argument(
        "--host", default="http://localhost:11434",
        help="Ollama host URL (default: http://localhost:11434)"
    )

    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--list-cultures", action="store_true",
        help="List available cultures and exit"
    )

    args = parser.parse_args()

    # Validate num_options range
    if args.num_options < 3 or args.num_options > 20:
        parser.error("--num-options must be between 3 and 20")

    return args

# Example usage and main function
if __name__ == "__main__":
    args = parse_arguments()

    # Handle special commands
    if args.list_cultures:
        cultures = ["western", "east_asian", "middle_eastern", "south_asian",
                   "latin_american", "european", "african", "north_american",
                   "scandinavian", "southeast_asian", "oceanic", "eastern_european"]
        print("Available cultures:")
        for culture in cultures:
            print(f"  {culture}")
        exit(0)

    # Initialize benchmark
    benchmark = LindaBenchmark(
        ollama_host=args.host,
        language=args.language,
        num_options=args.num_options,
        culture_filter=args.culture
    )

    print("🧠 Linda Conjunction Fallacy Benchmark")
    print("=" * 50)
    print(f"Language: {args.language}")
    print(f"Models: {', '.join(args.models)}")
    print(f"Options per test: {args.num_options}")
    print(f"Trials per model: {args.trials}")
    if args.culture:
        print(f"Culture filter: {args.culture}")
    print()

    if args.verbose:
        print("📊 Available personas:")
        for p in benchmark.persona_templates:
            print(f"  {p.name} ({p.age}, {p.culture}) - {', '.join(p.personality_traits[:2])}")
        print()

    # Run benchmark
    start_time = time.time()
    results = benchmark.run_benchmark(
        args.models,
        trials_per_model=args.trials,
        delay=args.delay
    )

    total_time = time.time() - start_time

    # Analyze results
    analysis = benchmark.analyze_results(results)

    # Print summary
    print("\n📊 BENCHMARK SUMMARY")
    print("=" * 50)

    for model_name, stats in analysis.items():
        print(f"\n🤖 {model_name}:")
        print(f"   Fallacy Rate: {stats['fallacy_rate']:.1%} ({stats['fallacies_detected']}/{stats['total_tests']})")
        print(f"   Avg Response Time: {stats['avg_response_time']:.2f}s")
        print(f"   Parsing Success: {stats['parsing_success_rate']:.1%}")
        if stats['avg_fallacy_confidence'] > 0:
            print(f"   Avg Fallacy Confidence: {stats['avg_fallacy_confidence']:.2f}")
        if stats['avg_conjunction_rank'] > 0:
             print(f"   Avg Conjunction Rank: {stats['avg_conjunction_rank']:.1f}")
             print(f"   Avg Component A Rank: {stats['avg_component_a_rank']:.1f}")
             print(f"   Avg Component B Rank: {stats['avg_component_b_rank']:.1f}")

    print(f"\n⏱️  Total benchmark time: {total_time:.1f}s")
    print(f"📝 Total tests conducted: {sum(stats['total_tests'] for stats in analysis.values())}")

    # Save results
    filename = benchmark.save_results(results, args.output)

    # Create analysis summary file
    analysis_filename = filename.replace('.json', '_analysis.json')
    analysis['benchmark_config'] = {
        'language': args.language,
        'num_options': args.num_options,
        'trials_per_model': args.trials,
        'culture_filter': args.culture,
        'total_time': total_time,
        'models_tested': args.models,
        'delay': args.delay
    }

    with open(analysis_filename, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"📈 Analysis saved to: {analysis_filename}")
    print("\n🎉 Benchmark completed!")
