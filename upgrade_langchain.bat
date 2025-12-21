@echo off
REM LangChain 升级脚本 (0.3.x → 1.2.0) - Windows 版本
REM 使用清华大学镜像源加速

echo ==========================================
echo LangChain 升级脚本 (0.3.x → 1.2.0)
echo ==========================================
echo.

REM 设置镜像源
set MIRROR_URL=https://pypi.tuna.tsinghua.edu.cn/simple

REM 检查当前版本
echo [1/6] 检查当前 LangChain 版本...
pip show langchain langchain-core langchain-community langchain-text-splitters | findstr Version
echo.

REM 备份 requirements.txt
echo [2/6] 备份 requirements.txt...
if exist requirements.txt (
    copy requirements.txt requirements.txt.backup.%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    echo ✓ requirements.txt 已备份
) else (
    echo ✗ requirements.txt 不存在
    exit /b 1
)
echo.

REM 确认升级
echo [3/6] 准备升级到 LangChain 1.2.0
set /p confirm="是否继续？(y/n): "
if /i not "%confirm%"=="y" (
    echo 升级已取消
    exit /b 1
)
echo.

REM 升级包
echo [4/6] 开始升级 LangChain 包（使用清华镜像源）...
pip install -i %MIRROR_URL% --upgrade langchain==1.2.0 langchain-core langchain-community langchain-text-splitters

if %errorlevel% equ 0 (
    echo ✓ LangChain 升级成功
) else (
    echo ✗ LangChain 升级失败
    exit /b 1
)
echo.

REM 显示新版本
echo [5/6] 检查升级后的版本...
pip show langchain langchain-core langchain-community langchain-text-splitters | findstr Version
echo.

REM 更新 requirements.txt
echo [6/6] 更新 requirements.txt...
pip freeze | findstr /i "langchain" > langchain_new_versions.txt
echo ✓ 新版本信息已保存到 langchain_new_versions.txt
echo 请手动更新 requirements.txt 中的版本号
echo.

REM 测试导入
echo [7/7] 测试关键模块导入...
python -c "from langchain.memory import ConversationSummaryMemory; print('✓ langchain.memory 导入成功')" 2>nul || echo ✗ langchain.memory 导入失败
python -c "from langchain_core.prompts import ChatPromptTemplate; print('✓ langchain_core.prompts 导入成功')" 2>nul || echo ✗ langchain_core.prompts 导入失败
python -c "from langchain_community.chat_models import ChatOpenAI; print('✓ langchain_community.chat_models 导入成功')" 2>nul || echo ✗ langchain_community.chat_models 导入失败
python -c "from langchain_core.messages import HumanMessage, AIMessage; print('✓ langchain_core.messages 导入成功')" 2>nul || echo ✗ langchain_core.messages 导入失败
echo.

echo ==========================================
echo 升级完成！
echo ==========================================
echo.
echo 下一步：
echo 1. 检查 langchain_new_versions.txt 中的版本号
echo 2. 更新 requirements.txt
echo 3. 运行测试确保功能正常
echo 4. 如有问题，使用备份恢复：copy requirements.txt.backup.* requirements.txt
pause

