import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.workflow import workflow, skill_loader
from utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    print("=== Agent Skills Demo (Official Standards) ===")
    print("Progressive Disclosure: Metadata -> Instructions -> Resources")
    print("Discovery: Pure LLM Reasoning (No Keywords)")
    print("\nType 'exit' or 'quit' to quit\n")
    
    logger.info("[启动] 正在加载技能元数据...")
    all_skills_metadata = skill_loader.load_all_metadata()
    logger.info(f"[启动] 已加载 {len(all_skills_metadata)} 个技能的元数据\n")
    
    conversation_history = []
    
    while True:
        user_input = input("Enter your task: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            print("Please enter a valid task\n")
            continue
        
        initial_state = {
            "task": user_input,
            "available_skills": all_skills_metadata,
            "selected_skill": None,
            "messages": [],
            "result": "",
            "conversation_history": conversation_history,
            "is_continue": True
        }
        
        print(f"\n\033[1m[🔍 Processing Task...]\033[0m")
        final_output = workflow.invoke(initial_state)
        
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
        
        conversation_history = final_output.get('conversation_history', [])

if __name__ == "__main__":
    main()
