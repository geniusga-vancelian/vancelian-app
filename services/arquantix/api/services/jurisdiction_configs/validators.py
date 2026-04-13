"""
Validation functions for jurisdiction configs
"""
from typing import Dict, Any, List, Tuple


def validate_kyc_config_structure(config_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate KYC config structure:
    - Steps must not have 'conditions' key
    - show_block/hide_block actions must reference blocks within the same step
    
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(config_json, dict):
        return False, ["config_json must be a dict"]
    
    steps = config_json.get("steps", [])
    if not isinstance(steps, list):
        return False, ["steps must be a list"]
    
    for step_idx, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"Step {step_idx} must be a dict")
            continue
        
        step_id = step.get("step_id", f"step_{step_idx}")
        
        # Check for step-level conditions (forbidden)
        if "conditions" in step:
            errors.append(f"Step '{step_id}' must not have 'conditions' key. Conditions must be on Block.conditions only.")
        
        # Get all block_ids in this step
        blocks = step.get("blocks", [])
        if not isinstance(blocks, list):
            errors.append(f"Step '{step_id}' blocks must be a list")
            continue
        
        step_block_ids = set()
        for block in blocks:
            if isinstance(block, dict):
                block_id = block.get("block_id")
                if block_id:
                    step_block_ids.add(block_id)
        
        # Validate conditions in each block
        for block_idx, block in enumerate(blocks):
            if not isinstance(block, dict):
                continue
            
            block_id = block.get("block_id", f"block_{block_idx}")
            conditions = block.get("conditions", [])
            
            if not isinstance(conditions, list):
                continue
            
            for cond_idx, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    continue
                
                then_actions = condition.get("then", [])
                if not isinstance(then_actions, list):
                    continue
                
                for action_idx, action in enumerate(then_actions):
                    if not isinstance(action, dict):
                        continue
                    
                    action_type = action.get("action")
                    target = action.get("block_id") or action.get("target")
                    
                    # Check show_block/hide_block references
                    if action_type in ["show_block", "hide_block"]:
                        if not target:
                            errors.append(
                                f"Step '{step_id}' block '{block_id}' condition {cond_idx} action {action_idx}: "
                                f"{action_type} must specify block_id"
                            )
                        elif target not in step_block_ids:
                            errors.append(
                                f"Step '{step_id}' block '{block_id}' condition {cond_idx} action {action_idx}: "
                                f"{action_type} references block_id '{target}' which is not in the same step. "
                                f"Available blocks in step: {sorted(step_block_ids)}"
                            )
    
    return len(errors) == 0, errors
