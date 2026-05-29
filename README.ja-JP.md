<p align="center">
  <img src="https://github.com/user-attachments/assets/d4f48f71-d76e-4ffe-9fb1-0b075d79bf05" alt="forza-painter FH6 logo" width="720">
</p>

<h1 align="center">forza-painter FH6</h1>

<p align="center">
  <strong>画像を Forza Horizon 6 の Vinyl Group レイヤーに変換・インポートするデスクトップツール。</strong>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="README.ja-JP.md">日本語</a> ·
  <a href="README.ko-KR.md">한국어</a>
</p>

<p align="center">
  <a href="README.md">README</a> ·
  <a href="FAQ.md">FAQ</a> ·
  <a href="ACKNOWLEDGEMENTS.md">Acknowledgements</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="LICENSE">License</a>
</p>

<p align="center">
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>単一 EXE</code>
</p>

PNG/JPG/BMP 画像を Forza Horizon 6 の Vinyl Group レイヤーに変換します。アプリ内で生成・プレビュー・インポートまで完結し、一般ユーザーは Python、`.venv`、バッチファイル、手動のメモリアドレス入力は不要です。

> **EXE のダウンロード:** [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) から `forza-painter-fh6-v1.6.6.exe` を取得し、そのまま実行してください。

> **結果がぼやける場合:** まず **Random samples**（ランダムサンプル）を上げてください。**200000** 以上で品質が大きく変わることが多いです。

> **インポートに時間がかかることがあります:** 複数の FH6 テンプレート検出方式を試行し、最大 5 分かかる場合があります。FH6 を Vinyl Group Editor のままにし、メニューを切り替えないでください。

| 機能 | 説明 |
| --- | --- |
| JSON 生成 | 同梱の GPU/OpenCL 生成器で画像を geometry JSON に変換します。 |
| 画像プレビュー | 生成前に前処理フィルター（luma、バイラテラル、ポスタライズ、セルシェーディングなど）を比較できます。 |
| テキストビニール | GB2312 ライブラリとシステムフォントで CJK 入力、または参考画像からトレース。 |
| Final JSON インポート | 生成した geometry JSON を FH6 にインポート。 |
| Handmade JSON インポート | FH6 タイプコード / 手作り JSON をインポート。 |
| ゲーム JSON エクスポート | 開いている FH6 ビニールグループを手作り JSON としてエクスポート。 |
| 安全な FH6 ワークフロー | 書き込み前に編集可能なレイヤーテーブルを自動検出・検証。 |
| 更新確認 | 起動時に新バージョンを確認し、変更履歴を表示。 |

## クイックスタート

1. [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) から `forza-painter-fh6-v1.6.6.exe` をダウンロードします。
2. EXE を通常の書き込み可能フォルダーに置きます（例: `Desktop\forza-painter-fh6`）。
3. EXE をダブルクリックして起動します。**インポートまたはエクスポート**時に同意を求め、必要なら UAC（管理者）プロンプトが表示されます。
4. FH6 で `Create Vinyl Group` / `Vinyl Group Editor` を開き、sphere テンプレートを読み込んで `Ungroup` します。
5. アプリの **Create** で JSON を生成し、**Import → Import Final JSON** で**正確なテンプレートレイヤー数**を入力してインポートします。ヘッダーの **Help** からチュートリアルと安全ガイドを開けます。

開発目的でなければ、GitHub の自動 `Source code` ZIP は不要です。一般ユーザーは `.exe` のみで十分です。

## プレビュー

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/app-import-preview.png" alt="アプリのインポート画面"><br>
      <strong>アプリのインポート画面</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-template-ready.png" alt="FH6 テンプレート準備完了"><br>
      <strong>FH6 でテンプレート準備完了</strong>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-import-result.png" alt="FH6 インポート結果"><br>
      <strong>インポート結果</strong>
    </td>
    <td align="center" width="50%">
      <img src="docs/screenshots/fh6-car-applied.png" alt="FH6 車への適用結果"><br>
      <strong>車への適用結果</strong>
    </td>
  </tr>
</table>

## 品質プリセット（概要）

| プリセット | レイヤー | ランダムサンプル | 備考 |
| --- | ---: | ---: | --- |
| 0. Tailored（実験） | 画像ごと | 画像ごと | 任意。Image Preview 分析後に生成。**Normal（4）がデフォルト。** |
| 1. Eco（実験） | 1500 | 90000 | GPU 負荷を抑える |
| 4. Normal | 1800 | 120000 | 推奨デフォルト |
| 7. Maximum Power | 2900 | 1000000 | 最高品質、最も遅い |

詳細なプリセット表・手順・トラブルシューティング・安全 FAQ: **[FAQ.md](FAQ.md)**（英語）

## その他のドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [FAQ.md](FAQ.md) | ワークフロー、ルール、トラブルシューティング（英語） |
| [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) | 謝辞と上流プロジェクト |
| [CHANGELOG.md](CHANGELOG.md) | バージョン履歴（アプリ内更新も参照） |
| [SECURITY.md](SECURITY.md) | セキュリティポリシー |
| [docs/SAFETY.ja.md](docs/SAFETY.ja.md) | 安全ガイド（日本語） |
| [docs/TEXT_VINYL.md](docs/TEXT_VINYL.md) | テキストビニール参考 |
