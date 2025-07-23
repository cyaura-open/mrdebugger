import sys
from ai_client import AIClientFactory
import yaml
import pathlib
import argparse

def test_api_connection(provider_name: str, config: dict) -> bool:
    """Test API connection with a simple request"""
    try:
        print(f"Testing {provider_name.upper()} connection...")
        client = AIClientFactory.create_client(provider_name, config)
        
        # Simple test prompt
        test_prompt = "Respond with exactly: 'Connection successful'"
        response = client.send_message(test_prompt, retry_attempts=1)
        
        if "Connection successful" in response or "successful" in response.lower():
            print(f"{provider_name.upper()} connection: SUCCESS")
            return True
        else:
            print(f"{provider_name.upper()} connection: PARTIAL (got response but unexpected format)")
            print(f"   Response: {response[:100]}...")
            return True  # Still working, just unexpected response
            
    except Exception as e:
        print(f"{provider_name.upper()} connection: FAILED")
        print(f"   Error: {str(e)}")
        return False


def test_all_connections(config_file: str = 'config.json'):
    """Test all configured API connections"""
    try:
        path = pathlib.Path(config_file)
        with open(path, 'r') as f:
            config = yaml.safe_load(f) if path.suffix.lower() in {'.yml', '.yaml'} else json.load(f)
    except FileNotFoundError:
        print(f"Config file {config_file} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}")
        return False
    
    print("Testing API Connections...\n")
    
    apis_config = config['apis']
    workflow_config = config['workflow']
    
    results = {}
    
    # Test all configured APIs
    for provider_name, provider_config in apis_config.items():
        if not provider_config.get('api_key') or provider_config['api_key'] == f"your_{provider_name}_api_key_here":
            print(f"Skipping {provider_name.upper()}: API key not configured")
            results[provider_name] = False
            continue
            
        results[provider_name] = test_api_connection(provider_name, provider_config)
    
    print("\nConnection Test Summary:")
    print("=" * 40)
    
    all_success = True
    for provider, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{provider.upper()}: {status}")
        if not success:
            all_success = False
    
    # Check workflow configuration
    print(f"\nWorkflow Configuration:")
    ai_a = workflow_config['ai_a']
    ai_b = workflow_config['ai_b'] 
    final_ai = workflow_config['final_arbitrator']
    
    print(f"AI_A: {ai_a.upper()} {'OK' if results.get(ai_a, False) else 'FAIL'}")
    print(f"AI_B: {ai_b.upper()} {'OK' if results.get(ai_b, False) else 'FAIL'}")
    print(f"Final AI: {final_ai.upper()} {'OK' if results.get(final_ai, False) else 'FAIL'}")
    
    if all_success:
        print(f"\nAll connections successful! Ready to run bug investigation.")
    else:
        print(f"\nSome connections failed. Check API keys and configuration.")
    
    return all_success


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Test API connections')
    parser.add_argument('--config', default='config.json', help='Configuration file')
    args = parser.parse_args()
    
    success = test_all_connections(args.config)
    sys.exit(0 if success else 1)