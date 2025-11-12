import torch
import torch.nn as nn
from torch.distributions import Categorical
from transformers import GPT2LMHeadModel, GPT2Config, AutoTokenizer
import numpy as np
from sympy import *
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from tqdm import tqdm
import os

class PolynomialGenerator:
    """
    Generator for procedural mathematical equations with controlled complexity
    and specified target solutions.
    """
    
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_batch(
        self, batch_size: int, symbol: Symbol, degree: int = 2, 
        min_coefficient: int = -100, max_coefficient: int = 100
    ) -> List[Dict[str, Any]]:
        """Generate a batch of polynomial equations with solution targets."""
        batch = []
        for _ in range(batch_size):
            roots = []
            for _ in range(degree):
                root = random.randint(min_coefficient, max_coefficient)
                if roots.count(root) == 0: 
                    roots.append(root)
            
            factors = [symbol - root for root in roots]
            poly = expand(prod(factors))
            all_solutions = solve(Eq(poly, 0), symbol)
            
            batch.append({
                'poly': poly,
                'factors': factors,
                'solution': all_solutions,
                'complexity': degree
            })
        return batch

class PolynomialFactoringEnv:
    """
    A conceptual environment for polynomial factoring using RL.
    """
    def __init__(self, tokenizer, max_length=128):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.generator = PolynomialGenerator(seed=42)
        
    def reset_batch(self, batch_size):
        """Generate a batch of polynomial equations."""
        polynomials = self.generator.generate_batch(
            batch_size, symbols("x"), 2
        )
        self.current_polynomials = polynomials
        
        # Create prompts for factoring
        poly_strings = [f"Factor: {str(p['poly'])} = " for p in polynomials]
        batch_encoding = self.tokenizer(
            poly_strings,
            return_tensors='pt',
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_attention_mask=True
        )
        
        attention_masks = batch_encoding['attention_mask']
        states = batch_encoding['input_ids']
        
        return states, attention_masks

    def step_batch(self, action_ids_batch):
        """Process a batch of actions."""
        factored_forms = []
        rewards = []
        dones = []
        
        for i, action_ids in enumerate(action_ids_batch):
            # Decode the model's output (factored form)
            factored_form = self.tokenizer.decode(action_ids, skip_special_tokens=True)
            factored_forms.append(factored_form)
            
            reward = self._calculate_reward(factored_form, i)
            rewards.append(reward)
            
            # For simplicity, we'll consider each interaction a terminal state
            dones.append(True)
            
        return factored_forms, rewards, dones

    def _calculate_reward(self, factored_form, poly_idx):
        """
        Calculates reward based on correctness of factors.
        """
        correct_factors = [f"({str(f)})" for f in self.current_polynomials[poly_idx]['factors']]
        parsed_factors = self._parse_factors(factored_form)
        
        if not parsed_factors:
            return -1.0  # Nothing correct

        print(correct_factors)
        print(parsed_factors)
        print()

        if len(parsed_factors) != len(correct_factors):
            return -0.5  # Correct format but wrong number of factors
            
        # Count correct factors
        correct_count = sum(1 for f in parsed_factors if f in correct_factors)
        
        if correct_count == len(correct_factors):
            return 1.0  # Fully correct
        elif correct_count > 0:
            return 0.5  # Some factors correct
        else:
            return 0.0  # No factors correct but correct number
            
    def _parse_factors(self, factored_form):
        """
        Parses the factored string into a list of factors.
        """
        # This is a very basic and fragile parser
        try:
            factors = []
            last_idx = 0
            while last_idx != -1 and last_idx < len(factored_form):
                last_idx = lparen_idx = factored_form.index('(', last_idx)
                if last_idx == -1:
                    break
                last_idx = rparen_idx = factored_form.index(')', last_idx)
                if last_idx == -1:
                    break
                factors.append(factored_form[lparen_idx:rparen_idx + 1])
            return factors
        except:
            return []  # Return empty list if parsing fails


# Use GPT-2 tokenizer with proper padding configuration
tokenizer = AutoTokenizer.from_pretrained("gpt2")
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = 'left'  # Set left padding for decoder-only models

