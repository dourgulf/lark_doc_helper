#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

// Configuration
const SKILLS_ROOT = path.join(os.homedir(), '.cursor', 'skills');
const PROJECT_ROOT = path.resolve(__dirname, '..');
const SCRIPTS_DIR = path.join(PROJECT_ROOT, 'scripts');

const SKILLS = [
    {
        name: "lark-doc-to-markdown",
        configFile: path.join(PROJECT_ROOT, "SKILL.md")
    },
    {
        name: "markdown-to-lark-doc",
        configFile: path.join(PROJECT_ROOT, "SKILL_markdown_to_lark_doc.md")
    }
];

function install() {
    console.log(`🚀 Starting to install skills to: ${SKILLS_ROOT}`);

    SKILLS.forEach(skill => {
        const skillName = skill.name;
        const configFile = skill.configFile;
        
        const targetDir = path.join(SKILLS_ROOT, skillName);
        const targetScriptsDir = path.join(targetDir, 'scripts');

        console.log(`\n--------------------------------------------------`);
        console.log(`📦 Installing Skill: ${skillName}`);
        console.log(`--------------------------------------------------`);

        // 1. Create directories
        try {
            if (!fs.existsSync(targetDir)) {
                console.log(`  + Creating directory: ${targetDir}`);
                fs.mkdirSync(targetDir, { recursive: true });
            }
            if (!fs.existsSync(targetScriptsDir)) {
                console.log(`  + Creating directory: ${targetScriptsDir}`);
                fs.mkdirSync(targetScriptsDir, { recursive: true });
            }
        } catch (e) {
            console.error(`  ! Error creating directories: ${e.message}`);
            return;
        }

        // 2. Copy SKILL.md
        if (fs.existsSync(configFile)) {
            const targetConfigPath = path.join(targetDir, 'SKILL.md');
            console.log(`  -> Copying config: ${path.basename(configFile)} to ${targetConfigPath}`);
            fs.copyFileSync(configFile, targetConfigPath);
        } else {
            console.warn(`  ! Warning: Config file ${configFile} not found!`);
        }

        // 3. Copy scripts
        console.log(`  -> Copying scripts from ${SCRIPTS_DIR} to ${targetScriptsDir}`);
        if (fs.existsSync(SCRIPTS_DIR)) {
            const items = fs.readdirSync(SCRIPTS_DIR);
            items.forEach(item => {
                const srcPath = path.join(SCRIPTS_DIR, item);
                const dstPath = path.join(targetScriptsDir, item);
                
                // Skip __pycache__, .env, .DS_Store
                if (['__pycache__', '.env', '.DS_Store'].includes(item)) return;

                if (fs.statSync(srcPath).isFile()) {
                    fs.copyFileSync(srcPath, dstPath);
                }
            });
        } else {
            console.error(`  ! Error: Scripts directory not found at ${SCRIPTS_DIR}`);
            return;
        }

        // 4. Copy requirements.txt
        const reqFile = path.join(PROJECT_ROOT, 'requirements.txt');
        if (fs.existsSync(reqFile)) {
            const targetReq = path.join(targetDir, 'requirements.txt');
            console.log(`  -> Copying requirements.txt to ${targetReq}`);
            fs.copyFileSync(reqFile, targetReq);

            // 5. Setup Python venv and install requirements
            console.log(`  🐍 Setting up Python environment...`);
            try {
                // Check python command
                let pythonCmd = 'python3';
                try {
                    execSync('python3 --version', { stdio: 'ignore' });
                } catch (e) {
                    try {
                        execSync('python --version', { stdio: 'ignore' });
                        pythonCmd = 'python';
                    } catch (e) {
                        console.error('  ! Error: Python 3 not found. Please install Python 3.');
                        return;
                    }
                }

                // Create venv
                if (!fs.existsSync(path.join(targetDir, 'venv'))) {
                    console.log(`     Creating venv...`);
                    execSync(`${pythonCmd} -m venv venv`, { cwd: targetDir, stdio: 'inherit' });
                } else {
                    console.log(`     venv already exists, skipping creation.`);
                }

                // Install requirements
                console.log(`     Installing requirements...`);
                const pipCmd = process.platform === 'win32' 
                    ? path.join('venv', 'Scripts', 'pip') 
                    : path.join('venv', 'bin', 'pip');
                
                execSync(`"${path.join(targetDir, pipCmd)}" install -r requirements.txt`, { cwd: targetDir, stdio: 'inherit' });
                
                console.log(`  ✅ Python environment ready.`);

            } catch (e) {
                console.error(`  ! Error setting up Python environment: ${e.message}`);
            }
        }

        console.log(`  ℹ️  Note: Ensure .env file exists in ${targetDir} or your project root when using this skill.`);
    });

    console.log(`\n✅ All skills installed successfully!`);
}

install();
