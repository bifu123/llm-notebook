import os
import pymssql
from datetime import datetime
from typing import List, Tuple  # ✅ 修正：导入 Tuple
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# --- 读取 .env ---
load_dotenv()

# --- 初始化 LLM 模型 ---
llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("BASE_URL"),
    model=os.getenv("MODEL"),
    temperature=0
)

# --- MSSQL 配置 ---
mssql_config = {
    'server': os.getenv("MSSQL_SERVER"),
    'database': os.getenv("MSSQL_DATABASE"),
    'user': os.getenv("MSSQL_USER"),
    'password': os.getenv("MSSQL_PASSWORD"),
    'charset': 'utf8'
}


class TextNotebook:
    def __init__(self, llm: ChatOpenAI, db_config: dict):
        self.llm = llm
        self.db_config = db_config
        self._ensure_table()

    def _connect(self):
        return pymssql.connect(**self.db_config)

    def _ensure_table(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='notes' AND xtype='U'
            )
            CREATE TABLE notes (
                id INT IDENTITY(1,1) PRIMARY KEY,
                content NVARCHAR(MAX),
                created_at DATETIME
            )
            """)
            conn.commit()

    def store_note(self, note: str):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (content, created_at) VALUES (%s, %s)",
                (note, datetime.now())
            )
            conn.commit()
        print(f"✅ 已保存记事：{note}")

    def _get_structured_summary(self, notes: List[Tuple[str, datetime]], question: str) -> str:
        context = "\n".join([f"{i+1}. {n[0]}（时间：{n[1]}）" for i, n in enumerate(notes)])
        prompt = f"""
以下是一个用户的记事列表，请根据这些内容回答用户的问题：

问题：{question}
记事：
{context}

请用简洁自然语言回答问题。
"""
        return self.llm.invoke(prompt).content.strip()

    def search_notes(self, query: str) -> List[Tuple[str, datetime]]:
        with self._connect() as conn:
            cursor = conn.cursor(as_dict=True)
            sql = """
            SELECT TOP 10 content, created_at
            FROM notes
            WHERE CONTAINS(content, %s)
            ORDER BY created_at DESC
            """
            cursor.execute(sql, [query])
            return [(row['content'], row['created_at']) for row in cursor.fetchall()]

    def query_notes(self, question: str) -> str:
        # 尝试 LLM 分析 + 全文搜索关键词提取
        keyword_prompt = f"""
用户的问题是：“{question}”
请从中提取适合用于数据库全文搜索的关键词，输出格式如下：
关键词：关键词1 关键词2 ...

注意：只输出“关键词：...”这一行。
"""
        keyword_line = self.llm.invoke(keyword_prompt).content.strip()
        print("🔍 LLM关键词提取：", keyword_line)

        keywords = []
        if "关键词：" in keyword_line:
            keywords = keyword_line.split("关键词：")[-1].strip().split()

        if not keywords:
            return "❌ 无法提取有效关键词，无法搜索。"

        # 构造全文搜索语句（用 OR 连接）
        search_expr = " OR ".join(keywords)
        print("🔍 构造全文检索语句：", search_expr)
        notes = self.search_notes(search_expr)

        if not notes:
            return "❌ 未找到相关记事。"

        return self._get_structured_summary(notes, question)


if __name__ == "__main__":
    notebook = TextNotebook(llm=lm, db_config=mssql_config)

    while True:
        mode = input("🔧 输入 1 添加记事，输入 2 查询问题，输入 q 退出：")
        if mode == "1":
            note = input("📝 请输入记事：")
            notebook.store_note(note)
        elif mode == "2":
            question = input("❓ 请输入问题：")
            response = notebook.query_notes(question)
            print("💬 回答：", response)
        elif mode.lower() == "q":
            break