# --- Model Definition ---
# Define a small GPT-2 model configuration (<1M parameters)
config = GPT2Config(
    vocab_size=tokenizer.vocab_size,
    n_positions=256,
    n_embd=64,       # Reduced embedding size
    n_layer=8,       # Fewer layers
    n_head=8,        # Fewer attention heads
    resid_pdrop=0.1, # Small dropout for regularization
    embd_pdrop=0.1,
    attn_pdrop=0.1,
    # Remove the loss_type parameter as it's not recognized
)

# Initialize the policy model
policy_model = GPT2LMHeadModel(config)
print(f"Policy Model Parameters: {sum(p.numel() for p in policy_model.parameters())}")

# Initialize reference model (frozen copy of initial policy)
reference_model = GPT2LMHeadModel(config)
reference_model.load_state_dict(policy_model.state_dict())
for param in reference_model.parameters():
    param.requires_grad = False

# Move models to device with MPS optimizations
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
    # Enable MPS optimizations
    torch.mps.empty_cache()  # Clear MPS cache
    print("MPS device detected and cache cleared")
else:
    device = torch.device("cpu")

print(f"Using device: {device}")

# Move models to device and ensure they're in the right mode
policy_model.to(device)
reference_model.to(device)

# Ensure models are in training/eval mode appropriately
policy_model.train()
reference_model.eval()

# --- GRPO Training Setup ---
optimizer = torch.optim.AdamW(policy_model.parameters(), lr=5e-4, weight_decay=0.01)
env = PolynomialFactoringEnv(tokenizer)
num_episodes = 5000
gamma = 0.99
group_size = 1     # Increased for better MPS utilization
batch_size = 8     # Increased batch size for better GPU utilization

# Create checkpoint directory
os.makedirs("checkpoints", exist_ok=True)

def safe_generate(model, input_ids, attention_mask, **kwargs):
    """Safe generation with MPS optimizations."""
    try:
        # Clear MPS cache before generation for better utilization
        # if device.type == 'mps':
        #     torch.mps.empty_cache()
            
        # Ensure tensors are contiguous for better MPS performance
        input_ids = input_ids.contiguous()
        attention_mask = attention_mask.contiguous()
        
        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=13,
                min_new_tokens=5,
                num_return_sequences=1,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True,  # Enable KV cache for efficiency
                **kwargs
            )
            return outputs
    except RuntimeError as e:
        print(f"Generation failed: {e}")
        # Fallback: return input with a simple completion
        fallback_tokens = tokenizer("(x-1)(x+1)", return_tensors='pt')['input_ids'].to(device)
        fallback_output = torch.cat([input_ids, fallback_tokens.repeat(input_ids.shape[0], 1)], dim=1)
        return fallback_output

# --- GRPO Training Loop ---
progress_bar = tqdm(range(num_episodes), desc="Training Progress")

