#!/usr/bin/env python3
"""
Refactored GRPO training for polynomial factorization with proper pre-training.
Key improvements:
1. Pre-training phase on mathematical expressions
2. Efficient memmap dataset loading
3. Proper GRPO implementation with group baselines
4. Curriculum learning strategy
5. Better model architecture for math reasoning
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from tqdm import tqdm
import logging
from sympy import symbols, expand, solve, Eq, factor, sympify, latex
import re
import pickle

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for training phases"""
    # Model architecture
    vocab_size: int = 50257  # GPT-2 tokenizer size
    n_positions: int = 128
    n_embd: int = 256        # Larger embedding for better math representation
    n_layer: int = 6         # Fewer layers but wider
    n_head: int = 8
    
    # Pre-training config
    pretrain_epochs: int = 1
    pretrain_batch_size: int = 32
    pretrain_lr: float = 5e-5
    
    # GRPO config
    grpo_episodes: int = 10000
    grpo_batch_size: int = 16
    grpo_group_size: int = 8  # Proper GRPO group size
    grpo_lr: float = 5e-5
    
    # Dataset config
    dataset_size: int = 32000
    max_degree: int = 3
    curriculum_stages: int = 3
    
    # Paths
    data_dir: str = "data"
    checkpoint_dir: str = "checkpoints"
    
    # Device optimization
    use_compile: bool = False  # torch.compile for faster training

class MathTokenizer:
    """Enhanced tokenizer for mathematical expressions"""
    
    def __init__(self, base_tokenizer):
        self.base_tokenizer = base_tokenizer
        # Add mathematical special tokens
        self.math_tokens = {
            'FACTOR_START': '<|factor_start|>',
            'FACTOR_END': '<|factor_end|>', 
            'EQUALS': '<|equals|>',
            'PLUS': '<|plus|>',
            'MINUS': '<|minus|>',
            'MULTIPLY': '<|multiply|>',
            'POWER': '<|power|>',
            'LPAREN': '<|lparen|>',
            'RPAREN': '<|rparen|>',
        }
        
        # Add tokens to tokenizer vocabulary if not present
        new_tokens = []
        for token in self.math_tokens.values():
            if token not in self.base_tokenizer.get_vocab():
                new_tokens.append(token)
        
        if new_tokens:
            self.base_tokenizer.add_tokens(new_tokens)
        
        self.pad_token = self.base_tokenizer.eos_token
        self.base_tokenizer.pad_token = self.pad_token
        
    def encode_math_expression(self, expr) -> str:
        """Convert mathematical expression to tokenizer-friendly format"""
        def encode_single(expr_str):
            # Replace mathematical symbols with special tokens
            expr_str = expr_str.replace('=', f" {self.math_tokens['EQUALS']} ")
            expr_str = expr_str.replace('+', f" {self.math_tokens['PLUS']} ")
            expr_str = expr_str.replace('-', f" {self.math_tokens['MINUS']} ")
            expr_str = expr_str.replace('**', f" {self.math_tokens['POWER']} ")
            expr_str = expr_str.replace('*', f" {self.math_tokens['MULTIPLY']} ")
            expr_str = expr_str.replace('(', f" {self.math_tokens['LPAREN']} ")
            expr_str = expr_str.replace(')', f" {self.math_tokens['RPAREN']} ")
            
            # Clean up extra spaces
            return ' '.join(expr_str.split())

        if isinstance(expr, list):
            return [encode_single(e) for e in expr]
        elif isinstance(expr, str):
            return encode_single(expr)
        else:
            raise TypeError()
    
    def encode(self, text: str, **kwargs) -> Dict[str, torch.Tensor]:
        """Encode text with math-aware preprocessing"""
        processed_text = self.encode_math_expression(text)
        return self.base_tokenizer(processed_text, **kwargs)
    
    def decode(self, token_ids, **kwargs) -> str:
        """Decode tokens and clean up math formatting"""
        text = self.base_tokenizer.decode(token_ids, **kwargs)
        # Convert back to standard math notation
        for symbol, token in self.math_tokens.items():
            if symbol == 'EQUALS':
                text = text.replace(token, '=')
            elif symbol == 'PLUS':
                text = text.replace(token, '+')
            elif symbol == 'MINUS':
                text = text.replace(token, '-')
            elif symbol == 'MULTIPLY':
                text = text.replace(token, '*')
            elif symbol == 'POWER':
                text = text.replace(token, '**')
            elif symbol == 'LPAREN':
                text = text.replace(token, '(')
            elif symbol == 'RPAREN':
                text = text.replace(token, ')')
        
        return text.strip()


