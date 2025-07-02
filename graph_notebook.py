import os
import re
from datetime import datetime
from typing import List, Tuple
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("BASE_URL"),
    model=os.getenv("MODEL"),
    temperature=0
)

class GraphNotebook:
    def __init__(self, llm: ChatOpenAI, neo4j_driver: GraphDatabase.driver):
        self.llm = llm
        self.driver = neo4j_driver

    def get_current_datetime_str(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.now().strftime(format)

    def store_entry(self, entry_text: str):
        prompt = f"""
请将下列中文记事文本解析为结构化 RDF 三元组 (主语, 谓语, 宾语, 时间)，
并尽可能提取数字金额（元）及数字数量，输出为 Python 列表格式，格式如下：
[('我', '花费', '钱', '2025-07-02 08:00:00', 200, None), ('张三', '办了', '事', '2025-07-02 08:00:00', None, 3)]

说明：金额字段为 float 或 None，数量字段为 int 或 None

要求：
- 时间格式为 YYYY-MM-DD HH:MM:SS，如果无时间请用当前时间 {self.get_current_datetime_str()}
- 如果无金额或无数量，请分别填 None
- 只输出列表，不要注释或换行

文本：
“{entry_text}”
"""
        response = self.llm.invoke(prompt)
        try:
            # 解析格式：(subj, pred, obj, date, amount, count)
            triples: List[Tuple[str, str, str, str, float, int]] = eval(response.content.strip())
        except Exception as e:
            print("❌ 三元组解析失败:", e)
            return

        with self.driver.session() as session:
            for subj, pred, obj, date, amount, count in triples:
                cypher = f"""
MERGE (s:Entity {{name: $subj}})
MERGE (o:Entity {{name: $obj}})
MERGE (s)-[r:{pred}]->(o)
"""
                props = {}
                if date:
                    props['date'] = date
                if amount is not None:
                    props['amount'] = amount
                if count is not None:
                    props['count'] = count

                if props:
                    set_clause = ", ".join([f"r.{k} = ${k}" for k in props.keys()])
                    cypher += f" SET {set_clause}"
                    session.run(cypher, subj=subj, obj=obj, **props)
                else:
                    session.run(cypher, subj=subj, obj=obj)
        print("✅ 已保存:", triples)

    def get_all_predicates(self) -> List[str]:
        with self.driver.session() as session:
            result = session.run("CALL db.relationshipTypes()")
            predicates = [record["relationshipType"] for record in result]
        print("ℹ️ 当前图谱谓词:", predicates)
        return predicates

    def query_entry(self, question_text: str) -> str:
        predicates = self.get_all_predicates()
        predicates_str = ", ".join(predicates) if predicates else "无谓词"

        predicate_prompt = f"""
数据库中现有的关系谓词有：{predicates_str}。
请根据用户的自然语言问题，从这些谓词中选择最合适的一个或多个，并构造一条完整的 Neo4j Cypher 查询语句，查询以“我”为主体的相关信息。

要求：
- 必须以 MATCH 开头，以 RETURN 结尾
- 必须包含 (主体:Entity {{name: '我'}}) 模式
- 使用关系变量 `r` 来引用关系，金额字段是 `r.amount`，数量字段是 `r.count`
- 不要输出任何注释或多余内容，只输出纯 Cypher 查询语句

用户问题：
{question_text}
"""
        cypher_raw = self.llm.invoke(predicate_prompt).content.strip()
        cypher_matches = re.findall(r"(MATCH .*?RETURN .*?)(?:$|\n)", cypher_raw, re.DOTALL | re.IGNORECASE)
        cypher = cypher_matches[0].strip() if cypher_matches else cypher_raw
        print("📌 生成的 Cypher 查询：\n", cypher)

        # 自动修正 SUM() 用法：金额和数量字段
        if "SUM" in cypher.upper():
            if not re.search(r"SUM\(r\.amount\)", cypher, re.IGNORECASE) and "r.amount" in cypher:
                print("⚠️ 自动修正：SUM 函数应使用关系属性 r.amount")
                cypher = re.sub(r"SUM\([^)]+\)", "SUM(r.amount)", cypher, flags=re.IGNORECASE)
            if not re.search(r"SUM\(r\.count\)", cypher, re.IGNORECASE) and "r.count" in cypher:
                print("⚠️ 自动修正：SUM 函数应使用关系属性 r.count")
                cypher = re.sub(r"SUM\([^)]+\)", "SUM(r.count)", cypher, flags=re.IGNORECASE)

        # 自动修正 count(r) -> SUM(r.count)
        if re.search(r"count\(r\)", cypher, re.IGNORECASE) and "r.count" not in cypher:
            print("⚠️ 自动修正：使用 SUM(r.count) 代替 count(r)")
            cypher = re.sub(r"count\(r\)", "SUM(r.count)", cypher, flags=re.IGNORECASE)

        try:
            with self.driver.session() as session:
                result = session.run(cypher)
                data = [dict(r) for r in result]

                if len(data) == 0:
                    print("⚠️ 查询结果为空，尝试返回所有以‘我’为主体的关系记录")
                    fallback_cypher = """
MATCH (s:Entity {name:'我'})-[r]->(o:Entity)
RETURN s.name AS subject, type(r) AS predicate, o.name AS object, r.date AS date, r.amount AS amount, r.count AS count
ORDER BY r.date DESC
LIMIT 50
"""
                    fallback_result = session.run(fallback_cypher)
                    data = [dict(r) for r in fallback_result]

        except Exception as e:
            print("❌ 查询执行失败:", e)
            return "查询失败，请检查 Cypher 语句或图谱结构。"

        summary_prompt = f"""
请根据以下查询结果，用简洁中文回答用户问题：
用户问题：{question_text}
查询结果：{data}
"""
        answer = self.llm.invoke(summary_prompt).content.strip()
        return answer


if __name__ == "__main__":
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URL"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    notebook = GraphNotebook(llm=llm, neo4j_driver=driver)

    
    while True:
        print("🔧 输入 1 添加记事，输入 2 查询问题，输入 q 退出：")
        cmd = input().strip()
        if cmd == '1':
            note = input("📝 请输入记事：")
            notebook.store_entry(note)
        elif cmd == '2':
            question = input("❓ 请输入问题：")
            answer = notebook.query_entry(question)
            print("💬 回答：", answer)
        elif cmd.lower() == 'q':
            print("退出程序。")
            break
        else:
            print("无效输入，请输入 1、2 或 q。")