for episode in progress_bar:
    group_log_probs = []
    group_rewards = []
    group_states = []
    group_attention_masks = []
    
    # Collect a group of trajectories
    for group_step in range(group_size):
        try:
            # # Clear MPS cache periodically for better utilization
            # if device.type == 'mps' and group_step % 2 == 0:
            #     torch.mps.empty_cache()
                
            # Generate batch of states
            states, attention_masks = env.reset_batch(batch_size)
            states = states.to(device, non_blocking=True).contiguous()
            attention_masks = attention_masks.to(device, non_blocking=True).contiguous()
            
            group_states.append(states)
            group_attention_masks.append(attention_masks)
            
            # Generate actions (factoring) for the batch using safe generation
            outputs = safe_generate(
                policy_model,
                input_ids=states,
                attention_mask=attention_masks
            )
            
            # Extract only the new tokens (action) for each item in the batch
            action_ids_batch = outputs[:, states.shape[1]:]
            
            # Environment interaction for the batch
            factored_forms, rewards, dones = env.step_batch(action_ids_batch)
            group_rewards.extend(rewards)
            
            # Calculate log probabilities for the batch
            for i in range(batch_size):
                try:
                    state = states[i:i+1]
                    attention_mask = attention_masks[i:i+1]
                    action_ids = action_ids_batch[i]
                    
                    # Re-run the model to get logits for the full sequence
                    full_input_ids = torch.cat([state, action_ids.unsqueeze(0)], dim=1).contiguous()
                    
                    # Create proper attention mask for full sequence
                    state_attention = attention_mask
                    action_attention = torch.ones(1, action_ids.shape[0], device=device, dtype=attention_mask.dtype)
                    full_attention_mask = torch.cat([state_attention, action_attention], dim=1).contiguous()
                    
                    # Use forward pass instead of __call__ for better MPS performance
                    policy_model.train()  # Ensure training mode
                    outputs = policy_model.forward(
                        input_ids=full_input_ids,
                        attention_mask=full_attention_mask,
                        return_dict=True,
                        use_cache=False  # Disable cache during training for MPS stability
                    )
                    logits = outputs.logits
                    
                    # Calculate log probabilities for action tokens only
                    action_start_idx = state.shape[1]
                    action_logits = logits[0, action_start_idx-1:-1]  # Logits for predicting action tokens
                    action_tokens = action_ids
                    
                    # Apply softmax and get log probabilities
                    log_probs = torch.log_softmax(action_logits, dim=-1)
                    action_log_probs = log_probs[torch.arange(len(action_tokens)), action_tokens]
                    
                    # Sum log probabilities for the entire action
                    total_action_log_prob = torch.sum(action_log_probs)
                    group_log_probs.append(total_action_log_prob)
                    
                except Exception as e:
                    print(f"Error in log prob calculation: {e}")
                    # Add a dummy log prob to maintain batch consistency
                    group_log_probs.append(torch.tensor(-1.0, device=device))
            
        except Exception as e:
            print(f"Error in group step {group_step}: {e}")
            continue
    
    if not group_log_probs or not group_rewards:
        continue
        
    # --- GRPO Update ---
    try:
        rewards_tensor = torch.tensor(group_rewards, dtype=torch.float32, device=device)
        log_probs_tensor = torch.stack(group_log_probs)
        
        # Simple baseline (mean reward)
        baseline = torch.mean(rewards_tensor)
        advantages = rewards_tensor - baseline
        
        # Policy gradient loss (simplified GRPO)
        policy_loss = -torch.mean(advantages * log_probs_tensor)
        
        # Add small regularization term
        reg_loss = 0.01 * sum(p.pow(2.0).sum() for p in policy_model.parameters() if p.requires_grad)
        total_loss = policy_loss + reg_loss
        
        # Optimization step with gradient clipping
        optimizer.zero_grad()
        
        # Use retain_graph=False and clear cache for MPS
        total_loss.backward()
        
        # if device.type == 'mps':
        #     torch.mps.empty_cache()  # Clear cache after backward pass
            
        torch.nn.utils.clip_grad_norm_(policy_model.parameters(), max_norm=1.0)
        optimizer.step()
        
        # Clear cache after optimizer step for MPS
        # if device.type == 'mps':
        #     torch.mps.empty_cache()
        
        # Update progress bar
        progress_bar.set_postfix({
            "Avg Reward": f"{torch.mean(rewards_tensor).item():.4f}",
            "Loss": f"{total_loss.item():.4f}",
        })
        
    except Exception as e:
        print(f"Error in GRPO update: {e}")
        continue
    
    # Save checkpoint every 1000 episodes
    if episode % 1000 == 0 and episode > 0:
        try:
            checkpoint_path = f"checkpoints/grpo_checkpoint_{episode}.pt"
            torch.save({
                'episode': episode,
                'policy_model_state_dict': policy_model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': total_loss.item() if 'total_loss' in locals() else 0.0,
            }, checkpoint_path)
            print(f"\nCheckpoint saved at {checkpoint_path}")
        except Exception as e:
            print(f"Error saving checkpoint: {e}")

print("Training finished.")

# Save final model
try:
    final_checkpoint_path = "checkpoints/grpo_final_model.pt"
    torch.save({
        'policy_model_state_dict': policy_model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, final_checkpoint_path)
    print(f"Final model saved at {final_checkpoint_path}")
except Exception as e:
    print(f"Error saving final model: {e}")