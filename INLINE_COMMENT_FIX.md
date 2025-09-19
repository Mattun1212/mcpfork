# インラインコメント機能修正記録

## 修正概要
Confluence 7.19.17のインラインコメント機能を標準API仕様に合わせて修正しました。

## 問題
- 独自パラメータ `inline_marker_ref` と `inline_original_selection` を使用していた
- Confluence標準APIでは異なるパラメータ名とリクエスト構造が必要

## 修正内容

### 1. パラメータ変更
**修正前:**
```python
def add_inline_comment(
    page_id: str,
    content: str,
    inline_marker_ref: str,
    inline_original_selection: str
)
```

**修正後:**
```python
def add_inline_comment(
    page_id: str,
    content: str,
    text_selection: str,
    text_selection_match_count: int = 1,
    text_selection_match_index: int = 0
)
```

### 2. APIリクエスト構造変更
**修正前:**
```json
"inlineCommentProperties": {
    "inlineMarkerRef": inline_marker_ref,
    "inlineOriginalSelection": inline_original_selection
}
```

**修正後:**
```json
"inlineCommentProperties": {
    "textSelection": text_selection,
    "textSelectionMatchCount": text_selection_match_count,
    "textSelectionMatchIndex": text_selection_match_index
}
```

### 3. 修正したファイル
- `/Users/koutaro.matsushita/Desktop/mcp/mcp-atlassian/src/mcp_atlassian/confluence/comments.py` (L253-364)
- `/Users/koutaro.matsushita/Desktop/mcp/mcp-atlassian/src/mcp_atlassian/servers/confluence.py` (L708-752)
- `/Users/koutaro.matsushita/Desktop/mcp/mcp-atlassian/tests/unit/confluence/test_inline_comments.py` (複数箇所)

### 4. Claude Desktop Config更新
`/Users/koutaro.matsushita/Library/Application Support/Claude/claude_desktop_config.json` に以下を追加:
```json
"r-atlassian": {
  "command": "mcp-atlassian",
  "args": [
    "start",
    "confluence"
  ]
}
```

## テスト手順
Claude Code再起動後、以下でテスト:

```
mcp__r-atlassian__confluence_add_inline_comment
- page_id: 5901930339
- content: テスト
- text_selection: Summary
```

## 期待される動作
ECFDPM-231のConfluenceページの「Summary」見出しに「テスト」というインラインコメントが正常に追加される。

## エラー履歴
- 修正前: `Unable to add inline comment to page 5901930339. API request completed but inline comment creation unsuccessful.`
- 原因: 独自パラメータが標準Confluence APIで認識されない

## 参考情報
- Confluence バージョン: 7.19.17 (node001: 36bc0fdd)
- 標準APIでは `textSelection`, `textSelectionMatchCount`, `textSelectionMatchIndex` パラメータを使用
- インラインコメント機能はConfluence 5.7以降で利用可能