class PolynomialDataGenerator:
    """Advanced polynomial data generator with curriculum learning"""
    
    def __init__(self, config: TrainingConfig, seed: int = 42):
        self.config = config
        random.seed(seed)
        np.random.seed(seed)
        self.x = symbols('x')
        
    def generate_polynomial_problems(self, num_samples: int, degree: int, 
                                   integer_roots: bool = True) -> List[Dict[str, Any]]:
        """Generate polynomial factoring problems"""
        problems = []
        
        for _ in range(num_samples):
            if integer_roots:
                # Generate integer roots for easier learning
                roots = []
                for _ in range(degree):
                    root = random.randint(-10, 10)
                    if root not in roots:  # Avoid duplicate roots
                        roots.append(root)
                
                # Handle case where we couldn't generate enough unique roots
                while len(roots) < degree:
                    roots.append(random.randint(-10, 10))
            else:
                # Generate rational roots for harder problems
                roots = [random.randint(-10, 10) / random.randint(1, 3) for _ in range(degree)]
            
            # Create polynomial from roots
            factors = [self.x - root for root in roots]
            expanded_poly = expand(np.prod(factors) if len(factors) > 0 else 1)
            
            # Create factored form string
            factored_form = ' * '.join([f"(x - {root})" if root >= 0 else f"(x + {abs(root)})" for root in roots])
            
            problems.append({
                'expanded': str(expanded_poly),
                'factored': factored_form,
                'roots': roots,
                'degree': degree,
                'difficulty': 'easy' if integer_roots else 'hard'
            })
            
        return problems
    
    def generate_pretraining_data(self) -> List[str]:
        """Generate pre-training data for mathematical reasoning"""
        pretraining_examples = []
        
        # Basic arithmetic
        for _ in range(self.config.dataset_size // 4):
            a, b = random.randint(-100, 100), random.randint(-100, 100)
            pretraining_examples.extend([
                f"{a} + {b} = {a + b}",
                f"{a} - {b} = {a - b}",
                f"{a} * {b} = {a * b}",
            ])
        
        # Polynomial expansion examples
        for degree in range(1, self.config.max_degree + 1):
            problems = self.generate_polynomial_problems(
                self.config.dataset_size // (4 * self.config.max_degree), 
                degree
            )
            for prob in problems:
                pretraining_examples.append(f"Expand: {prob['factored']} = {prob['expanded']}")
        
        return pretraining_examples
    
    def generate_grpo_dataset(self) -> List[Dict[str, Any]]:
        """Generate dataset specifically for GRPO training"""
        dataset = []
        
        # Curriculum learning: start with lower degrees
        for stage in range(self.config.curriculum_stages):
            degree = min(stage + 1, self.config.max_degree)
            stage_size = self.config.dataset_size // self.config.curriculum_stages
            
            # Mix of easy and hard problems
            easy_problems = self.generate_polynomial_problems(
                stage_size // 2, degree, integer_roots=True
            )
            hard_problems = self.generate_polynomial_problems(
                stage_size // 2, degree, integer_roots=False
            )
            
            for prob in easy_problems + hard_problems:
                dataset.append({
                    'prompt': f"Factor: {prob['expanded']} =",
                    'target': prob['factored'],
                    'roots': prob['roots'],
                    'degree': prob['degree'],
                    'difficulty': prob['difficulty'],
                    'stage': stage
                })
        
        return dataset


class MemmapDataset(Dataset):
    """Memory-mapped dataset for efficient loading"""
    
    def __init__(self, data_path: str, tokenizer: MathTokenizer, max_length: int = 128):
        self.data_path = Path(data_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Load metadata
        with open(self.data_path / "metadata.json", 'r') as f:
            self.metadata = json.load(f)
        
        self.length = self.metadata['length']
        
        # Memory-map the data
        self.data_mmap = np.memmap(
            self.data_path / "data.dat", 
            dtype=np.int64, 
            mode='r',
            shape=(self.length, max_length)
        )
        
        self.attention_mmap = np.memmap(
            self.data_path / "attention.dat",
            dtype=np.int64,
            mode='r', 
            shape=(self.length, max_length)
        )
    
    def __len__(self):
        return self.length
    
    def __getitem__(self, idx):
        return {
            'input_ids': torch.from_numpy(self.data_mmap[idx].copy()),
            'attention_mask': torch.from_numpy(self.attention_mmap[idx].copy())
        }


class PreTrainer:
    """Pre-training phase for mathematical reasoning"""
    
    def __init__(self, model: nn.Module, tokenizer: MathTokenizer, config: TrainingConfig):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=config.pretrain_lr)
        
        # Compile model for faster training if available
        if self.config.use_compile and hasattr(torch, 'compile'):
            self.model = torch.compile(self.model)
    
    def prepare_pretraining_data(self, force_regenerate: bool = False):
        """Prepare and save pre-training data to memmap"""
        data_path = Path(self.config.data_dir) / "pretrain"
        data_path.mkdir(parents=True, exist_ok=True)
        
        if (data_path / "metadata.json").exists() and not force_regenerate:
            logger.info("Pre-training data already exists, skipping generation")
            return str(data_path)
        
        logger.info("Generating pre-training data...")
        generator = PolynomialDataGenerator(self.config)
        examples = generator.generate_pretraining_data()
        
        # Tokenize all examples
        tokenized_data = []
        attention_masks = []
        
        for example in tqdm(examples, desc="Tokenizing"):
            encoded = self.tokenizer.encode(
                example,
                max_length=self.config.n_positions,
                padding='max_length',
                truncation=True,
                return_tensors='pt',
                return_attention_mask=True
            )
            
            tokenized_data.append(encoded['input_ids'].squeeze().numpy())
            attention_masks.append(encoded['attention_mask'].squeeze().numpy())
        
        # Save to memmap
        data_array = np.array(tokenized_data, dtype=np.int64)
        attention_array = np.array(attention_masks, dtype=np.int64)
        
        data_mmap = np.memmap(
            data_path / "data.dat",
            dtype=np.int64,
            mode='w+',
            shape=data_array.shape
        )
        data_mmap[:] = data_array
        del data_mmap
        
        attention_mmap = np.memmap(
            data_path / "attention.dat", 
            dtype=np.int64,
            mode='w+',
            shape=attention_array.shape
        )
        attention_mmap[:] = attention_array
        del attention_mmap
        
        # Save metadata
        metadata = {
            'length': len(examples),
            'max_length': self.config.n_positions,
            'vocab_size': self.config.vocab_size
        }
        
        with open(data_path / "metadata.json", 'w') as f:
            json.dump(metadata, f)
        
        logger.info(f"Saved {len(examples)} pre-training examples to {data_path}")
        return str(data_path)
    
    def train(self, device: torch.device):
        """Run pre-training phase"""
        logger.info("Starting pre-training phase...")
        
        # Prepare data
        data_path = self.prepare_pretraining_data()
        dataset = MemmapDataset(data_path, self.tokenizer, self.config.n_positions)
        dataloader = DataLoader(
            dataset, 
            batch_size=self.config.pretrain_batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        self.model.train()
        
        for epoch in range(self.config.pretrain_epochs):
            total_loss = 0
            num_batches = 0
            
            pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{self.config.pretrain_epochs}")
            
            for batch in pbar:
                input_ids = batch['input_ids'].to(device, non_blocking=True)
                attention_mask = batch['attention_mask'].to(device, non_blocking=True)
                
                # Shift for causal language modeling
                labels = input_ids.clone()
                labels[attention_mask == 0] = -100  # Ignore padding tokens
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                    return_dict=True
                )
                
                loss = outputs.loss
                
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                
                total_loss += loss.item()
                num_batches += 1
                
                pbar.set_postfix({'loss': f"{loss.item():.4f}"})
            
            avg_loss = total_loss / num_batches
            logger.info(f"Epoch {epoch+1} completed. Average loss: {avg_loss:.4f}")
            
            # Save checkpoint
            if (epoch + 1) % 10 == 0:
                checkpoint_path = Path(self.config.checkpoint_dir) / f"pretrain_epoch_{epoch+1}.pt"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'loss': avg_loss,
                }, checkpoint_path)
                logger.info(f"Checkpoint saved: {checkpoint_path}")


