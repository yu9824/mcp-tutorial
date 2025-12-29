import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

from langchain.agents import create_agent
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolCall,
    ToolMessage,
)
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def initialize_model() -> ChatOllama:
    """Ollamaモデルを初期化する"""
    return ChatOllama(
        model="Llama-3.1-Swallow-8B:latest",
        base_url="http://localhost:11434",  # 省略可
        temperature=0.7,
    )


def get_server_script_path() -> Path:
    """server.py の絶対パスを取得する"""
    script_dir = Path(__file__).parent.resolve()
    server_script = script_dir / "server.py"

    if not server_script.exists():
        print(f"エラー: {server_script} が見つかりません。")
        sys.exit(1)

    return server_script


def create_server_parameters(server_script: Path) -> StdioServerParameters:
    """MCPサーバーのパラメータを作成する"""
    return StdioServerParameters(
        command="python3",  # 実行するコマンド
        args=[str(server_script)],  # コマンドライン引数（スクリプトパス）
    )


async def load_tools_from_mcp(session: ClientSession) -> list[Any]:
    """MCPセッションからツールを読み込む"""
    print("MCPツールをロード中...")
    # MCPツールを取得し、LangChainツールに変換
    # この関数が内部で session.list_tools() を呼び出し、
    # 返された MCPTool オブジェクトを convert_mcp_tool_to_langchain_tool で変換
    tools = await load_mcp_tools(session)
    print(f"ロードされたツール: {[tool.name for tool in tools]}")
    return tools


def create_agent_with_tools(model: ChatOllama, tools: list[Any]) -> Any:
    """モデルとツールからエージェントを作成する"""
    print("エージェントを作成中...")
    return create_agent(
        model=model,
        tools=tools,
        system_prompt="あなたは役立つアシスタントです。利用可能なツールを使って質問に答えてください。",
    )


def extract_tool_calls(last_message: BaseMessage) -> list[ToolCall]:
    """メッセージからツール呼び出しを抽出する"""
    tool_calls: list[ToolCall] = []

    if not isinstance(last_message, AIMessage):
        return tool_calls

    # 1. AIMessageのtool_calls属性を確認
    if getattr(last_message, "tool_calls", list()):
        existing_tool_calls = last_message.tool_calls
        # 既存のtool_callsをToolCall形式に変換
        for tc in existing_tool_calls:
            if isinstance(tc, dict):
                # 辞書形式の場合はToolCallに変換
                args = tc.get("args") or tc.get("parameters", {})
                if not isinstance(args, dict):
                    args = {}
                tool_calls.append(
                    ToolCall(
                        name=tc.get("name", ""),
                        args=cast(dict[str, Any], args),
                        id=tc.get("id", ""),
                    )
                )
            else:
                # オブジェクト形式の場合
                tool_calls.append(
                    ToolCall(
                        name=getattr(tc, "name", ""),
                        args=getattr(
                            tc, "args", getattr(tc, "parameters", {})
                        ),
                        id=getattr(tc, "id", ""),
                    )
                )
    # 2. 応答内容からJSON形式のツール呼び出しを解析
    elif last_message.content:
        content = last_message.content
        # contentが文字列であることを確認
        if isinstance(content, str):
            # JSON形式のツール呼び出しを検索
            try:
                # ```json ブロックを探す
                json_blocks = re.findall(
                    r"```json\s*(\{[\s\S]*?\})\s*```", content
                )
                if json_blocks:
                    for block in json_blocks:
                        try:
                            tool_call_data = json.loads(block.strip())
                            if isinstance(tool_call_data, dict):
                                tool_calls.append(
                                    ToolCall(
                                        name=tool_call_data.get("name", ""),
                                        args=tool_call_data.get(
                                            "args",
                                            tool_call_data.get(
                                                "parameters", {}
                                            ),
                                        ),
                                        id=tool_call_data.get("id", ""),
                                    )
                                )
                            elif isinstance(tool_call_data, list):
                                for item in tool_call_data:
                                    if isinstance(item, dict):
                                        tool_calls.append(
                                            ToolCall(
                                                name=item.get("name", ""),
                                                args=item.get(
                                                    "args",
                                                    item.get("parameters", {}),
                                                ),
                                                id=item.get("id", ""),
                                            )
                                        )
                        except Exception:
                            pass
                # 直接JSONオブジェクトの場合
                elif (
                    content.strip().startswith("{")
                    and "name" in content
                    and ("parameters" in content or "args" in content)
                ):
                    tool_call_data = json.loads(content.strip())
                    if isinstance(tool_call_data, dict):
                        tool_calls.append(
                            ToolCall(
                                name=tool_call_data.get("name", ""),
                                args=tool_call_data.get(
                                    "args",
                                    tool_call_data.get("parameters", {}),
                                ),
                                id=tool_call_data.get("id", ""),
                            )
                        )
            except (json.JSONDecodeError, KeyError):
                pass

    return tool_calls


