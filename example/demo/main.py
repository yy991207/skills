import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.workflow import workflow, skill_loader
from utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    print("=== Agent Skills Demo (Official Standards) ===")
    print("Progressive Disclosure: Metadata → Instructions → Resources")
    print("Discovery: Pure LLM Reasoning (No Keywords)")
    print("\nType 'exit' or 'quit' to quit\n")
    
    # Layer 1: Load ALL skill metadata at startup (~100 tokens each)
    logger.info("[STARTUP] Loading skill metadata...")
    all_skills_metadata = skill_loader.load_all_metadata()
    logger.info(f"[STARTUP] Loaded metadata for {len(all_skills_metadata)} skills\n")
    
    while True:
        user_input = input("Enter your task: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            print("Please enter a valid task\n")
            continue
        
        # Initialize state with metadata-only
        initial_state = {
            "task": user_input,
            "available_skills": all_skills_metadata,  # Layer 1 only
            "selected_skill": None,
            "messages": [],
            "result": ""
        }
        
        print(f"\n\033[1m[🔍 Processing Task...]\033[0m")
        final_output = workflow.invoke(initial_state)
        
        # Clear separation for final result
        print("\n" + "━" * 65)
        print("\033[1;92m✨ AGENT RESPONSE\033[0m")
        print("━" * 65)
        
        selected = final_output.get('selected_skill')
        if selected:
            print(f"\033[96mSkill Used:\033[0m {selected.get('name')}")
            print(f"\033[96mSOP Loaded:\033[0m {len(selected.get('instructions', ''))} characters")
        else:
            print(f"\033[90mSkill Used:\033[0m None (General Reasoning)")
        
        print(f"\n\033[1mFinal Result:\033[0m")
        print(f"{final_output.get('result')}")
        print("━" * 65 + "\n")

if __name__ == "__main__":
    main()
