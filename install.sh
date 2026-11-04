#!/usr/bin/env bash
#
# disk-raccoon 智能安装脚本
# 自动探测系统中的 AI Agent 环境并创建软链接
#

set -e

VERSION="0.2.0"
REPO_URL="https://github.com/tasselx/disk-raccoon.git"
INSTALL_DIR="${HOME}/.config/disk-raccoon"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   🦝 硬盘小浣熊 (disk-raccoon) v${VERSION}   ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 1. 检查操作系统
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}❌ 错误: disk-raccoon 是专为 macOS 设计的缓存清理工具。${NC}"
    exit 1
fi

# 2. 检查 Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ 错误: 未检测到 python3，macOS 需安装 Command Line Tools 或 Python 3。${NC}"
    exit 1
fi

# 3. 确定源码目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [[ -f "${SCRIPT_DIR}/SKILL.md" && -f "${SCRIPT_DIR}/scripts/fast-scan.py" ]]; then
    # 本地已有仓库，直接以当前目录为基准
    TARGET_SOURCE="${SCRIPT_DIR}"
    echo -e "${GREEN}✓ 使用当前本地仓库: ${TARGET_SOURCE}${NC}"
else
    # 远程安装模式：clone 到 ~/.config/disk-raccoon
    TARGET_SOURCE="${INSTALL_DIR}"
    if [[ -d "${TARGET_SOURCE}/.git" ]]; then
        echo -e "${YELLOW}ℹ 目标目录已存在，正在拉取最新代码...${NC}"
        git -C "${TARGET_SOURCE}" pull --quiet
    else
        echo -e "${BLUE}⬇ 正在克隆仓库到 ${TARGET_SOURCE}...${NC}"
        mkdir -p "$(dirname "${TARGET_SOURCE}")"
        git clone --quiet "${REPO_URL}" "${TARGET_SOURCE}"
    fi
fi

# 赋予探针执行权限
chmod +x "${TARGET_SOURCE}/scripts/fast-scan.py"

# 4. 自动检测系统中的 AI Agent 并安装软链接
declare -a AGENT_DIRS=(
    "${HOME}/.claude/skills"                 # Claude Code
    "${HOME}/.gemini/skills"                 # Google Antigravity / Gemini
    "${HOME}/.gemini/config/skills"          # Antigravity Config
    "${HOME}/.codex/skills"                  # Codex
    "${HOME}/.cline/skills"                  # Cline
)

LINKED_COUNT=0

echo -e "\n${BLUE}🔍 正在探测已安装的 AI Agent 环境...${NC}"

for dir in "${AGENT_DIRS[@]}"; do
    # 如果父目录存在，说明安装了该 agent，或者直接为常用 agent 自动创建
    parent_dir="$(dirname "$dir")"
    if [[ -d "$parent_dir" ]]; then
        mkdir -p "$dir"
        target_link="${dir}/disk-raccoon"
        ln -sfn "${TARGET_SOURCE}" "${target_link}"
        echo -e "${GREEN}  ✓ 已链接到:${NC} ${target_link}"
        ((LINKED_COUNT++))
    fi
done

# 如果没有任何已识别的 agent 目录，默认至少创建 Claude Code 与通用 skills 目录
if [[ $LINKED_COUNT -eq 0 ]]; then
    default_dir="${HOME}/.claude/skills"
    mkdir -p "$default_dir"
    ln -sfn "${TARGET_SOURCE}" "${default_dir}/disk-raccoon"
    echo -e "${YELLOW}  ℹ 未检测到运行中的 Agent 配置目录，已默认链接至: ${default_dir}/disk-raccoon${NC}"
fi

# 5. 快速测试探针
echo -e "\n${BLUE}⚡ 正在测试极速探针...${NC}"
"${TARGET_SOURCE}/scripts/fast-scan.py" --min-mb=500 >/dev/null && echo -e "${GREEN}✓ 探针运行正常！${NC}"

echo -e "\n${GREEN}🎉 安装完成！${NC}"
echo -e "现在可以在你的 AI Agent（Claude Code / Antigravity 等）中输入："
echo -e "  💬 ${YELLOW}\"帮我看看缓存\"${NC} 或 ${YELLOW}\"磁盘满了，能清点什么\"${NC}"
echo -e "\n${BLUE}💡 提示：后续如有更新，只需在 ${TARGET_SOURCE} 运行 git pull 即可全 Agent 同步升级。${NC}"
