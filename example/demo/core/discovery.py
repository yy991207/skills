from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from typing import List, Optional
from core.models import SkillMetadata
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SkillDiscovery:
    """
    基于LLM的技能发现，遵循Anthropic官方标准
    使用纯LLM推理，不使用关键词匹配或算法路由
    """
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def _sanitize(self, text: str) -> str:
        return text.encode('utf-8', 'ignore').decode('utf-8')

    def discover_skill(self, task: str, available_skills: List[SkillMetadata]) -> Optional[SkillMetadata]:
        """
        使用LLM基于元数据选择最合适的技能
        """
        if not available_skills:
            logger.warning("没有可用的技能用于发现")
            return None
        
        # 清理任务输入
        task = self._sanitize(task)
        
        # 构建仅包含元数据的上下文（每个技能约100个token）
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
            
            # 查找匹配的技能 - 精确匹配或子字符串匹配
            match = next((s for s in available_skills if s["name"].lower() == selected_name or selected_name in s["name"].lower()), None)
            
            if match:
                logger.info(f"🎯 最终命中技能: {match['name']} (路径: {match['path']})")
            else:
                logger.warning(f"⚠️  LLM 建议了不存在的技能: {selected_name}")
            return match
            
        except Exception as e:
            logger.error(f"[发现] LLM调用失败: {e}")
            return None
