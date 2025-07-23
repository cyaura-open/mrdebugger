import yaml
import pathlib
import os
import re
import shutil
from typing import Dict, Any, List
from ai_client import AIClientFactory
from prompt_loader import PromptLoader
from file_manager import FileManager
from token_manager import TokenManager
from dotenv import load_dotenv

load_dotenv()

class WorkflowOrchestrator:
    """Orchestrates the complete multi-AI bug investigation workflow"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config = self._load_config(config_file)
        self.prompt_loader = PromptLoader(
            self.config['paths']['prompts_folder'],
            self.config.get('prompts')
        )
        self.file_manager = FileManager()
        self.token_manager = TokenManager(self.config)
        
        # Initialize AI clients
        apis_config = self.config['apis']
        workflow_config = self.config['workflow']
        
        self.ai_a = AIClientFactory.create_client(
            workflow_config['ai_a'], 
            apis_config[workflow_config['ai_a']]
        )
        self.ai_b = AIClientFactory.create_client(
            workflow_config['ai_b'], 
            apis_config[workflow_config['ai_b']]
        )
        self.final_ai = AIClientFactory.create_client(
            workflow_config['final_arbitrator'], 
            apis_config[workflow_config['final_arbitrator']]
        )
    
    def _create_versioned_results_folder(self, bug_file: str) -> str:
        """Create a new versioned results folder and return its name"""
        # Find existing bug folders
        existing_folders = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and re.match(r'^bug\d{4}_results$', item):
                existing_folders.append(item)
        
        # Extract numbers and find the highest
        if existing_folders:
            numbers = []
            for folder in existing_folders:
                match = re.match(r'^bug(\d{4})_results$', folder)
                if match:
                    numbers.append(int(match.group(1)))
            next_number = max(numbers) + 1
        else:
            next_number = 1
        
        # Create new folder name with 4-digit padding
        folder_name = f"bug{next_number:04d}_results"
        os.makedirs(folder_name)
        print(f"✓ Created results folder: {folder_name}")
        
        # Copy the bug file into the results folder
        bug_dest = os.path.join(folder_name, "bug.txt")
        shutil.copy2(bug_file, bug_dest)
        print(f"✓ Copied {bug_file} to {bug_dest}")
        
        return folder_name
    
    def _update_output_paths(self, results_folder: str):
        """Update all output paths to use the versioned results folder"""
        for key in self.config['output']:
            original_path = self.config['output'][key]
            # Extract just the filename from the original path
            filename = os.path.basename(original_path)
            # Update to use the new results folder
            self.config['output'][key] = os.path.join(results_folder, filename)
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load *.json or *.yml/.yaml transparently."""
        path = pathlib.Path(config_file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in {'.yml', '.yaml'}:
                    config = yaml.safe_load(f)
                    print(f"Loaded YAML config: {config_file}")
                else:
                    config = json.load(f)
                    print(f"Loaded JSON config: {config_file}")
                
                # Handle environment variable substitution if needed
                config = self._process_env_vars(config)
                return config
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file {config_file} not found")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise Exception(f"Invalid config syntax in {config_file}: {e}")
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process environment variable placeholders in config"""
        
        # Only process APIs section for now
        if 'apis' in config:
            for provider, api_config in config['apis'].items():
                api_key = api_config.get('api_key', '')
                if isinstance(api_key, str) and api_key.startswith('${') and api_key.endswith('}'):
                    env_var = api_key[2:-1]  # Remove ${ and }
                    actual_key = os.getenv(env_var, '')
                    if actual_key:
                        api_config['api_key'] = actual_key
                        print(f"Loaded {provider} API key from environment variable {env_var}")
                    else:
                        print(f"Warning: Environment variable {env_var} not set for {provider}")
        
        return config
    
    def run_investigation(self, bug_file: str = None, codebase_folder: str = None, 
                         codebase_files: List[str] = None) -> str:
        """Run the complete 3-phase investigation workflow"""
        print("Starting Multi-AI Bug Investigation...")
        
        # Determine input method
        if bug_file is None:
            bug_file = self.config['paths']['bug_file']
        
        # Create versioned results folder and update output paths
        results_folder = self._create_versioned_results_folder(bug_file)
        self._update_output_paths(results_folder)
        
        if codebase_folder:
            # Use folder-based approach
            print(f"Reading codebase from folder: {codebase_folder}")
            supported_extensions = self.config['paths']['supported_extensions']
            codebase_content = self.file_manager.read_codebase_folder(codebase_folder, supported_extensions)
        elif codebase_files:
            # Use specific files approach (legacy)
            print(f"Reading {len(codebase_files)} specific files")
            codebase_content = self.file_manager.read_codebase_files(codebase_files)
        else:
            # Default: try to read from configured codebase folder
            codebase_folder = self.config['paths']['codebase_folder']
            if self.file_manager.folder_exists(codebase_folder):
                print(f"Using default codebase folder: {codebase_folder}")
                supported_extensions = self.config['paths']['supported_extensions']
                codebase_content = self.file_manager.read_codebase_folder(codebase_folder, supported_extensions)
            else:
                raise Exception(f"No codebase specified and default folder '{codebase_folder}' not found")
        
        # Read bug description
        bug_description = self.file_manager.read_file(bug_file)
        print(f"Bug description loaded from: {bug_file}")
        
        # Show content stats
        self._show_content_stats(bug_description, codebase_content)
        
        # Phase 1: Initial Investigation
        print("\nPHASE 1: Initial Investigation")
        phase1_results = self._phase1_initial_investigation(bug_description, codebase_content)
        
        # Phase 2: Cross-Critique
        print("\nPHASE 2: Cross-Critique")
        phase2_results = self._phase2_cross_critique(
            bug_description, codebase_content, phase1_results
        )
        
        # Phase 3: Final Arbitration
        print("\nPHASE 3: Final Arbitration")
        final_result = self._phase3_final_arbitration(
            bug_description, codebase_content, phase1_results, phase2_results
        )
        
        print(f"\nInvestigation complete! Results saved to: {results_folder}")
        return final_result
    
    def _show_content_stats(self, bug_description: str, codebase_content: str):
        """Display content statistics"""
        bug_chars = len(bug_description)
        codebase_chars = len(codebase_content)
        total_chars = bug_chars + codebase_chars
        
        print(f"Content Statistics:")
        print(f"   - Bug description: {bug_chars:,} characters")
        print(f"   - Codebase content: {codebase_chars:,} characters")
        print(f"   - Total content: {total_chars:,} characters")
        
        # Estimate tokens for each AI
        workflow_config = self.config['workflow']
        for role, provider in [('AI_A', workflow_config['ai_a']), 
                              ('AI_B', workflow_config['ai_b']),
                              ('Final', workflow_config['final_arbitrator'])]:
            estimated_tokens = self.token_manager.estimate_tokens(
                bug_description + codebase_content, provider
            )
            print(f"   - {role} ({provider}): ~{estimated_tokens:,} tokens")
    
    def _phase1_initial_investigation(self, bug_description: str, codebase_content: str) -> Dict[str, str]:
        """Phase 1: Both AIs analyze the bug independently"""
        workflow_config = self.config['workflow']
        apis_config = self.config['apis']
        
        # Handle chunking for AI_A
        ai_a_provider = workflow_config['ai_a']
        ai_a_model = apis_config[ai_a_provider]['model']
        ai_a_chunks = self.token_manager.chunk_codebase_if_needed(
            bug_description, codebase_content, ai_a_provider, ai_a_model
        )
        
        # Handle chunking for AI_B  
        ai_b_provider = workflow_config['ai_b']
        ai_b_model = apis_config[ai_b_provider]['model']
        ai_b_chunks = self.token_manager.chunk_codebase_if_needed(
            bug_description, codebase_content, ai_b_provider, ai_b_model
        )
        
        print(f"  AI_A analyzing bug ({len(ai_a_chunks)} chunk(s))...")
        audit_report_a = self._analyze_with_chunks(self.ai_a, bug_description, ai_a_chunks)
        
        print(f"  AI_B analyzing bug ({len(ai_b_chunks)} chunk(s))...")
        audit_report_b = self._analyze_with_chunks(self.ai_b, bug_description, ai_b_chunks)
        
        # Save reports
        output_config = self.config['output']
        self.file_manager.write_file(output_config['audit_report_a'], audit_report_a)
        self.file_manager.write_file(output_config['audit_report_b'], audit_report_b)
        
        return {
            'audit_report_a': audit_report_a,
            'audit_report_b': audit_report_b
        }
    
    def _analyze_with_chunks(self, ai_client, bug_description: str, codebase_chunks: List[str]) -> str:
        """Analyze bug with potentially multiple codebase chunks"""
        if len(codebase_chunks) == 1:
            # Single chunk - normal analysis
            prompt = self._build_initial_prompt(bug_description, codebase_chunks[0])
            return ai_client.send_message(prompt, self.config['workflow']['retry_attempts'])
        
        # Multiple chunks - analyze each and consolidate
        chunk_analyses = []
        for i, chunk in enumerate(codebase_chunks):
            print(f"    Analyzing chunk {i+1}/{len(codebase_chunks)}...")
            prompt = self._build_initial_prompt(bug_description, chunk)
            chunk_analysis = ai_client.send_message(prompt, self.config['workflow']['retry_attempts'])
            chunk_analyses.append(f"## Analysis of Chunk {i+1}\n{chunk_analysis}")
        
        # Consolidate chunk analyses
        consolidation_prompt = self._build_chunk_consolidation_prompt(bug_description, chunk_analyses)
        return ai_client.send_message(consolidation_prompt, self.config['workflow']['retry_attempts'])
    
    def _build_chunk_consolidation_prompt(self, bug_description: str, chunk_analyses: List[str]) -> str:
        """Build prompt to consolidate multiple chunk analyses"""
        analyses_text = "\n\n".join(chunk_analyses)
        
        return f"""You have analyzed a bug across multiple code chunks. Now consolidate your findings into a single comprehensive analysis.

ORIGINAL BUG:
{bug_description}

YOUR CHUNK-BY-CHUNK ANALYSES:
{analyses_text}

TASK: Create a single, consolidated bug analysis report that:
1. Combines insights from all chunks
2. Identifies the primary root cause
3. Provides definitive fix recommendations
4. Eliminates redundancy between chunk analyses

Use the same format as a standard bug analysis report."""
    
    def _phase2_cross_critique(self, bug_description: str, codebase_content: str, 
                              phase1_results: Dict[str, str]) -> Dict[str, str]:
        """Phase 2: AIs cross-critique each other's work"""
        
        # AI_A critiques AI_B's work and consolidates
        print("  AI_A reviewing AI_B's analysis...")
        consolidation_prompt_a = self._build_consolidation_prompt(
            bug_description, codebase_content,
            phase1_results['audit_report_a'],  # Own report
            phase1_results['audit_report_b']   # Other's report
        )
        consolidation_a = self.ai_a.send_message(
            consolidation_prompt_a, 
            self.config['workflow']['retry_attempts']
        )
        
        # AI_B critiques AI_A's work and consolidates  
        print("  AI_B reviewing AI_A's analysis...")
        consolidation_prompt_b = self._build_consolidation_prompt(
            bug_description, codebase_content,
            phase1_results['audit_report_b'],  # Own report
            phase1_results['audit_report_a']   # Other's report
        )
        consolidation_b = self.ai_b.send_message(
            consolidation_prompt_b, 
            self.config['workflow']['retry_attempts']
        )
        
        # Save consolidations
        output_config = self.config['output']
        self.file_manager.write_file(output_config['consolidation_a'], consolidation_a)
        self.file_manager.write_file(output_config['consolidation_b'], consolidation_b)
        
        return {
            'consolidation_a': consolidation_a,
            'consolidation_b': consolidation_b
        }
    
    def _phase3_final_arbitration(self, bug_description: str, codebase_content: str,
                                 phase1_results: Dict[str, str], 
                                 phase2_results: Dict[str, str]) -> str:
        """Phase 3: Final AI creates definitive fix list"""
        
        print("  Final arbitrator creating definitive fixes...")
        
        final_prompt = self._build_final_prompt(
            bug_description, codebase_content,
            phase1_results, phase2_results
        )
        
        definitive_fixes = self.final_ai.send_message(
            final_prompt, 
            self.config['workflow']['retry_attempts']
        )
        
        # Save final result
        output_filename = self.config['output']['definitive_fixes']
        self.file_manager.write_file(output_filename, definitive_fixes)
        
        return definitive_fixes
    
    def _build_initial_prompt(self, bug_description: str, codebase_content: str) -> str:
        """Build the initial investigation prompt"""
        base_prompt = self.prompt_loader.get_prompt('bug_slayer')
        
        return f"""{base_prompt}

# BUG DESCRIPTION AND STACK TRACE:
{bug_description}

# CODEBASE FILES:
{codebase_content}

Please analyze this bug thoroughly and provide your detailed analysis report."""
    
    def _build_consolidation_prompt(self, bug_description: str, codebase_content: str,
                                   own_report: str, other_report: str) -> str:
        """Build the consolidation/cross-critique prompt"""
        base_prompt = self.prompt_loader.get_prompt('audit_consolidator')
        
        return f"""{base_prompt}

# ORIGINAL BUG DESCRIPTION:
{bug_description}

# ORIGINAL CODEBASE:
{codebase_content}

# YOUR PREVIOUS ANALYSIS:
{own_report}

# OTHER AI'S ANALYSIS:
{other_report}

Please provide your consolidated analysis after reviewing both reports."""
    
    def _build_final_prompt(self, bug_description: str, codebase_content: str,
                           phase1_results: Dict[str, str], 
                           phase2_results: Dict[str, str]) -> str:
        """Build the final arbitration prompt"""
        base_prompt = self.prompt_loader.get_prompt('final_consolidator')
        
        return f"""{base_prompt}

# ORIGINAL BUG DESCRIPTION:
{bug_description}

# ORIGINAL CODEBASE:
{codebase_content}

# CONSOLIDATION FROM AI_A:
{phase2_results['consolidation_a']}

# CONSOLIDATION FROM AI_B:
{phase2_results['consolidation_b']}

# INITIAL AUDIT REPORT A:
{phase1_results['audit_report_a']}

# INITIAL AUDIT REPORT B:
{phase1_results['audit_report_b']}

Please create the final, definitive list of validated bug fixes."""