class AdvancedRewardCalculator:
    """More sophisticated reward calculation for polynomial factoring"""
    
    def __init__(self):
        self.x = symbols('x')
    
    def parse_factored_form(self, text: str) -> List[str]:
        """Parse factored form with better regex matching"""
        # Remove "Factor:" prefix if present
        text = re.sub(r'^.*?=\s*', '', text)
        
        # Extract factors in parentheses
        factor_pattern = r'\([^)]+\)'
        factors = re.findall(factor_pattern, text)
        
        return factors
    
    def evaluate_factorization(self, prediction: str, target_roots: List[float]) -> float:
        """Evaluate factorization quality with multiple criteria"""
        predicted_factors = self.parse_factored_form(prediction)
        
        if not predicted_factors:
            return 0.0
        
        # Convert target roots to expected factor strings
        expected_factors = []
        for root in target_roots:
            if root >= 0:
                expected_factors.append(f"(x - {int(root)})" if root == int(root) else f"(x - {root})")
            else:
                expected_factors.append(f"(x + {int(abs(root))})" if root == int(root) else f"(x + {abs(root)})")
        
        # Scoring components
        factor_count_score = 1.0 if len(predicted_factors) == len(expected_factors) else 0.5
        
        # Check for exact matches
        exact_matches = sum(1 for pf in predicted_factors if pf in expected_factors)
        exact_match_score = exact_matches / len(expected_factors) if expected_factors else 0.0
        
        # Try to parse and verify algebraically
        try:
            # Reconstruct polynomial from predicted factors
            parsed_factors = []
            for factor_str in predicted_factors:
                # Simple parsing - could be more robust
                factor_str = factor_str.strip('()')
                if 'x' in factor_str:
                    parsed_factors.append(sympify(factor_str))
            
            if parsed_factors:
                reconstructed = expand(np.prod(parsed_factors))
                # Compare with target polynomial
                target_poly = expand(np.prod([self.x - root for root in target_roots]))
                algebraic_score = 1.0 if reconstructed.equals(target_poly) else 0.0
            else:
                algebraic_score = 0.0
                
        except:
            algebraic_score = 0.0
        
        # Weighted combination
        final_score = (
            0.3 * factor_count_score +
            0.4 * exact_match_score + 
            0.3 * algebraic_score
        )
        
        return final_score


