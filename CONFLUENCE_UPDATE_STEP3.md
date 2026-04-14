# ステップ3: MCP Atlassian統合のインストール

## 概要

このステップでは、**自動インストーラー**を使用してMCP Atlassian統合をセットアップします。インストーラーが以下を自動で行います：

- ✅ Python 3.12の自動インストール（必要な場合）
- ✅ 仮想環境の作成
- ✅ MCP Atlassianのインストール
- ✅ Claude Code設定ファイルの更新

**所要時間**: 5〜10分

---

## 3-1. インストールスクリプトのダウンロード

### Boxからダウンロード

**Box共有リンク**: [インストールスクリプト](https://rak.box.com/s/あなたのBoxリンク)

**ダウンロードするファイル:**
- **Mac/Linux用**: `install-mcp-atlassian.sh`
- **Windows用**: `install-mcp-atlassian.ps1`

**注意**: どちらか一つだけダウンロードしてください（お使いのOSに合わせて）

---

## 3-2. インストールの実行

### Mac/Linux の場合

1. **ターミナルを起動**
   - アプリケーション → ユーティリティ → ターミナル

2. **ダウンロードフォルダに移動**
   ```bash
   cd ~/Downloads
   ```

3. **実行権限を付与して実行**
   ```bash
   chmod +x install-mcp-atlassian.sh
   ./install-mcp-atlassian.sh
   ```

### Windows の場合

1. **PowerShellを管理者として起動**
   - スタートメニューで「PowerShell」を検索
   - 右クリック → 「管理者として実行」

2. **ダウンロードフォルダに移動**
   ```powershell
   cd $HOME\Downloads
   ```

3. **実行ポリシーを変更して実行**
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\install-mcp-atlassian.ps1
   ```

---

## 3-3. インストーラーの指示に従う

インストーラーが起動すると、以下の情報を順番に入力するよう求められます：

### 入力が必要な情報

1. **Rakutenメールアドレス**
   ```
   例: taro.yamada@rakuten.com
   ```

2. **JIRA Personal Access Token**
   - ステップ2-1で取得したトークンを貼り付け
   - **注意**: 入力中は画面に表示されません（セキュリティ保護）

3. **Confluence Personal Access Token**
   - ステップ2-2で取得したトークンを貼り付け
   - **注意**: 入力中は画面に表示されません（セキュリティ保護）

### インストーラーの実行例

```
======================================
MCP Atlassian Auto Installer
======================================

[✓] Python 3.12 found
[✓] Directory created: /Users/taro/.mcp/mcp-atlassian
[!] Creating Python virtual environment...
[✓] Virtual environment created
[!] Upgrading pip...
[✓] pip upgraded
[!] Installing MCP Atlassian (this may take a few minutes)...
[✓] MCP Atlassian installed
[✓] Installation successful!

======================================
Configuration Setup
======================================

Enter your Rakuten email address: taro.yamada@rakuten.com

Please generate your API tokens:
  JIRA: https://jira.rakuten-it.com/jira → Profile → Personal Access Tokens
  Confluence: https://confluence.rakuten-it.com/confluence → Settings → Personal Access Tokens

Enter your JIRA Personal Access Token: [入力は表示されません]
Enter your Confluence Personal Access Token: [入力は表示されません]

[!] Updating .claude.json...
[✓] .claude.json updated

======================================
Installation Complete!
======================================

Next steps:
  1. Restart Claude Code
  2. Run: /mcp
  3. Verify 'mcp-atlassian-mutton' is connected

Installation location: /Users/taro/.mcp/mcp-atlassian
```

---

## 3-4. インストール完了の確認

インストールが完了すると、以下のメッセージが表示されます：

```
======================================
Installation Complete!
======================================

Next steps:
  1. Restart Claude Code
  2. Run: /mcp
  3. Verify 'mcp-atlassian-mutton' is connected
```

### インストール場所

- **Mac/Linux**: `~/.mcp/mcp-atlassian/`
- **Windows**: `C:\Users\<ユーザー名>\.mcp\mcp-atlassian\`

---

## トラブルシューティング

### Pythonのインストールに失敗する

**症状**: 「Python installation failed」というエラー

**Mac の解決方法:**
```bash
# Homebrewを手動でインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Pythonをインストール
brew install python@3.12

# スクリプトを再実行
./install-mcp-atlassian.sh
```

**Windows の解決方法:**
1. https://www.python.org/downloads/ にアクセス
2. Python 3.12以上をダウンロード
3. インストーラーを実行時に **「Add Python to PATH」にチェック**
4. PowerShellを再起動してスクリプトを再実行

### .claude.jsonが見つからない

**症状**: 「.claude.json not found」というエラー

**解決方法:**
1. Claude Codeを一度起動して終了する
2. スクリプトを再実行

### 実行権限エラー（Mac）

**症状**: 「Permission denied」エラー

**解決方法:**
```bash
chmod +x install-mcp-atlassian.sh
./install-mcp-atlassian.sh
```

### PowerShell実行ポリシーエラー（Windows）

**症状**: 「実行ポリシーによりスクリプトを実行できません」

**解決方法:**
PowerShellを**管理者として**再起動して、以下を実行：
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install-mcp-atlassian.ps1
```

### インストールは成功したが接続できない

**確認事項:**
1. APIトークンが正しいか確認
   - JIRA用とConfluence用で**別々のトークン**が必要
   - トークンの有効期限が切れていないか
2. メールアドレスが正しいか確認
3. Claude Codeを再起動したか確認

---

## 手動インストール（上級者向け）

自動インストーラーを使用せず、手動でインストールする場合：

```bash
# Mac/Linux
mkdir -p ~/.mcp/mcp-atlassian
cd ~/.mcp/mcp-atlassian
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Mattun1212/mcpfork.git

# Windows
mkdir $HOME\.mcp\mcp-atlassian
cd $HOME\.mcp\mcp-atlassian
python -m venv .venv
.venv\Scripts\activate
pip install git+https://github.com/Mattun1212/mcpfork.git
```

その後、`~/.claude.json` を手動で編集してください。

---

**次のステップ**: [ステップ4: Claude Codeの起動と確認](#ステップ4-claude-codeの起動と確認)
