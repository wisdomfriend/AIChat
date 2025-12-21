# LangChain 升级指南

## 当前版本
- langchain==0.3.27
- langchain-core==0.3.80
- langchain-community==0.3.27
- langchain-text-splitters==0.3.11

## 升级步骤

### 1. 备份当前环境
```bash
# 备份当前的 requirements.txt
cp requirements.txt requirements.txt.backup

# 导出当前环境（可选）
pip freeze > current_env.txt
```

### 2. 检查最新版本
```bash
# 检查最新可用版本
pip index versions langchain
pip index versions langchain-core
pip index versions langchain-community
pip index versions langchain-text-splitters
```

### 3. 升级 LangChain 包
```bash
# 方式1：升级到最新版本（推荐先测试）
pip install --upgrade langchain langchain-core langchain-community langchain-text-splitters

# 方式2：升级到指定版本（更安全）
pip install --upgrade langchain>=0.3.27 langchain-core>=0.3.80 langchain-community>=0.3.27 langchain-text-splitters>=0.3.11

# 方式3：只升级补丁版本（最安全）
pip install --upgrade langchain==0.3.* langchain-core==0.3.* langchain-community==0.3.* langchain-text-splitters==0.3.*
```

### 4. 更新 requirements.txt
```bash
# 生成新的 requirements.txt
pip freeze | grep langchain > langchain_versions.txt

# 或者手动更新 requirements.txt 中的版本号
```

### 5. 测试关键功能
升级后需要测试以下功能：

#### 5.1 Memory 功能
- [ ] 测试对话历史保存和加载
- [ ] 测试窗口限制功能
- [ ] 测试 Token 缓冲功能
- [ ] 测试摘要功能

#### 5.2 LLM 调用
- [ ] 测试流式响应
- [ ] 测试不同模型提供商
- [ ] 测试 Token 计数

#### 5.3 Agent 功能（如果启用）
- [ ] 测试 Agent 创建
- [ ] 测试工具调用
- [ ] 测试流式 Agent 响应

### 6. 检查破坏性变更

#### 可能需要注意的变更：

1. **导入路径变更**
   - 检查 `from langchain.xxx` 是否仍然有效
   - 某些模块可能移动到 `langchain_core` 或 `langchain_community`

2. **API 变更**
   - `ChatOpenAI` 的参数可能有变化
   - Memory 类的初始化参数可能有变化
   - Agent 相关的 API 可能有变化

3. **依赖版本要求**
   - 检查 `openai` 版本是否兼容
   - 检查 `tiktoken` 版本是否兼容

### 7. 回滚方案（如果出现问题）

```bash
# 回滚到之前的版本
pip install langchain==0.3.27 langchain-core==0.3.80 langchain-community==0.3.27 langchain-text-splitters==0.3.11

# 或者从备份恢复
cp requirements.txt.backup requirements.txt
pip install -r requirements.txt
```

## 代码中使用的 LangChain API

### 需要特别注意的导入：

1. **Memory 相关**
   ```python
   from langchain.memory import (
       ConversationBufferWindowMemory,
       ConversationTokenBufferMemory,
       ConversationSummaryMemory
   )
   ```

2. **Agent 相关**
   ```python
   from langchain.agents import AgentExecutor, create_react_agent
   from langchain.tools import BaseTool
   ```

3. **Core 相关**
   ```python
   from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
   from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
   from langchain_core.tools import tool
   ```

4. **Community 相关**
   ```python
   from langchain_community.chat_models import ChatOpenAI
   ```

## 升级后验证清单

- [ ] 应用可以正常启动
- [ ] 聊天功能正常
- [ ] 文件上传功能正常
- [ ] 会话历史功能正常
- [ ] Token 计数功能正常
- [ ] 流式响应正常
- [ ] 没有警告或错误日志

## 参考资源

- [LangChain 官方文档](https://python.langchain.com/)
- [LangChain GitHub Releases](https://github.com/langchain-ai/langchain/releases)
- [LangChain 迁移指南](https://python.langchain.com/docs/versions/)

