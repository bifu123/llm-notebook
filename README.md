# 📓 智能记事系统（MSSQL + Neo4j + LLM）

本项目是一个基于自然语言驱动的智能记事系统，支持两种模式：

- **🗃️ TextNotebook**：基于 MSSQL + 全文检索 + LLM  
- **🕸️ GraphNotebook**：基于 Neo4j 图数据库 + RDF 三元组抽取 + LLM

你可以使用自然语言添加记录、查询内容，系统自动使用大模型（如 DeepSeek）进行关键词提取、图谱构建、关系匹配与自然语言回答。

---

## 📁 项目结构

```
.
├── mssql_notebook.py       # 文本笔记系统（MSSQL）
├── graph_notebook.py       # 图谱笔记系统（Neo4j）
├── .env                    # 环境变量文件（API Key）
└── README.md               # 使用说明文档
```

---

## 🔧 环境依赖

- Python >= 3.8
- MSSQL Server 2017+（需开启全文检索）
- Neo4j 5.x
- Python 第三方库：

```bash
pip install pymssql python-dotenv langchain-openai neo4j
```

---

## 🔐 配置环境变量（.env）

创建 `.env` 文件：

```
# 用于 DeepSeek 模型
DEEPSEEK_API_KEY=sk-你的key

# 用于连接 Neo4j（GraphNotebook）
NEO4J_URL=bolt://192.168.68.14:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

---

## 🗃️ TextNotebook（MSSQL 记事系统）

### 1️⃣ 创建数据库和数据表

```sql
CREATE DATABASE notebook;
GO

USE notebook;

CREATE TABLE notes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    content NVARCHAR(MAX),
    created_at DATETIME
);
```

### 2️⃣ 启用 MSSQL 全文检索

```sql
-- 创建全文目录
CREATE FULLTEXT CATALOG ftCatalog AS DEFAULT;

-- 获取主键索引名称
EXEC sp_helpindex notes;

-- 使用实际索引名替换下面的 PK_name
CREATE FULLTEXT INDEX ON notes(content)
    KEY INDEX PK__notes__xxxx
    ON ftCatalog;
```

也可以执行
```bash
python setup_mssql.py
```
一键创建

### 3️⃣ 启动程序

```bash
python mssql_notebook.py
```

### 4️⃣ 使用说明

- 添加记事：
  ```
  🔧 输入 1 添加记事
  📝 请输入记事：今天张三完成了项目交付
  ```

- 查询问题：
  ```
  🔧 输入 2 查询问题
  ❓ 请输入问题：张三做了什么？
  💬 回答：张三完成了项目交付。
  ```

---

## 🕸️ GraphNotebook（Neo4j 图谱记事系统）

### 1️⃣ 启动 Neo4j

确保你的 Neo4j 服务运行并已启用 Bolt 协议，用户名和密码写入 `.env`。

推荐版本：Neo4j Community Edition 5.x

### 2️⃣ 图谱结构说明

每条记事会被解析为 RDF 三元组形式：

```
(主语)-[谓语 {date, amount}]->(宾语)
```

并写入图数据库中，支持谓词动态获取，自动 Cypher 构造和结果总结。

### 3️⃣ 启动程序

```bash
python graph_notebook.py
```

### 4️⃣ 使用示例

- 添加记事：
  ```
  🔧 输入 1 添加记事
  📝 请输入记事：昨天我买了一头猪250元
  ✅ 已保存: [('我', '购买', '一头猪', '2025-07-01 08:00:00', 250)]
  ```

- 查询问题：
  ```
  🔧 输入 2 查询问题
  ❓ 请输入问题：我都买了什么？
  💬 回答：你购买了一头猪。
  ```

---

## 🧠 技术亮点

- ✅ LangChain + DeepSeek 接入高性能中文 LLM
- ✅ Neo4j 图数据库支持 RDF 三元组动态建图
- ✅ MSSQL 全文检索结合 LLM 实现智能匹配
- ✅ 自动关键词提取、关系识别、结果生成

---

## 📌 注意事项

- Neo4j 和 MSSQL 不冲突，可独立部署
- `.env` 中同时配置 DeepSeek 和 Neo4j 信息、mssql 信息
- MSSQL 的全文检索配置依赖系统组件，如未启用，请在“添加/删除功能”中启用“全文搜索”

---

## 📦 未来方向

- [ ] 图谱和文本记事统一查询接口
- [ ] 添加图形界面（如 Streamlit 或 Web 版）
- [ ] 引入语音识别、图像 OCR 处理
- [ ] 多用户多身份支持
- [ ] 作为 LMCP (用 langchain agent 改造的 MCP 模型上下文协议) 工具

---

## 🧑‍💻 作者
QQ: 415135222
如需系统部署、模型定制、企业集成，请联系作者。