class GRPOTrainer:
    """Proper GRPO implementation with group baselines"""
    
    def __init__(self, model: nn.Module, reference_model: nn.Module, 
                 tokenizer: MathTokenizer, config: TrainingConfig):
        self.model = model
        self.reference_model = reference_model
        self.tokenizer = tokenizer
        self.config = config
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=config.grpo_lr)
        self.reward_calculator = AdvancedRewardCalculator()
        
        # Compile for performance
        if self.config.use_compile and hasattr(torch, 'compile'):
            self.model = torch.compile(self.model)
    
    def prepare_grpo_data(self, force_regenerate: bool = False):
        """Prepare GRPO training data"""
        data_path = Path(self.config.data_dir) / "grpo"
        data_path.mkdir(parents=True, exist_ok=True)
        
        if (data_path / "grpo_data.pkl").exists() and not force_regenerate:
            logger.info("GRPO data already exists, loading...")
            with open(data_path / "grpo_data.pkl", 'rb') as f:
                return pickle.load(f)
        
        logger.info("Generating GRPO data...")
        generator = PolynomialDataGenerator(self.config)
        dataset = generator.generate_grpo_dataset()
        
        # Save dataset
        with open(data_path / "grpo_data.pkl", 'wb') as f:
            pickle.dump(dataset, f)
        
        logger.info(f"Generated {len(dataset)} GRPO examples")
        return dataset
    
    def generate_responses(self, prompts: List[str], device: torch.device) -> Tuple[List[str], torch.Tensor]:
        """Generate responses for a batch of prompts"""
        # Tokenize prompts
        encoded = self.tokenizer.encode(
            prompts,
            padding=True,
            truncation=True,
            max_length=64,  # Shorter for prompts
            return_tensors='pt'
        )
        
        input_ids = encoded['input_ids'].to(device)
        attention_mask = encoded['attention_mask'].to(device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=32,
                min_new_tokens=8,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                pad_token_id=self.tokenizer.base_tokenizer.pad_token_id,
                use_cache=True
            )
        
        # Extract only the generated part
        generated_ids = outputs[:, input_ids.shape[1]:]
        
        # Decode responses
        responses = []
        for ids in generated_ids:
            response = self.tokenizer.decode(ids, skip_special_tokens=True)
            responses.append(response)
        
        return responses, generated_ids
    
    def calculate_log_probs(self, input_ids: torch.Tensor, generated_ids: torch.Tensor, 
                          attention_mask: torch.Tensor, device: torch.device) -> torch.Tensor:
        """Calculate log probabilities for generated sequences"""
        # Combine input and generated tokens
        full_input_ids = torch.cat([input_ids, generated_ids], dim=1)
        
        # Extend attention mask
        gen_attention = torch.ones_like(generated_ids, dtype=attention_mask.dtype)
        full_attention_mask = torch.cat([attention_mask, gen_attention], dim=1)
        
        # Forward pass
        outputs = self.model(
            input_ids=full_input_ids,
            attention_mask=full_attention_mask,
            return_dict=True,
            use_cache=False
        )
        
        logits = outputs.logits
        
        # Calculate log probs for generated tokens only
        gen_start_idx = input_ids.shape[1]
        gen_logits = logits[:, gen_start_idx-1:-1]  # Shift for next token prediction
        
        log_probs = F.log_softmax(gen_logits, dim=-1)
        
        # Gather log probs for actual generated tokens
        token_log_probs = log_probs.gather(-1, generated_ids.unsqueeze(-1)).squeeze(-1)
        
        # Sum over sequence length
        sequence_log_probs = token_log_probs.sum(dim=1)
        
        return sequence_log_probs
    
    def train(self, device: torch.device):
        """Run GRPO training"""
        logger.info("Starting GRPO training phase...")
        
        dataset = self.prepare_grpo_data()
        self.model.train()
        self.reference_model.eval()
        
        pbar = tqdm(range(self.config.grpo_episodes), desc="GRPO Training")
        
        for episode in pbar:
            # Sample batch
            batch_samples = random.sample(dataset, self.config.grpo_batch_size)
            prompts = [sample['prompt'] for sample in batch_samples]
            
            # Group sampling for GRPO
            group_rewards = []
            group_log_probs = []
            
            for group_idx in range(0, len(batch_samples), self.config.grpo_group_size):
                group_end = min(group_idx + self.config.grpo_group_size, len(batch_samples))
                group_prompts = prompts[group_idx:group_end]
                group_samples = batch_samples[group_idx:group_end]
                
                # Generate responses for group
                responses, generated_ids = self.generate_responses(group_prompts, device)
                
                # Calculate rewards for group
                rewards = []
                for i, (response, sample) in enumerate(zip(responses, group_samples)):
                    reward = self.reward_calculator.evaluate_factorization(
                        response, sample['roots']
                    )
                    rewards.append(reward)
                
                rewards_tensor = torch.tensor(rewards, device=device, dtype=torch.float32)
                group_rewards.extend(rewards)
                
                # Calculate log probabilities
                encoded_prompts = self.tokenizer.encode(
                    group_prompts,
                    padding=True,
                    truncation=True,
                    max_length=64,
                    return_tensors='pt'
                )
                
                input_ids = encoded_prompts['input_ids'].to(device)
                attention_mask = encoded_prompts['attention_mask'].to(device)
                
                log_probs = self.calculate_log_probs(
                    input_ids, generated_ids, attention_mask, device
                )
                
                group_log_probs.extend(log_probs)
                
                # GRPO: Use group mean as baseline (key innovation)
                group_baseline = rewards_tensor.mean()
                group_advantages = rewards_tensor - group_baseline
                
                # Apply advantages to log probs
                policy_loss = -(group_advantages * log_probs).mean()
                
                # Add KL regularization with reference model
                with torch.no_grad():
                    ref_outputs = self.reference_model(
                        input_ids=torch.cat([input_ids, generated_ids], dim=1),
                        attention_mask=torch.cat([
                            attention_mask, 
                            torch.ones_like(generated_ids)
                        ], dim=1)
                    )
                    ref_logits = ref_outputs.logits[:, input_ids.shape[1]-1:-1]
                    ref_log_probs = F.log_softmax(ref_logits, dim=-1)
                    ref_token_log_probs = ref_log_probs.gather(-1, generated_ids.unsqueeze(-1)).squeeze(-1)
                    ref_sequence_log_probs = ref_token_log_probs.sum(dim=1)
                
                kl_penalty = 0.01 * (log_probs - ref_sequence_log_probs).pow(2).mean()
                
                total_loss = policy_loss + kl_penalty
                
                # Optimization step
                self.optimizer.zero_grad()
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
            
            # Update progress
            avg_reward = np.mean(group_rewards)
            pbar.set_postfix({
                'avg_reward': f"{avg_reward:.3f}",
                'loss': f"{total_loss.item():.4f}"
            })
            
            # Save checkpoints
            if episode % 1000 == 0 and episode > 0:
                checkpoint_path = Path(self.config.checkpoint_dir) / f"grpo_episode_{episode}.pt"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({
                    'episode': episode,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'avg_reward': avg_reward,
                }, checkpoint_path)


