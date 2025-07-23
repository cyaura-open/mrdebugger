import sys
import argparse
import json
import os
from typing import List
from workflow_orchestrator import WorkflowOrchestrator
from token_manager import TokenManager
import yaml
import pathlib
from file_manager import FileManager
from test_connections import test_all_connections

def validate_content_sizes(config_file: str, bug_file: str = None, 
                          codebase_folder: str = None, codebase_files: List[str] = None):
    """Validate that content fits within API limits"""
    try:
        path = pathlib.Path(config_file)
        with open(path, 'r') as f:
            config = yaml.safe_load(f) if path.suffix.lower() in {'.yml', '.yaml'} else json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return False
    
    try:
        # Use default bug file if not specified
        if bug_file is None:
            bug_file = config['paths']['bug_file']
        
        bug_description = FileManager.read_file(bug_file)
        token_manager = TokenManager(config)
        
        print("Validating content sizes...")
        validation_report = token_manager.validate_workflow_content(
            bug_description, codebase_folder=codebase_folder, codebase_files=codebase_files
        )
        
        print(f"Content Analysis:")
        print(f"   - Bug description: {validation_report['bug_description_size']:,} chars")
        print(f"   - Codebase: {validation_report['total_codebase_size']:,} chars")
        
        all_valid = True
        for provider_key, validation in validation_report['provider_validations'].items():
            status = "FITS" if validation['fits'] else "TOO LARGE"
            print(f"   - {provider_key}: {validation['estimated_tokens']:,}/{validation['safe_limit']:,} tokens {status}")
            if not validation['fits']:
                all_valid = False
        
        if not all_valid:
            print("\nContent too large for some APIs. The workflow will automatically chunk content.")
        
        return True
        
    except Exception as e:
        print(f"Error validating content: {e}")
        return False


def setup_project_structure():
    """Create the expected project structure if it doesn't exist"""
    print("Setting up project structure...")
    
    # Create codebase folder
    if not FileManager.folder_exists('codebase'):
        os.makedirs('codebase')
        print("   - Created 'codebase/' folder")
    
    # Create prompts folder
    if not FileManager.folder_exists('prompts'):
        os.makedirs('prompts')
        print("   - Created 'prompts/' folder")
    
    # Create bug.txt if it doesn't exist
    if not FileManager.file_exists('bug.txt'):
        sample_bug = """PROBLEM: Describe your issue here

STACK TRACE:
Paste your error/stack trace here

DESCRIPTION:
Provide detailed description of:
- What you were trying to do
- What happened instead
- Steps to reproduce
- Expected behavior

ENVIRONMENT:
- Programming language and version
- Framework versions
- Operating system
- Other relevant details
"""
        FileManager.write_file('bug.txt', sample_bug)
        print("   - Created sample 'bug.txt' file")
    
    print("Project structure ready!")
    print("Next steps:")
    print("   1. Edit 'bug.txt' with your bug description")
    print("   2. Put your code files in the 'codebase/' folder")
    print("   3. Add your API keys to 'config.yaml'")
    print("   4. Run: python main.py")
    print("   5. Results will be saved in auto-generated 'bug####_results/' folders")


