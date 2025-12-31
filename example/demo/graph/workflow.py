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

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

llm = ChatOpenAI(
    model=config["llm"]["model"],
    openai_api_key=config["llm"]["api_key"],
    openai_api_base=config["llm"]["base_url"]
)

skill_loader = SkillLoader(config["paths"]["skills_dir"])
skill_discovery = SkillDiscovery(llm)
skill_executor = SkillExecutor()

def discover_node(state: AgentState):
    logger.info("步骤1：基于元数据发现相关技能...")
    
    task = state["task"]
    available_skills = state["available_skills"]
    
    selected_metadata = skill_discovery.discover_skill(task, available_skills)
    
    if selected_metadata:
        logger.info(f"✓ 找到匹配: {selected_metadata['name']}")
        return {"selected_skill": {"name": selected_metadata["name"], 
                                    "description": selected_metadata["description"],
                                    "path": selected_metadata["path"],
                                    "instructions": ""}}
    else:
        logger.info("✗ 此任务不需要专业技能")
        return {"selected_skill": None}

def conversation_node(state: AgentState):
    logger.info("对话节点：处理用户输入...")
    
    task = state["task"]
    conversation_history = state.get("conversation_history", [])
    
    conversation_history.append({
        "role": "user",
        "content": task
    })
    
    return {"conversation_history": conversation_history}

def interaction_node(state: AgentState):
    logger.info("交互节点：与skills模块通信...")
    
    selected = state.get("selected_skill")
    task = state.get("task")
    conversation_history = state.get("conversation_history", [])
    
    if not selected:
        logger.info("未选择技能，使用通用对话")
        response = "I understand your request. Let me help you with that."
        conversation_history.append({
            "role": "assistant",
            "content": response
        })
        return {
            "result": response,
            "conversation_history": conversation_history
        }
    
    skill_name = selected.get("name", "unknown")
    logger.info(f"与技能交互: {skill_name}")
    
    response = f"Using {skill_name} skill to process: {task}"
    conversation_history.append({
        "role": "assistant",
        "content": response
    })
    
    return {
        "result": response,
        "conversation_history": conversation_history
    }

def check_continue_node(state: AgentState):
    logger.info("检查继续节点：确定对话是否应继续...")
    
    task = state.get("task", "").lower()
    is_continue = not any(keyword in task for keyword in ['exit', 'quit', 'bye', '结束', '再见'])
    
    return {"is_continue": is_continue}