def main():
    """Main training pipeline"""
    # Setup
    config = TrainingConfig()
    device = torch.device("cuda" if torch.cuda.is_available() else 
                          "mps" if torch.backends.mps.is_available() else "cpu")
    
    logger.info(f"Using device: {device}")
    
    # Initialize tokenizer
    from transformers import GPT2Tokenizer, GPT2LMHeadModel, GPT2Config
    base_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    base_tokenizer.pad_token = base_tokenizer.eos_token
    base_tokenizer.padding_side = 'left'  # Set left padding for decoder-only models
    tokenizer = MathTokenizer(base_tokenizer)
    
    # Update config with actual vocab size after adding math tokens
    config.vocab_size = len(tokenizer.base_tokenizer)
    
    # Initialize model with optimized architecture
    model_config = GPT2Config(
        vocab_size=config.vocab_size,
        n_positions=config.n_positions,
        n_embd=config.n_embd,
        n_layer=config.n_layer,
        n_head=config.n_head,
        resid_pdrop=0.1,
        embd_pdrop=0.1,
        attn_pdrop=0.1,
    )
    
    model = GPT2LMHeadModel(model_config)
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Create reference model (frozen copy for GRPO)
    reference_model = GPT2LMHeadModel(model_config)
    reference_model.load_state_dict(model.state_dict())
    for param in reference_model.parameters():
        param.requires_grad = False
    
    # Move to device
    model.to(device)
    reference_model.to(device)
    
    # Phase 1: Pre-training
    logger.info("="*50)
    logger.info("PHASE 1: PRE-TRAINING")
    logger.info("="*50)
    
    pretrainer = PreTrainer(model, tokenizer, config)
    pretrainer.train(device)
    
    logger.info("Pre-training completed!")
    
    # Phase 2: GRPO Fine-tuning
    logger.info("="*50)
    logger.info("PHASE 2: GRPO FINE-TUNING")
    logger.info("="*50)
    
    # Update reference model with pre-trained weights
    reference_model.load_state_dict(model.state_dict())
    
    grpo_trainer = GRPOTrainer(model, reference_model, tokenizer, config)
    grpo_trainer.train(device)
    
    logger.info("GRPO training completed!")
    
    # Save final model
    final_path = Path(config.checkpoint_dir) / "final_model.pt"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'tokenizer_state': tokenizer.base_tokenizer.get_vocab(),
        'config': config,
    }, final_path)
    
    logger.info(f"Final model saved to: {final_path}")
    
    # Test the model
    test_model(model, tokenizer, device)


