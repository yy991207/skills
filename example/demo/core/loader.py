import os
import yaml
from typing import List, Optional
from core.models import SkillMetadata
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SkillLoader:
    """
    渐进式技能加载器，遵循Anthropic官方标准
    实现3层加载：元数据 -> 指令 -> 资源
    """
    def __init__(self, skills_dir: str):
        self.skills_dir = os.path.abspath(skills_dir)
    
    def load_all_metadata(self) -> List[SkillMetadata]:
        """
        第1层：仅加载所有技能的元数据（名称 + 描述）
        每个技能约100个token
        """
        skills = []
        if not os.path.exists(self.skills_dir):
            logger.warning(f"未找到技能目录: {self.skills_dir}")
            return skills

        # 判断skills_dir指向'skills'目录还是其父目录
        if os.path.basename(self.skills_dir) == "skills":
            skills_root = self.skills_dir
        else:
            skills_root = os.path.join(self.skills_dir, "skills")
        
        if not os.path.exists(skills_root):
            logger.warning(f"未找到技能根目录: {skills_root}")
            return skills

        for entry in os.scandir(skills_root):
            if entry.is_dir():
                skill_file = os.path.join(entry.path, "SKILL.md")
                if os.path.exists(skill_file):
                    metadata = self._extract_metadata(skill_file)
                    if metadata:
                        metadata["path"] = entry.path
                        skills.append(metadata)
        
        logger.info(f"已加载 {len(skills)} 个技能的元数据")
        return skills

    def _sanitize_string(self, text: str) -> str:
        """移除导致UTF-8编码问题的代理字符"""
        if not text:
            return ""
        # 'surrogatepass'会保留这些字符，但HTTP库通常会失败
        # 我们使用ignore/replace来确保安全
        return text.encode('utf-8', 'ignore').decode('utf-8')

    def _extract_metadata(self, skill_file: str) -> Optional[SkillMetadata]:
        """仅提取frontmatter元数据（不包含完整内容）"""
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
                            "path": ""  # 将由调用者设置
                        }
        except Exception as e:
            logger.error(f"从{skill_file}提取元数据时出错: {e}")
        return None

    def load_full_instructions(self, skill_path: str) -> str:
        """
        第2层：加载完整的SKILL.md主体内容以及所有强制引用的文档
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
        
        # 主动加载强制引用的文件（第3层中标记为Mandatory的项目）
        # 搜索模式：Read [`filename.md`]
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
        第3层：加载特定资源文件（scripts/、references/、assets/）
        仅在SKILL.md明确需要时调用
        """
        full_path = os.path.join(skill_path, resource_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"已加载资源: {resource_path}")
                return content
        logger.warning(f"未找到资源: {resource_path}")
        return ""
