"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")

# グローバル変数で読み込んだデータを保持
_loaded_data: Optional[pd.DataFrame] = None


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


# CSV読み込みツール
@mcp.tool()
def read_csv(file_path: str) -> str:
    """CSVファイルを読み込んでデータをメモリに保持します。

    Args:
        file_path: 読み込むCSVファイルのパス

    Returns:
        読み込んだデータの基本情報（行数、列数、列名など）
    """
    global _loaded_data

    try:
        path = Path(file_path)
        if not path.exists():
            return f"エラー: ファイル '{file_path}' が見つかりません。"

        _loaded_data = pd.read_csv(file_path)

        info = f"CSVファイル '{file_path}' を読み込みました。\n"
        info += f"行数: {len(_loaded_data)}\n"
        info += f"列数: {len(_loaded_data.columns)}\n"
        info += f"列名: {', '.join(_loaded_data.columns.tolist())}\n"

        return info
    except Exception as e:
        return f"エラー: CSVファイルの読み込みに失敗しました: {str(e)}"


# データのdescribeツール
@mcp.tool()
def describe_data() -> str:
    """読み込んだデータの統計情報を表示します。

    Returns:
        データの統計情報（describe()の結果）
    """
    global _loaded_data

    if _loaded_data is None:
        return "エラー: データが読み込まれていません。先にread_csvツールでCSVファイルを読み込んでください。"

    try:
        # 数値列の統計情報を取得
        desc = _loaded_data.describe()

        result = "=== データの統計情報 ===\n\n"
        result += desc.to_string()
        result += "\n\n=== データ型 ===\n"
        result += _loaded_data.dtypes.to_string()
        result += "\n\n=== 欠損値 ===\n"
        result += _loaded_data.isnull().sum().to_string()

        return result
    except Exception as e:
        return f"エラー: 統計情報の取得に失敗しました: {str(e)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FastMCP demo server")
    parser.add_argument(
        "--transport",
        default="stdio",
        help="Transport to use for MCP (default: stdio)",
    )
    # keep host/port optional for transports that may need them
    parser.add_argument(
        "--host", default=None, help="Host to bind (if applicable)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Port to bind (if applicable)"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # configure basic logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info(
        "Starting MCP server (transport=%s, host=%s, port=%s)",
        args.transport,
        args.host,
        args.port,
    )

    # Call run with available args; only pass host/port if provided
    run_kwargs = {"transport": args.transport}
    if args.host is not None:
        run_kwargs["host"] = args.host
    if args.port is not None:
        run_kwargs["port"] = args.port

    mcp.run(**run_kwargs)
