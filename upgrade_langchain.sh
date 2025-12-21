#!/bin/bash
# LangChain 升级脚本 (0.3.x → 1.2.0)

echo "=========================================="
echo "LangChain 升级脚本 (0.3.x → 1.2.0)"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查当前版本
echo -e "${YELLOW}1. 检查当前 LangChain 版本...${NC}"
pip show langchain langchain-core langchain-community langchain-text-splitters | grep Version
echo ""

# 备份 requirements.txt
echo -e "${YELLOW}2. 备份 requirements.txt...${NC}"
if [ -f requirements.txt ]; then
    cp requirements.txt requirements.txt.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ requirements.txt 已备份${NC}"
else
    echo -e "${RED}✗ requirements.txt 不存在${NC}"
    exit 1
fi
echo ""

# 确认升级
echo -e "${YELLOW}3. 准备升级到 LangChain 1.2.0${NC}"
read -p "是否继续？(y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}升级已取消${NC}"
    exit 1
fi

# 升级包
echo -e "${YELLOW}4. 开始升级 LangChain 包...${NC}"
pip install --upgrade langchain==1.2.0 langchain-core langchain-community langchain-text-splitters

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ LangChain 升级成功${NC}"
else
    echo -e "${RED}✗ LangChain 升级失败${NC}"
    exit 1
fi
echo ""

# 显示新版本
echo -e "${YELLOW}5. 检查升级后的版本...${NC}"
pip show langchain langchain-core langchain-community langchain-text-splitters | grep Version
echo ""

# 更新 requirements.txt
echo -e "${YELLOW}6. 更新 requirements.txt...${NC}"
pip freeze | grep -E "langchain|langchain-core|langchain-community|langchain-text-splitters" > langchain_new_versions.txt
echo -e "${GREEN}✓ 新版本信息已保存到 langchain_new_versions.txt${NC}"
echo "请手动更新 requirements.txt 中的版本号"
echo ""

# 测试导入
echo -e "${YELLOW}7. 测试关键模块导入...${NC}"
python3 << EOF
try:
    from langchain.memory import ConversationBufferWindowMemory
    print("✓ langchain.memory 导入成功")
except Exception as e:
    print(f"✗ langchain.memory 导入失败: {e}")

try:
    from langchain.agents import AgentExecutor, create_react_agent
    print("✓ langchain.agents 导入成功")
except Exception as e:
    print(f"✗ langchain.agents 导入失败: {e}")

try:
    from langchain_core.prompts import ChatPromptTemplate
    print("✓ langchain_core.prompts 导入成功")
except Exception as e:
    print(f"✗ langchain_core.prompts 导入失败: {e}")

try:
    from langchain_community.chat_models import ChatOpenAI
    print("✓ langchain_community.chat_models 导入成功")
except Exception as e:
    print(f"✗ langchain_community.chat_models 导入失败: {e}")

try:
    from langchain_core.tools import tool
    print("✓ langchain_core.tools 导入成功")
except Exception as e:
    print(f"✗ langchain_core.tools 导入失败: {e}")
EOF

echo ""
echo -e "${GREEN}=========================================="
echo "升级完成！"
echo "==========================================${NC}"
echo ""
echo "下一步："
echo "1. 检查 langchain_new_versions.txt 中的版本号"
echo "2. 更新 requirements.txt"
echo "3. 运行测试确保功能正常"
echo "4. 如有问题，使用备份恢复：cp requirements.txt.backup.* requirements.txt"

