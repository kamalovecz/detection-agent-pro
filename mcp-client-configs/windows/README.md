# Windows MCP 配置样板

这个目录里放的是已经按当前机器路径生成好的 MCP 客户端配置样板。

## 文件说明

- `claude_desktop_config.example.json`
  - 适合 Claude Desktop
  - 通常粘贴到 `%APPDATA%\Claude\claude_desktop_config.json`

- `cursor_mcp.example.json`
  - 适合 Cursor
  - 常见位置：
    - `%USERPROFILE%\.cursor\mcp.json`
    - 或 `%APPDATA%\Cursor\User\mcp.json`

## 当前已适配的服务

- `zotero`
- `word-document-server`

## 注意

- `zotero` 当前使用本地模式：`ZOTERO_LOCAL=true`
- `Office Word MCP` 当前使用 `stdio`
- 如果你要让 Zotero MCP 使用语义检索，还需要额外安装 `semantic` 依赖
- 修改正式客户端配置前，建议先备份原配置文件
