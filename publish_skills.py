import os
import shutil
from pathlib import Path

# 配置目标 Skill 根目录
# 默认为 ~/.cursor/skills
SKILLS_ROOT = Path.home() / ".cursor" / "skills"

# 当前项目路径
PROJECT_ROOT = Path(__file__).parent.absolute()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# 定义要发布的 Skill 列表
# name: Skill 目录名
# config_file: 对应的 SKILL.md 源文件
SKILLS = [
    {
        "name": "lark-doc-to-markdown",
        "config_file": PROJECT_ROOT / "skills" / "lark-doc-to-markdown" / "SKILL.md"
    },
    {
        "name": "markdown-to-lark-doc",
        "config_file": PROJECT_ROOT / "skills" / "markdown-to-lark-doc" / "SKILL.md"
    }
]

def publish():
    """将当前项目的脚本和配置发布到 Skill 目录"""
    
    if not SCRIPTS_DIR.exists():
        print(f"Error: Scripts directory not found at {SCRIPTS_DIR}")
        return

    print(f"🚀 Starting to publish skills to: {SKILLS_ROOT}")

    for skill in SKILLS:
        skill_name = skill["name"]
        config_file = skill["config_file"]
        
        target_dir = SKILLS_ROOT / skill_name
        target_scripts_dir = target_dir / "scripts"
        
        print(f"\n--------------------------------------------------")
        print(f"📦 Publishing Skill: {skill_name}")
        print(f"--------------------------------------------------")
        
        # 1. 创建目标目录
        try:
            if not target_dir.exists():
                print(f"  + Creating directory: {target_dir}")
                target_dir.mkdir(parents=True, exist_ok=True)
                
            if not target_scripts_dir.exists():
                print(f"  + Creating directory: {target_scripts_dir}")
                target_scripts_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"  ! Error creating directories: {e}")
            continue
            
        # 2. 复制 SKILL.md 配置文件
        if config_file.exists():
            target_config_path = target_dir / "SKILL.md"
            print(f"  -> Copying config: {config_file.name} to {target_config_path}")
            shutil.copy2(config_file, target_config_path)
        else:
            print(f"  ! Warning: Config file {config_file} not found!")

        # 3. 复制 scripts 目录下的所有文件
        print(f"  -> Copying scripts from {SCRIPTS_DIR} to {target_scripts_dir}")
        for item in os.listdir(SCRIPTS_DIR):
            src_path = SCRIPTS_DIR / item
            dst_path = target_scripts_dir / item
            
            # 显式排除 __pycache__ 和 .env 以及其他不需要的文件
            if item in ["__pycache__", ".env", ".DS_Store"]:
                continue
                
            # 只复制文件
            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
        
        # 4. 复制 requirements.txt (如果有)
        req_file = PROJECT_ROOT / "requirements.txt"
        if req_file.exists():
             target_req = target_dir / "requirements.txt"
             print(f"  -> Copying requirements.txt to {target_req}")
             shutil.copy2(req_file, target_req)
        
        # 5. 提示用户可能需要配置 .env
        print(f"  ℹ️  Note: Ensure .env file exists in the directory where you run this skill.")

    print(f"\n✅ All skills published successfully!")

if __name__ == "__main__":
    publish()
