#!/usr/bin/env python3

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    try:
        # server.pyを直接実行するように修正
        params = StdioServerParameters(
            command="python3", args=["server.py", "--transport", "stdio"]
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ MCPサーバーとの接続が確立されました")

                # 1. 利用可能なツールを確認
                print("\n🔧 利用可能なツール:")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f" - {tool.name}: {tool.description}")

                # 2. ツールの実行テスト（add関数）
                print("\n🧮 ツール実行テスト:")
                print("add(5, 3) を実行中...")
                add_result = await session.call_tool(
                    "add", arguments={"a": 5, "b": 3}
                )
                print(f"結果: {add_result.content[0].text}")

                # 3. 利用可能なリソースを確認
                print("\n📚 利用可能なリソース:")
                resources = await session.list_resources()
                for resource in resources.resources:
                    print(f" - {resource.uri}: {resource.name}")

                # 4. リソースの読み取りテスト
                print("\n📖 リソース読み取りテスト:")
                print("greeting://Alice を読み取り中...")
                greeting_result = await session.read_resource(
                    "greeting://Alice"
                )
                print(f"結果: {greeting_result.contents[0].text}")

                # 5. 利用可能なプロンプトを確認
                print("\n💬 利用可能なプロンプト:")
                prompts = await session.list_prompts()
                for prompt in prompts.prompts:
                    print(f" - {prompt.name}: {prompt.description}")

                # 6. プロンプトの実行テスト
                print("\n🎯 プロンプト実行テスト:")
                print("greet_user プロンプトを実行中...")
                try:
                    prompt_result = await session.get_prompt(
                        "greet_user",
                        arguments={"name": "Alice", "style": "formal"},
                    )
                    print("プロンプト出力:")
                    # GetPromptResultの構造を確認して適切な属性を使用
                    print(f"プロンプト結果: {prompt_result}")
                    if hasattr(prompt_result, "messages"):
                        for message in prompt_result.messages:
                            print(f" - {message.content}")
                    elif hasattr(prompt_result, "content"):
                        print(f" - {prompt_result.content}")
                    else:
                        print(f"利用可能な属性: {dir(prompt_result)}")
                except Exception as prompt_error:
                    print(f"❌ プロンプト実行エラー: {prompt_error}")
                    print(f"エラータイプ: {type(prompt_error)}")
                    import traceback

                    print("詳細なエラー情報:")
                    traceback.print_exc()

                print("\n✅ 全てのテストが正常に完了しました！")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print(f"エラータイプ: {type(e)}")
        import traceback

        print("詳細なエラー情報:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
