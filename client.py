#!/usr/bin/env python3

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import PromptReference


async def main():
    # FastMCPサーバーを起動するコマンド（あなたの serve.sh がこれを呼んでいるならOK）
    params = StdioServerParameters(command="bash", args=["serve.sh"])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 利用可能なプロンプトを確認
            prompts = await session.list_prompts()
            print("Available prompts:")
            for prompt in prompts.prompts:
                print(f" - {prompt.name}")

            # greet_user プロンプトを実行
            print("\nRunning prompt: greet_user")
            result = await session.get_prompt(
                "greet_user",
                arguments=[
                    {"name": "name", "value": "Alice"},
                    {"name": "style", "value": "formal"},
                ],
            )

            # 結果を表示
            print("\nPrompt output:")
            for item in result.output:
                print(f" - {item.text}")


if __name__ == "__main__":
    asyncio.run(main())
