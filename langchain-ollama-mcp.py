import asyncio
import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    try:
        # モデルを初期化
        model = ChatOllama(
            model="Llama-3.1-Swallow-8B:latest",
            base_url="http://localhost:11434",  # 省略可
            temperature=0.7,
        )

        # server.py の絶対パスを取得
        script_dir = Path(__file__).parent.resolve()
        server_script = script_dir / "server.py"

        if not server_script.exists():
            print(f"エラー: {server_script} が見つかりません。")
            sys.exit(1)

        # server.py スクリプトを実行するためのパラメータを設定
        server_params = StdioServerParameters(
            command="python3",  # 実行するコマンド
            args=[str(server_script)],  # コマンドライン引数（スクリプトパス）
        )

        print("MCPサーバーに接続中...")
        # stdio_client コンテキストマネージャを使用して接続を確立
        async with stdio_client(server_params) as (read, write):
            # read/writeストリームを使用してClientSessionを作成
            # session_kwargs で ClientSession の挙動をカスタマイズ可能
            async with ClientSession(read, write) as session:
                print("セッションを初期化中...")
                # サーバーとのハンドシェイクを実行
                await session.initialize()
                print("セッションが初期化されました。")

                print("MCPツールをロード中...")
                # MCPツールを取得し、LangChainツールに変換
                # この関数が内部で session.list_tools() を呼び出し、
                # 返された MCPTool オブジェクトを convert_mcp_tool_to_langchain_tool で変換
                tools = await load_mcp_tools(session)
                print(f"ロードされたツール: {[tool.name for tool in tools]}")

                # create_agentでエージェントを作成
                print("エージェントを作成中...")
                agent = create_agent(
                    model=model,
                    tools=tools,
                    system_prompt="あなたは役立つアシスタントです。利用可能なツールを使って質問に答えてください。",
                )

                # エージェントを実行
                print("エージェントを呼び出し中...")
                question = "3 + 5 は？"
                result = await agent.ainvoke(
                    {"messages": [HumanMessage(content=question)]}
                )

                print("\n=== エージェントの応答 ===")
                # エージェントの戻り値は {"messages": [...]} の形式
                # 最後のメッセージがエージェントの応答
                if "messages" in result and result["messages"]:
                    print(result["messages"][-1].content)
                else:
                    print(result)

    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
