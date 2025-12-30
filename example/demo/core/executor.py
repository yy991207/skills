from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SkillExecutor:
    """
    负责在本地（WSL环境）执行命令
    """
    def run_command(self, command: str) -> Dict[str, Any]:
        import subprocess
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "code": process.returncode,
                "output": stdout,
                "error": stderr
            }
        except Exception as e:
            return {
                "status": "exception",
                "message": str(e)
            }

    def execute_python_script(self, script_path: str, args: list = None) -> Dict[str, Any]:
        args_str = " ".join(args) if args else ""
        cmd = f"python {script_path} {args_str}"
        return self.run_command(cmd)
