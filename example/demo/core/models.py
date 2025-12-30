from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

class SkillMetadata(TypedDict):
    """Lightweight metadata for skill discovery (Layer 1)"""
    name: str
    description: str
    path: str

class SkillFull(TypedDict):
    """Complete skill information with instructions (Layer 2)"""
    name: str
    description: str
    path: str
    instructions: str  # Full SKILL.md body content

class AgentState(TypedDict):
    """LangGraph state with progressive disclosure support"""
    # User request
    task: str
    
    # Layer 1: All available skill metadata (loaded at startup)
    available_skills: List[SkillMetadata]
    
    # Layer 2: Selected skill with full instructions (loaded on activation)
    selected_skill: Optional[SkillFull]
    
    # Execution context
    messages: Annotated[List[BaseMessage], operator.add]
    result: str
