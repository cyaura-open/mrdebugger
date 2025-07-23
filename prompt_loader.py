import os
from typing import Dict, Any


class PromptLoader:
    """Handles loading and formatting of prompt templates"""
    
    def __init__(self, prompts_folder: str = 'prompts', prompt_files: Dict[str, str] | None = None):
        """
        prompts_folder: path to folder containing prompt text files
        prompt_files: mapping of logical prompt names to filenames (usually injected from config)
        """
        self.prompts_folder = prompts_folder
        # Use supplied mapping or fallback to legacy defaults for backward-compatibility
        self.prompt_files = prompt_files or {
            'bug_slayer': 'bug_slayer_prompt.txt',
            'audit_consolidator': 'audit_consolidator_prompt.txt',
            'final_consolidator': 'final_consolidator_prompt.txt'
        }
        self.prompts: Dict[str, str] = {}
        self._load_prompts()
    
    def get_prompt(self, prompt_type: str) -> str:
        """Get a prompt by type"""
        if prompt_type not in self.prompts:
            raise KeyError(f"Prompt type '{prompt_type}' not found. Available: {list(self.prompts.keys())}")
        return self.prompts[prompt_type]
    
    def _load_prompts(self):
        """Load all prompt files specified in self.prompt_files"""
        # Check prompts folder exists
        if not os.path.exists(self.prompts_folder):
            raise FileNotFoundError(f"Prompts folder not found: {self.prompts_folder}")

        # Load each required prompt file
        for name, filename in self.prompt_files.items():
            filepath = os.path.join(self.prompts_folder, filename)
            
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Required prompt file not found: {filepath}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError(f"Prompt file is empty: {filepath}")
                    self.prompts[name] = content
                    print(f"✓ Loaded prompt: {filepath}")
            except Exception as e:
                raise Exception(f"Error loading prompt file {filepath}: {e}")
        
        print(f"✓ Successfully loaded {len(self.prompts)} prompt files")