def test_model(model: nn.Module, tokenizer: MathTokenizer, device: torch.device):
    """Test the trained model on sample problems"""
    logger.info("="*50)
    logger.info("TESTING TRAINED MODEL")
    logger.info("="*50)
    
    model.eval()
    
    test_cases = [
        "Factor: x**2 - 5*x + 6 =",
        "Factor: x**2 - 1 =", 
        "Factor: x**2 + 2*x + 1 =",
        "Factor: x**3 - 8 =",
        "Factor: 2*x**2 - 8*x + 8 ="
    ]
    
    with torch.no_grad():
        for test_case in test_cases:
            # Encode input
            encoded = tokenizer.encode(
                test_case,
                return_tensors='pt',
                max_length=64,
                truncation=True,
                padding=True
            )
            
            input_ids = encoded['input_ids'].to(device)
            attention_mask = encoded['attention_mask'].to(device)
            
            # Generate response
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=32,
                min_new_tokens=5,
                do_sample=True,
                temperature=0.3,  # Lower temperature for more deterministic output
                top_p=0.8,
                pad_token_id=tokenizer.base_tokenizer.pad_token_id,
                use_cache=True
            )
            
            # Decode response
            generated_ids = outputs[0, input_ids.shape[1]:]
            response = tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            logger.info(f"Input: {test_case}")
            logger.info(f"Output: {response}")
            logger.info("-" * 30)


