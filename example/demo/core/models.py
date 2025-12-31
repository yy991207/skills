from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

class SkillMetadata(TypedDict):
    name: str
    description: str
    path: str

class SkillFull(TypedDict):
    name: str
    description: str
    path: str
    instructions: str

class AgentState(TypedDict):
    task: str
    available_skills: List[SkillMetadata]
    selected_skill: Optional[SkillFull]
    messages: Annotated[List[BaseMessage], operator.add]
    result: str
    conversation_history: List[dict]
    is_continue: bool