def load_node(state: AgentState):
    selected = state.get("selected_skill")
    if not selected:
        return {}
    
    logger.info(f"步骤2：激活技能 '{selected['name']}' （加载指令）...")
    
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
    MAX_RETRIES = 3
    
    logger.info("步骤3：生成执行计划并运行代码...")
    
    selected = state.get("selected_skill")
    task = state.get("task")
    
    if not selected:
        available = state.get("available_skills", [])
        skill_names = ", ".join([s["name"] for s in available])
        result = "使用通用推理（未匹配到专业技能）。"
        return {"result": result}
    
    instructions = selected.get("instructions", "")
    skill_path = selected["path"]
    
    base_prompt = f"""You are a task automation assistant with access to the '{selected['name']}' skill.

=== 技能指令 ===
{instructions}

=== 用户任务 ===
{task}

根据技能指令生成完成任务的Python代码。
重要：仅输出Python代码块。不要直接输出HTML、CSS或JavaScript。
如果任务需要生成网页内容，请编写创建并保存文件的Python代码。"""

    logger.info("\n" + "-"*30 + " [执行提示] " + "-"*30)
    logger.info(f"目标技能: {selected['name']}")
    logger.info(f"任务: {task}")
    logger.info("-" * 80)

    current_prompt = base_prompt
    last_error = None
    
    logger.info("\n" + "="*20 + " [完整LLM提示开始] " + "="*20)
    logger.info(current_prompt)
    logger.info("="*20 + " [完整LLM提示结束] " + "="*20 + "\n")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"\n[尝试 {attempt}/{MAX_RETRIES}] 调用LLM生成代码...")
            
            print(f"\n" + "-"*25 + f" [LLM输出 - 尝试 {attempt}] " + "-"*25)
            full_content = []
            for chunk in llm.stream([SystemMessage(content=current_prompt)]):
                content_chunk = chunk.content
                if content_chunk:
                    print(content_chunk, end="", flush=True)
                    full_content.append(content_chunk)
            
            content = "".join(full_content)
            print("\n" + "-" * 80)
            
            code_match = re.search(r"```python\n(.*)```", content, re.DOTALL)
            if not code_match:
                code_match = re.search(r"```\n(.*)```", content, re.DOTALL)
            
            if not code_match:
                last_error = "LLM输出中未找到有效的Python代码块。"
                logger.warning(f"[尝试 {attempt}] {last_error}")
                current_prompt = base_prompt + f"\n\n=== 之前的错误 ===\n{last_error}\n请仅输出```python代码块。"
                continue
            
            code = code_match.group(1).strip()
            temp_script = "temp_skill_script.py"
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(code)
            
            env = os.environ.copy()
            current_pythonpath = env.get("PYTHONPATH", "")
            
            new_paths = [
                skill_path, 
                os.path.join(skill_path, "ooxml"), 
                os.path.join(skill_path, "scripts"),
                os.path.join(skill_path, "ooxml", "ooxml")
            ]
            unique_paths = [p for p in new_paths if os.path.exists(p)]
            
            env["PYTHONPATH"] = os.pathsep.join(unique_paths + ([current_pythonpath] if current_pythonpath else []))

            logger.info("\n" + "⚙️  " + "="*15 + " [环境设置] " + "="*15)
            logger.info(f"临时脚本: {os.path.abspath(temp_script)}")
            logger.info(f"注入的PYTHONPATH:")
            for p in unique_paths:
                logger.info(f"  - {p}")
            logger.info("="*50 + "\n")

            logger.info(f"🚀 执行: python {temp_script}")
            
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
            
            logger.info("\n" + "-"*30 + " [执行结果] " + "-"*30)
            if process.returncode == 0:
                logger.info("状态: 成功")
                logger.info(f"标准输出:\n{stdout}")
                result = f"成功！输出:\n{stdout}"
                logger.info("-" * 80)
                return {"result": result, "messages": [HumanMessage(content=result)]}
            else:
                last_error = stderr
                logger.info(f"状态: 失败 (尝试 {attempt})")
                logger.info(f"标准错误:\n{stderr}")
                logger.info("-" * 80)
                
                if attempt < MAX_RETRIES:
                    current_prompt = base_prompt + f"""

=== 之前的代码失败 ===
```python
{code}
```

=== 错误信息 ===
{stderr}

请根据上述错误信息修复代码。仅输出修正后的Python代码块。"""
                    logger.info(f"使用错误反馈重试...")
                    
        except Exception as e:
            last_error = str(e)
            logger.error(f"[尝试 {attempt}] 异常: {e}")
            if attempt < MAX_RETRIES:
                current_prompt = base_prompt + f"\n\n=== 之前的错误 ===\n{last_error}\n请重试。"
    
    result = f"在{MAX_RETRIES}次尝试后失败。最后的错误:\n{last_error}"
    logger.error(result)
    return {"result": result, "messages": [HumanMessage(content=result)]}


builder = StateGraph(AgentState)
builder.add_node("discover", discover_node)
builder.add_node("conversation", conversation_node)
builder.add_node("interaction", interaction_node)
builder.add_node("check_continue", check_continue_node)
builder.add_node("load", load_node)
builder.add_node("execute", execute_node)

builder.set_entry_point("discover")
builder.add_edge("discover", "conversation")
builder.add_edge("conversation", "interaction")
builder.add_edge("interaction", "check_continue")

def should_continue(state: AgentState):
    return state.get("is_continue", False)

builder.add_conditional_edges(
    "check_continue",
    should_continue,
    {
        True: "load",
        False: END
    }
)

builder.add_edge("load", "execute")
builder.add_edge("execute", END)

workflow = builder.compile()
