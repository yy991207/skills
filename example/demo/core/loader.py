import os
import yaml
from typing import List, Optional
from core.models import SkillMetadata
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SkillLoader:
    """
    Progressive skill loader following official Anthropic standards
    Implements 3-layer loading: Metadata -> Instructions -> Resources
    """
    def __init__(self, skills_dir: str):
        self.skills_dir = os.path.abspath(skills_dir)
    
    def load_all_metadata(self) -> List[SkillMetadata]:
        """
        Layer 1: Load ONLY metadata (name + description) for all skills
        This should be ~100 tokens per skill
        """
        skills = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return skills

        # Determine if skills_dir points to 'skills' or parent
        if os.path.basename(self.skills_dir) == "skills":
            skills_root = self.skills_dir
        else:
            skills_root = os.path.join(self.skills_dir, "skills")
        
        if not os.path.exists(skills_root):
            logger.warning(f"Skills root not found: {skills_root}")
            return skills

        for entry in os.scandir(skills_root):
            if entry.is_dir():
                skill_file = os.path.join(entry.path, "SKILL.md")
                if os.path.exists(skill_file):
                    metadata = self._extract_metadata(skill_file)
                    if metadata:
                        metadata["path"] = entry.path
                        skills.append(metadata)
        
        logger.info(f"Loaded metadata for {len(skills)} skills")
        return skills

    def _sanitize_string(self, text: str) -> str:
        """Remove surrogate characters that cause UTF-8 encoding issues"""
        if not text:
            return ""
        # 'surrogatepass' would keep them, but HTTP libs usually fail. 
        # We'll use ignore/replace to be safe.
        return text.encode('utf-8', 'ignore').decode('utf-8')

    def _extract_metadata(self, skill_file: str) -> Optional[SkillMetadata]:
        """Extract ONLY frontmatter metadata (NOT full body)"""
        try:
            with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        meta_yaml = yaml.safe_load(parts[1])
                        return {
                            "name": self._sanitize_string(str(meta_yaml.get("name", "unknown"))),
                            "description": self._sanitize_string(str(meta_yaml.get("description", ""))),
                            "path": ""  # Will be set by caller
                        }
        except Exception as e:
            logger.error(f"Error extracting metadata from {skill_file}: {e}")
        return None

    def load_full_instructions(self, skill_path: str) -> str:
        """
        Layer 2: Load complete SKILL.md body and any MANDATORY referenced docs
        """
        logger.info("\n" + "="*20 + " [LAYER 2: INSTRUCTION LOADING] " + "="*20)
        logger.info(f"📁 技能根目录: {skill_path}")
        
        skill_file = os.path.join(skill_path, "SKILL.md")
        logger.info(f"📄 主指令文件: {skill_file}")
        
        if not os.path.exists(skill_file):
            logger.warning(f"⚠️  主指令文件不存在!")
            return ""
        
        logger.info(f"   ∟ 正在读取主指令文件...")
        with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        sanitized_content = self._sanitize_string(content)
        logger.info(f"   ∟ 主指令读取完成 ({len(sanitized_content)} 字符)")
        
        # Proactively load mandatory referenced files (Layer 3 items mentioned as Mandatory)
        # Search for pattern: Read [`filename.md`]
        import re
        mandatory_docs = re.findall(r"Read \[`(.*\.md)`\]", sanitized_content)
        
        logger.info(f"\n🔍 扫描关联文档引用...")
        if mandatory_docs:
            logger.info(f"   发现 {len(mandatory_docs)} 个关联文档引用: {mandatory_docs}")
        else:
            logger.info(f"   未发现强制关联文档")
        
        extra_docs = []
        loaded_files = set(["SKILL.md"])
        
        for doc_name in mandatory_docs:
            if doc_name in loaded_files:
                logger.info(f"   ∟ 跳过已加载: {doc_name}")
                continue
            
            doc_path = os.path.join(skill_path, doc_name)
            if os.path.exists(doc_path):
                logger.info(f"📂 加载关联文档: {doc_name}")
                logger.info(f"   ∟ 路径: {doc_path}")
                with open(doc_path, "r", encoding="utf-8", errors="ignore") as df:
                    extra_content = df.read()
                    sanitized_extra = self._sanitize_string(extra_content)
                    extra_docs.append(f"\n\n=== ATTACHED DOC: {doc_name} ===\n{sanitized_extra}")
                    loaded_files.add(doc_name)
                    logger.info(f"   ∟ 读取完成 ({len(sanitized_extra)} 字符), 已合并至上下文")
            else:
                logger.warning(f"⚠️  找不到关联文档: {doc_path}")
        
        full_instructions = sanitized_content + "".join(extra_docs)
        logger.info(f"\n✅ [LOADER] 指令集构建完成")
        logger.info(f"   ∟ 主文档: {len(sanitized_content)} 字符")
        logger.info(f"   ∟ 关联文档: {len(extra_docs)} 个, 共 {sum(len(d) for d in extra_docs)} 字符")
        logger.info(f"   ∟ 总长度: {len(full_instructions)} 字符")
        logger.info("="*60 + "\n")
        return full_instructions


    def load_resource(self, skill_path: str, resource_path: str) -> str:
        """
        Layer 3: Load specific resource file (scripts/, references/, assets/)
        Only called when explicitly needed by SKILL.md
        """
        full_path = os.path.join(skill_path, resource_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Loaded resource: {resource_path}")
                return content
        logger.warning(f"Resource not found: {resource_path}")
        return ""