class ModelEvaluator:
    """Comprehensive evaluation of the trained model"""
    
    def __init__(self, model: nn.Module, tokenizer: MathTokenizer, device: torch.device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.reward_calculator = AdvancedRewardCalculator()
        
    def evaluate_on_test_set(self, test_size: int = 100) -> Dict[str, float]:
        """Evaluate model on a held-out test set"""
        logger.info("Running comprehensive evaluation...")
        
        # Generate test problems
        generator = PolynomialDataGenerator(TrainingConfig())
        
        results = {'easy': [], 'medium': [], 'hard': []}
        
        # Easy problems (degree 2, integer roots)
        easy_problems = generator.generate_polynomial_problems(test_size // 3, 2, True)
        for prob in tqdm(easy_problems, desc="Evaluating easy problems"):
            prompt = f"Factor: {prob['expanded']} ="
            response = self._generate_response(prompt)
            score = self.reward_calculator.evaluate_factorization(response, prob['roots'])
            results['easy'].append(score)
        
        # Medium problems (degree 3, integer roots)  
        medium_problems = generator.generate_polynomial_problems(test_size // 3, 3, True)
        for prob in tqdm(medium_problems, desc="Evaluating medium problems"):
            prompt = f"Factor: {prob['expanded']} ="
            response = self._generate_response(prompt)
            score = self.reward_calculator.evaluate_factorization(response, prob['roots'])
            results['medium'].append(score)
            
        # Hard problems (degree 2, rational roots)
        hard_problems = generator.generate_polynomial_problems(test_size // 3, 2, False)
        for prob in tqdm(hard_problems, desc="Evaluating hard problems"):
            prompt = f"Factor: {prob['expanded']} ="
            response = self._generate_response(prompt)
            score = self.reward_calculator.evaluate_factorization(response, prob['roots'])
            results['hard'].append(score)
        
        # Calculate statistics
        stats = {}
        for difficulty, scores in results.items():
            stats[f'{difficulty}_mean'] = np.mean(scores)
            stats[f'{difficulty}_std'] = np.std(scores)
            stats[f'{difficulty}_accuracy'] = np.mean([s >= 0.8 for s in scores])  # 80% threshold
        
        # Overall statistics
        all_scores = results['easy'] + results['medium'] + results['hard']
        stats['overall_mean'] = np.mean(all_scores)
        stats['overall_std'] = np.std(all_scores)
        stats['overall_accuracy'] = np.mean([s >= 0.8 for s in all_scores])
        
        # Log results
        logger.info("="*50)
        logger.info("EVALUATION RESULTS")
        logger.info("="*50)
        for key, value in stats.items():
            logger.info(f"{key}: {value:.4f}")
        
        return stats
    
    def _generate_response(self, prompt: str) -> str:
        """Generate a single response for evaluation"""
        self.model.eval()
        
        with torch.no_grad():
            encoded = self.tokenizer.encode(
                prompt,
                return_tensors='pt',
                max_length=64,
                truncation=True
            )
            
            input_ids = encoded['input_ids'].to(self.device)
            attention_mask = encoded['attention_mask'].to(self.device)
            
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=32,
                min_new_tokens=5,
                do_sample=False,  # Deterministic for evaluation
                temperature=1.0,
                pad_token_id=self.tokenizer.base_tokenizer.pad_token_id,
                use_cache=True
            )
            
            generated_ids = outputs[0, input_ids.shape[1]:]
            response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
        return response


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train polynomial factorization model with GRPO")
    parser.add_argument("--skip-pretrain", action="store_true", 
                       help="Skip pre-training phase")
    parser.add_argument("--skip-grpo", action="store_true",
                       help="Skip GRPO phase") 
    parser.add_argument("--eval-only", action="store_true",
                       help="Only run evaluation")
    parser.add_argument("--model-path", type=str, default=None,
                       help="Path to pre-trained model")
    parser.add_argument("--config-path", type=str, default=None,
                       help="Path to config file")
    
    args = parser.parse_args()
    
    if args.eval_only:
        if not args.model_path:
            logger.error("--model-path required for evaluation")
            exit(1)
            
        # Load model and evaluate
        checkpoint = torch.load(args.model_path)
        
        # Initialize components
        device = torch.device("cuda" if torch.cuda.is_available() else 
                             "mps" if torch.backends.mps.is_available() else "cpu")
        
        from transformers import GPT2Tokenizer, GPT2LMHeadModel
        base_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        tokenizer = MathTokenizer(base_tokenizer)
        
        config = checkpoint.get('config', TrainingConfig())
        model_config = GPT2Config(
            vocab_size=len(tokenizer.base_tokenizer),
            n_positions=config.n_positions,
            n_embd=config.n_embd,
            n_layer=config.n_layer,
            n_head=config.n_head,
        )
        
        model = GPT2LMHeadModel(model_config)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        
        # Run evaluation
        evaluator = ModelEvaluator(model, tokenizer, device)
        stats = evaluator.evaluate_on_test_set()
        
        # Save evaluation results
        eval_results_path = Path("evaluation_results.json")
        with open(eval_results_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Evaluation results saved to: {eval_results_path}")
        
    else:
        # Run full training pipeline
        main()