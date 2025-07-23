import re
from typing import Dict, List, Tuple
from file_manager import FileManager


class TokenManager:
    """Handles token counting and content size management for API calls"""
    
    # Approximate tokens per character for different models
    TOKEN_RATIOS = {
        'openai': 0.25,  # ~4 chars per token for GPT models
        'anthropic': 0.25,  # Similar ratio for Claude
        'default': 0.25
    }
    
    # Conservative API limits (leaving room for response)
    API_LIMITS = {
        'openai': {
            'o3': 200000,  # O3 context limit
            'default': 100000
        },
        'anthropic': {
            'claude-4-sonnet-20240620': 200000,  # Claude 4 Sonnet limit
            'default': 100000  
        }
    }
    
    def __init__(self, config: Dict):
        self.config = config
    
    def estimate_tokens(self, text: str, provider: str = 'default') -> int:
        """Estimate token count for given text"""
        ratio = self.TOKEN_RATIOS.get(provider, self.TOKEN_RATIOS['default'])
        return int(len(text) * ratio)
    
    def get_max_tokens_for_provider(self, provider: str, model: str) -> int:
        """Get maximum token limit for a provider/model"""
        provider_limits = self.API_LIMITS.get(provider, {'default': 100000})
        return provider_limits.get(model, provider_limits.get('default', 100000))
    
    def validate_content_size(self, content: str, provider: str, model: str) -> Tuple[bool, int, int]:
        """
        Validate if content fits within API limits
        Returns: (fits, estimated_tokens, max_allowed)
        """
        estimated_tokens = self.estimate_tokens(content, provider)
        max_tokens = self.get_max_tokens_for_provider(provider, model)
        
        # Reserve 25% for prompt formatting and response
        safe_limit = int(max_tokens * 0.75)
        
        return estimated_tokens <= safe_limit, estimated_tokens, safe_limit
    
    def chunk_codebase_if_needed(self, bug_description: str, codebase_content: str, 
                                provider: str, model: str) -> List[str]:
        """
        Split codebase into chunks if too large for API
        Returns list of content chunks that each fit within limits
        """
        base_prompt_size = len(bug_description) + 1000  # Extra for prompt formatting
        base_tokens = self.estimate_tokens(bug_description, provider) + 400  # Prompt overhead
        
        max_tokens = self.get_max_tokens_for_provider(provider, model)
        safe_limit = int(max_tokens * 0.75)
        available_tokens = safe_limit - base_tokens
        
        if available_tokens <= 0:
            raise Exception(f"Bug description too large for {provider} {model}")
        
        # Check if codebase fits
        codebase_tokens = self.estimate_tokens(codebase_content, provider)
        
        if codebase_tokens <= available_tokens:
            return [codebase_content]  # Fits in one chunk
        
        # Need to split codebase
        print(f"Warning: Codebase too large ({codebase_tokens} tokens), splitting into chunks...")
        
        # Split by files first
        file_sections = self._split_by_files(codebase_content)
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for section in file_sections:
            section_tokens = self.estimate_tokens(section, provider)
            
            # If single file is too large, we have a problem
            if section_tokens > available_tokens:
                print(f"Warning: Single file section exceeds token limit, truncating...")
                section = self._truncate_section(section, available_tokens, provider)
                section_tokens = self.estimate_tokens(section, provider)
            
            # Check if we can add this section to current chunk
            if current_tokens + section_tokens <= available_tokens:
                current_chunk += section
                current_tokens += section_tokens
            else:
                # Start new chunk
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
                current_tokens = section_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"Split codebase into {len(chunks)} chunks")
        return chunks
    
    def _split_by_files(self, codebase_content: str) -> List[str]:
        """Split combined codebase content back into individual file sections"""
        # Look for file separators like "# ===== filename.py ====="
        pattern = r'\n# ===== .+ =====\n'
        sections = re.split(pattern, codebase_content)
        
        # Re-add headers to sections (except first)
        headers = re.findall(pattern, codebase_content)
        
        result = []
        if sections[0].strip():  # First section (before any header)
            result.append(sections[0])
        
        for i, header in enumerate(headers):
            if i + 1 < len(sections) and sections[i + 1].strip():
                result.append(header + sections[i + 1])
        
        return result if result else [codebase_content]
    
    def _truncate_section(self, section: str, max_tokens: int, provider: str) -> str:
        """Truncate a section to fit within token limits"""
        target_chars = int(max_tokens / self.TOKEN_RATIOS.get(provider, 0.25))
        
        if len(section) <= target_chars:
            return section
        
        # Try to truncate at natural boundaries
        truncated = section[:target_chars]
        
        # Find last complete line
        last_newline = truncated.rfind('\n')
        if last_newline > target_chars * 0.8:  # If we're not losing too much
            truncated = truncated[:last_newline]
        
        return truncated + "\n\n[... TRUNCATED FOR API LIMITS ...]"
    
    def validate_workflow_content(self, bug_description: str, codebase_content: str = None, 
                                 codebase_folder: str = None, codebase_files: List[str] = None) -> Dict:
        """
        Validate content sizes for all workflow steps
        Returns validation report
        """
        # Get codebase content if not provided
        if codebase_content is None:
            if codebase_folder:
                supported_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', 
                                      '.php', '.rb', '.go', '.rs', '.ts', '.jsx', '.tsx']
                codebase_content = FileManager.read_codebase_folder(codebase_folder, supported_extensions)
            elif codebase_files:
                codebase_content = FileManager.read_codebase_files(codebase_files)
            else:
                codebase_content = ""
        
        workflow_config = self.config['workflow']
        apis_config = self.config['apis']
        
        validation_report = {
            'total_codebase_size': len(codebase_content),
            'bug_description_size': len(bug_description),
            'provider_validations': {}
        }
        
        # Check each provider in the workflow
        providers_to_check = [
            ('ai_a', workflow_config['ai_a']),
            ('ai_b', workflow_config['ai_b']),
            ('final_arbitrator', workflow_config['final_arbitrator'])
        ]
        
        for role, provider_name in providers_to_check:
            provider_config = apis_config[provider_name]
            model = provider_config['model']
            
            fits, estimated_tokens, safe_limit = self.validate_content_size(
                bug_description + codebase_content, provider_name, model
            )
            
            validation_report['provider_validations'][f"{role}_{provider_name}"] = {
                'fits': fits,
                'estimated_tokens': estimated_tokens,
                'safe_limit': safe_limit,
                'model': model
            }
        
        return validation_report