def main():
    """Main entry point for the Multi-AI Bug Investigation workflow"""
    
    parser = argparse.ArgumentParser(
        description='Multi-AI Bug Investigation Workflow',
        epilog='''Examples:
  # Setup project structure
  python main.py --setup
  
  # Test API connections
  python main.py --test-connections
  
  # Run with default structure (bug.txt + codebase/ folder)
  python main.py
  
  # Run with custom bug file and codebase folder
  python main.py --bug custom_bug.txt --codebase my_code/
  
  # Run with specific files (legacy mode)
  python main.py --bug bug.txt --files src/main.py src/utils.py
  
  # Validate content size only
  python main.py --validate-only
  
Note: Each run creates a new bug####_results/ folder with all outputs.''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input options
    parser.add_argument(
        '--bug', 
        help='Bug description file (default: bug.txt)'
    )
    
    parser.add_argument(
        '--codebase', 
        help='Codebase folder to analyze (default: codebase/)'
    )
    
    parser.add_argument(
        '--files', 
        nargs='*',
        help='Specific files to analyze (alternative to --codebase)'
    )
    
    # Configuration options
    parser.add_argument(
        '--config', 
        default='config.yaml',
        help='Configuration file (default: config.yaml)'
    )
    
    # Action options
    parser.add_argument(
        '--setup', 
        action='store_true',
        help='Setup project structure (create codebase/ folder and bug.txt)'
    )
    
    parser.add_argument(
        '--test-connections', 
        action='store_true',
        help='Test API connections and exit'
    )
    
    parser.add_argument(
        '--validate-only', 
        action='store_true',
        help='Only validate content sizes without running analysis'
    )
    
    parser.add_argument(
        '--output-only', 
        action='store_true',
        help='Only show the final output without progress messages'
    )
    
    args = parser.parse_args()
    
    # Setup mode
    if args.setup:
        setup_project_structure()
        sys.exit(0)
    
    # Test connections mode
    if args.test_connections:
        success = test_all_connections(args.config)
        sys.exit(0 if success else 1)
    
    try:
        # Load config to get defaults
        path = pathlib.Path(args.config)
        with open(path, 'r') as f:
            config = yaml.safe_load(f) if path.suffix.lower() in {'.yml', '.yaml'} else json.load(f)
        
        # Determine input sources
        bug_file = args.bug or config['paths']['bug_file']
        codebase_folder = args.codebase or config['paths']['codebase_folder']
        codebase_files = args.files
        
        # Validate inputs
        if not FileManager.file_exists(bug_file):
            print(f"Error: Bug file '{bug_file}' not found")
            print("Tip: Run 'python main.py --setup' to create project structure")
            sys.exit(1)
        
        # Check codebase input
        if codebase_files:
            # Specific files mode
            missing_files = [f for f in codebase_files if not FileManager.file_exists(f)]
            if missing_files:
                print(f"Error: Files not found: {', '.join(missing_files)}")
                sys.exit(1)
            print(f"Using specific files: {len(codebase_files)} files")
        else:
            # Folder mode
            if not FileManager.folder_exists(codebase_folder):
                print(f"Error: Codebase folder '{codebase_folder}' not found")
                print("Tip: Run 'python main.py --setup' to create project structure")
                sys.exit(1)
            
            # Check if folder has supported files
            supported_extensions = config['paths']['supported_extensions']
            found_files = FileManager.scan_codebase_folder(codebase_folder, supported_extensions)
            if not found_files:
                print(f"Error: No supported code files found in '{codebase_folder}'")
                print(f"Tip: Supported extensions: {', '.join(supported_extensions)}")
                sys.exit(1)
            print(f"Using codebase folder: {codebase_folder} ({len(found_files)} files)")
        
        # Validate content sizes
        if not validate_content_sizes(args.config, bug_file, codebase_folder, codebase_files):
            sys.exit(1)
        
        # If only validating, exit here
        if args.validate_only:
            print("\nValidation complete. Content is ready for analysis.")
            sys.exit(0)
        
        # Initialize and run workflow
        print("\nStarting Multi-AI Bug Investigation...")
        orchestrator = WorkflowOrchestrator(args.config)
        
        # Modern folder-based investigation
        result = orchestrator.run_investigation(
            bug_file=bug_file,
            codebase_folder=codebase_folder
        )
        
        if args.output_only:
            print(result)
        else:
            print(f"\nFinal Result saved to: {orchestrator.config['output']['definitive_fixes']}")
            print("\n" + "="*60)
            print("DEFINITIVE BUG FIXES")
            print("="*60)
            print(result)
        
    except FileNotFoundError as e:
        print(f"File Error: {e}")
        print("Tip: Run 'python main.py --setup' to create project structure")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Config Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()