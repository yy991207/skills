from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from typing import List, Optional
from core.models import SkillMetadata
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SkillDiscovery:
    """
    LLM-based skill discovery following official Anthropic standards
    Uses pure LLM reasoning, NOT keyword matching or algorithmic routing
    """
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def _sanitize(self, text: str) -> str:
        return text.encode('utf-8', 'ignore').decode('utf-8')

    def discover_skill(self, task: str, available_skills: List[SkillMetadata]) -> Optional[SkillMetadata]:
        """
        Use LLM to select the most appropriate skill based on metadata ONLY
        """
        if not available_skills:
            logger.warning("No skills available for discovery")
            return None
        
        # Sanitize task input
        task = self._sanitize(task)
        
        # Build metadata-only context (~100 tokens per skill)
        skill_list = "\n".join([
            f"- **{skill['name']}**: {self._sanitize(skill['description'][:150])}..."
            for skill in available_skills
        ])
        
        prompt = f"""You are a skill discovery system. Based on the user's task, select the MOST appropriate skill from the available skills list.

Available Skills:
{skill_list}

User Task: {task}

Instructions:
1. Analyze which skill best matches the task requirements
2. Return ONLY the skill name (e.g., "docx", "pdf", "pptx")
3. If no skill matches, return "NONE"

Your response must be a single word - the skill name or "NONE"."""

        logger.info("\n" + "="*20 + " [SKILL DISCOVERY PROMPT START] " + "="*20)
        logger.info(prompt)
        logger.info("="*20 + " [SKILL DISCOVERY PROMPT END] " + "="*20 + "\n")

        try:
            logger.info(f"发送任务匹配请求... (候选技能数: {len(available_skills)})")
            response = self.llm.invoke([SystemMessage(content=prompt)])
            selected_name = response.content.strip().lower()
            
            logger.info(f"LLM 原始决策输出: '{selected_name}'")
            
            if selected_name == "none":
                return None
            
            # Find matching skill - exact or substring
            match = next((s for s in available_skills if s["name"].lower() == selected_name or selected_name in s["name"].lower()), None)
            
            if match:
                logger.info(f"🎯 最终命中技能: {match['name']} (路径: {match['path']})")
            else:
                logger.warning(f"⚠️  LLM 建议了不存在的技能: {selected_name}")
            return match
            
        except Exception as e:
            logger.error(f"[DISCOVERY] LLM call failed: {e}")
            return None