def parse_tool_call(
    tool_call: ToolCall, iteration: int, tool_index: int
) -> tuple[str, dict[str, Any], str]:
    """ツール呼び出しオブジェクトから情報を抽出する"""
    # ToolCallはTypedDictなので辞書として扱う
    tool_name = tool_call.get("name", "")
    tool_args = tool_call.get("args", {})
    tool_id: str = tool_call.get("id") or f"call_{iteration}_{tool_index}"

    return tool_name, tool_args, tool_id


async def execute_tool_call(
    session: ClientSession,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_id: str,
) -> ToolMessage:
    """MCPセッションを使用してツールを実行する"""
    try:
        # MCPセッションを使用してツールを実行
        tool_result = await session.call_tool(tool_name, arguments=tool_args)

        # 結果を取得
        if tool_result.content:
            first_content = tool_result.content[0]
            # TextContentかどうかを確認（text属性があるかチェック）
            if hasattr(first_content, "text"):
                result_text = first_content.text
            else:
                result_text = str(first_content)
        else:
            result_text = str(tool_result)

        print(f"  結果: {result_text[:200]}...")

        # ToolMessageを作成して返す
        return ToolMessage(
            content=result_text,
            tool_call_id=tool_id,
            name=tool_name,
        )

    except Exception as e:
        error_msg = (
            f"ツール '{tool_name}' の実行中にエラーが発生しました: {str(e)}"
        )
        print(f"  {error_msg}")
        return ToolMessage(
            content=error_msg,
            tool_call_id=tool_id,
            name=tool_name,
        )


async def run_agent_loop(
    agent: Any, session: ClientSession, question: str, max_iterations: int = 10
) -> None:
    """エージェントを実行し、ツール呼び出しを処理するループ"""
    messages: list[BaseMessage] = [HumanMessage(content=question)]
    iteration = 0

    while iteration < max_iterations:
        print(f"\n--- イテレーション {iteration + 1} ---")
        result = await agent.ainvoke({"messages": messages})

        if "messages" not in result:
            break

        # 最後のメッセージを取得
        last_message = result["messages"][-1]
        # result["messages"]がlist[BaseMessage]であることを保証
        messages = cast(list[BaseMessage], result["messages"])

        # メッセージを表示
        print(f"エージェントの応答: {last_message.content}...")

        # ツール呼び出しを検出
        tool_calls = extract_tool_calls(last_message)

        # ツール呼び出しがあるか確認
        if tool_calls:
            print(f"\nツール呼び出しを検出: {len(tool_calls)}個")

            # 各ツール呼び出しを実行
            for idx, tool_call in enumerate(tool_calls):
                tool_name, tool_args, tool_id = parse_tool_call(
                    tool_call, iteration, idx
                )

                print(f"  ツール: {tool_name}")
                print(f"  引数: {tool_args}")

                # ツールを実行
                tool_message = await execute_tool_call(
                    session, tool_name, tool_args, tool_id
                )
                messages.append(tool_message)

            # ツール呼び出しがあったので、次のイテレーションに進む
            iteration += 1
            continue
        else:
            # ツール呼び出しがないので、最終応答
            print("\n=== エージェントの最終応答 ===")
            if isinstance(last_message, AIMessage):
                print(last_message.content)
            else:
                print(last_message)
            break

    if iteration >= max_iterations:
        print(
            f"\n警告: 最大イテレーション数 ({max_iterations}) に達しました。"
        )


async def main() -> None:
    try:
        # モデルを初期化
        model = initialize_model()

        # server.py の絶対パスを取得
        server_script = get_server_script_path()

        # server.py スクリプトを実行するためのパラメータを設定
        server_params = create_server_parameters(server_script)

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

                # MCPツールをロード
                tools = await load_tools_from_mcp(session)

                # エージェントを作成
                agent = create_agent_with_tools(model, tools)

                # エージェントを実行
                print("エージェントを呼び出し中...")
                # CSVツールのテスト用の質問
                question = "sample.csvというファイルを読み込んで、そのデータの統計情報を表示してください。"

                await run_agent_loop(agent, session, question)

    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
