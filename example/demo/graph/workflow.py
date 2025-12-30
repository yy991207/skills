from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from core.models import AgentState, SkillFull
from core.discovery import SkillDiscovery
from core.loader import SkillLoader
from core.executor import SkillExecutor
from utils.logger import setup_logger
import yaml
import os
import re

logger = setup_logger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Initialize components
llm = ChatOpenAI(
    model=config["llm"]["model"],
    openai_api_key=config["llm"]["api_key"],
    openai_api_base=config["llm"]["base_url"]
)

skill_loader = SkillLoader(config["paths"]["skills_dir"])
skill_discovery = SkillDiscovery(llm)
skill_executor = SkillExecutor()

def discover_node(state: AgentState):
    """
    Node 1: Skill Discovery using LLM reasoning on metadata ONLY
    """
    logger.info("Step 1: Discovering relevant skill based on metadata...")
    
    task = state["task"]
    available_skills = state["available_skills"]
    
    selected_metadata = skill_discovery.discover_skill(task, available_skills)
    
    if selected_metadata:
        logger.info(f"✓ Found match: {selected_metadata['name']}")
        return {"selected_skill": {"name": selected_metadata["name"], 
                                    "description": selected_metadata["description"],
                                    "path": selected_metadata["path"],
                                    "instructions": ""}}
    else:
        logger.info("✗ No specialized skill required for this task")
        return {"selected_skill": None}

def load_node(state: AgentState):
    """
    Node 2: Load full SKILL.md instructions
    """
    selected = state.get("selected_skill")
    if not selected:
        return {}
    
    logger.info(f"Step 2: Activating skill '{selected['name']}' (loading instructions)...")
    
    skill_path = selected["path"]
    instructions = skill_loader.load_full_instructions(skill_path)
    
    updated_skill: SkillFull = {
        "name": selected["name"],
        "description": selected["description"],
        "path": skill_path,
        "instructions": instructions
    }
    
    return {"selected_skill": updated_skill}

def execute_node(state: AgentState):
    """
    Node 3: Execute using LLM + loaded instructions
    Includes automatic retry with error feedback
    """
    MAX_RETRIES = 3
    
    logger.info("Step 3: Generating execution plan and running code...")
    
    selected = state.get("selected_skill")
    task = state.get("task")
    
    if not selected:
        available = state.get("available_skills", [])
        skill_names = ", ".join([s["name"] for s in available])
        result = "Using general reasoning (no specialized skill matched)."
        return {"result": result}
    
    instructions = selected.get("instructions", "")
    skill_path = selected["path"]
    
    # Initial prompt
    base_prompt = f"""You are a task automation assistant with access to the '{selected['name']}' skill.

=== SKILL INSTRUCTIONS ===
{instructions}

=== USER TASK ===
{task}

Generate Python code that accomplishes the task according to the skill instructions.
IMPORTANT: Output ONLY a Python code block. Do NOT output HTML, CSS, or JavaScript directly.
If the task requires generating web content, write Python code that creates and saves the file."""

    logger.info("\n" + "-"*30 + " [EXECUTION PROMPT] " + "-"*30)
    logger.info(f"Target Skill: {selected['name']}")
    logger.info(f"Task: {task}")
    logger.info("-" * 80)

    current_prompt = base_prompt
    last_error = None
    
    # Detailed log of the full prompt (including instructions)
    logger.info("\n" + "="*20 + " [FULL LLM PROMPT START] " + "="*20)
    logger.info(current_prompt)
    logger.info("="*20 + " [FULL LLM PROMPT END] " + "="*20 + "\n")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"\n[Attempt {attempt}/{MAX_RETRIES}] Calling LLM for code generation...")
            
            print(f"\n" + "-"*25 + f" [LLM OUTPUT - Attempt {attempt}] " + "-"*25)
            full_content = []
            for chunk in llm.stream([SystemMessage(content=current_prompt)]):
                content_chunk = chunk.content
                if content_chunk:
                    print(content_chunk, end="", flush=True)
                    full_content.append(content_chunk)
            
            content = "".join(full_content)
            print("\n" + "-" * 80)
            
            # Extract code block
            code_match = re.search(r"```python\n(.*)```", content, re.DOTALL)
            if not code_match:
                code_match = re.search(r"```\n(.*)```", content, re.DOTALL)
            
            if not code_match:
                last_error = "No valid Python code block found in LLM output."
                logger.warning(f"[Attempt {attempt}] {last_error}")
                current_prompt = base_prompt + f"\n\n=== PREVIOUS ERROR ===\n{last_error}\nPlease output ONLY a ```python code block."
                continue
            
            code = code_match.group(1).strip()
            temp_script = "temp_skill_script.py"
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Setup environment
            env = os.environ.copy()
            current_pythonpath = env.get("PYTHONPATH", "")
            
            # Add skill_path and its potential internal subdirectories
            new_paths = [
                skill_path, 
                os.path.join(skill_path, "ooxml"), 
                os.path.join(skill_path, "scripts"),
                os.path.join(skill_path, "ooxml", "ooxml")
            ]
            unique_paths = [p for p in new_paths if os.path.exists(p)]
            
            env["PYTHONPATH"] = os.pathsep.join(unique_paths + ([current_pythonpath] if current_pythonpath else []))

            # Deep Trace Log for Environment
            logger.info("\n" + "⚙️  " + "="*15 + " [ENVIRONMENT SETUP] " + "="*15)
            logger.info(f"Temp Script: {os.path.abspath(temp_script)}")
            logger.info(f"Injected PYTHONPATH:")
            for p in unique_paths:
                logger.info(f"  - {p}")
            logger.info("="*50 + "\n")

            logger.info(f"🚀 Executing: python {temp_script}")
            
            import subprocess
            process = subprocess.Popen(
                f"python {temp_script}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            stdout, stderr = process.communicate()
            
            logger.info("\n" + "-"*30 + " [EXECUTION RESULT] " + "-"*30)
            if process.returncode == 0:
                logger.info("Status: SUCCESS")
                logger.info(f"Stdout:\n{stdout}")
                result = f"Success! Output:\n{stdout}"
                logger.info("-" * 80)
                return {"result": result, "messages": [HumanMessage(content=result)]}
            else:
                last_error = stderr
                logger.info(f"Status: FAILED (Attempt {attempt})")
                logger.info(f"Stderr:\n{stderr}")
                logger.info("-" * 80)
                
                if attempt < MAX_RETRIES:
                    # Prepare retry prompt with error feedback
                    current_prompt = base_prompt + f"""

=== PREVIOUS CODE FAILED ===
```python
{code}
```

=== ERROR MESSAGE ===
{stderr}

Please fix the code based on the error message above. Output ONLY the corrected Python code block."""
                    logger.info(f"Retrying with error feedback...")
                    
        except Exception as e:
            last_error = str(e)
            logger.error(f"[Attempt {attempt}] Exception: {e}")
            if attempt < MAX_RETRIES:
                current_prompt = base_prompt + f"\n\n=== PREVIOUS ERROR ===\n{last_error}\nPlease try again."
    
    # All retries exhausted
    result = f"Failed after {MAX_RETRIES} attempts. Last error:\n{last_error}"
    logger.error(result)
    return {"result": result, "messages": [HumanMessage(content=result)]}


# Build graph
builder = StateGraph(AgentState)
builder.add_node("discover", discover_node)
builder.add_node("load", load_node)
builder.add_node("execute", execute_node)

builder.set_entry_point("discover")
builder.add_edge("discover", "load")
builder.add_edge("load", "execute")
builder.add_edge("execute", END)

workflow = builder.compile()
