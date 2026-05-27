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
  <code>v1.6.6</code> · <code>Windows</code> · <code>Forza Horizon 6</code> · <code>GPU/OpenCL</code> · <code>単一 EXE</code>
</p>

PNG/JPG/BMP 画像を Forza Horizon 6 の Vinyl Group レイヤーに変換します。アプリ内で生成・プレビュー・インポートまで完結し、一般ユーザーは Python、`.venv`、バッチファイル、手動のメモリアドレス入力は不要です。

> **EXE のダウンロード:** [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) から `forza-painter-fh6-v1.6.6.exe` を取得し、そのまま実行してください。

> **結果がぼやける場合:** まず `Random samples`（ランダムサンプル）を上げてください。**200000** 以上で品質が大きく変わることが多く、数値が高いほど鮮明ですが生成時間も長くなります。

> **インポートに時間がかかることがあります:** v1.4.1 以降、複数の FH6 テンプレート検出方式を試行し、安全なレイヤーテーブルの特定に最大 5 分かかる場合があります。FH6 を Vinyl Group Editor のままにし、メニューを切り替えないでください。失敗する場合は詳細ログをエクスポートしてください。

| 機能 | 説明 |
| --- | --- |
| JSON 生成 | 同梱の GPU/OpenCL 生成器で画像を geometry JSON に変換します。 |
| 画像プレビュー | 生成前に前処理フィルター（luma、バイラテラル、ポスタライズ、セルシェーディングなど）を比較できます。 |
| テキストビニール | 中国語/CJK の GB2312 ライブラリとシステムフォントで入力、または参考画像からトレース。詳細は `docs/TEXT_VINYL.md`。 |
| Final JSON インポート | 生成した geometry JSON を FH6 にインポート（実行フォルダー、最適 final 選択）。 |
| Handmade JSON インポート | FH6 タイプコード / 手作り JSON（四角、円、三角など）をインポート。 |
| ゲーム JSON エクスポート | 開いている FH6 ビニールグループを手作り JSON としてエクスポート。 |
| 安全な FH6 ワークフロー | 書き込み前に編集可能なレイヤーテーブルを自動検出・検証。 |
| 更新確認 | 起動時に新バージョンを確認し、利用可能な場合は変更履歴を表示。 |

## クイックスタート

1. [Releases](https://github.com/ShepherdHL/forza-painter-fh6/releases) から `forza-painter-fh6-v1.6.6.exe` をダウンロードします。
2. EXE を通常の書き込み可能フォルダーに置きます（例: `Desktop\forza-painter-fh6`）。
3. EXE をダブルクリックして起動します。FH6 へのインポートで Windows がプロセスアクセスをブロックする場合は、管理者として実行してください。
4. FH6 で `Create Vinyl Group` / `Vinyl Group Editor` を開き、sphere テンプレートを読み込んで `Ungroup` します。
5. アプリで JSON を生成し、**Import Final JSON** を開いて、**ゲーム内の正確なテンプレートレイヤー数**を入力してからインポートします。

開発目的でなければ、GitHub の自動 `Source code` ZIP をダウンロードする必要はありません。一般ユーザーは `.exe` のみで十分です。

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

## JSON 生成

1. `Generate JSON`（JSON 生成）ページを開きます。
2. `Add images`（画像を追加）をクリックし、PNG/JPG/BMP 画像を選択します。
3. 任意: **Image Preview**（画像プレビュー）で前処理フィルターを比較し、生成に使うものを選びます。
4. 品質プリセットと任意の **Preprocess Filter**（luma バンド、バイラテラル、ポスタライズ、セルシェーディングなど）を選択します。
5. 任意: `Use custom settings`（カスタム設定を使用）を有効にし、出力レイヤー数、解像度、ランダムサンプル、変異サンプルを変更します。
6. 下部の固定 `Start generating`（生成を開始）ボタンをクリックします。
7. プレビューとログが更新されるまで待ちます。

生成ファイルは元画像の横に保存されます（例: `image.500.json`、`image.1000.json`、`image.3000.json`）。

1 枚の画像から複数のチェックポイント JSON ができる場合があります。テンプレートに最も合う**レイヤー数が多い** JSON を優先してください。例: 3000 レイヤーのテンプレートには `image.3000.json` または最終の `image.json` を使用します。500 レイヤーの JSON を 3000 レイヤーのテンプレートにインポートすると、結果はぼやけて見えます。

| プリセット | 出力レイヤー | ランダムサンプル | 用途 |
| --- | ---: | ---: | --- |
| extremely fast | 500 | 30000 | 構図の素早い確認 |
| fast | 1000 | 60000 | 素早い下書き |
| balanced | 1800 | 120000 | 推奨デフォルト |
| slow | 2500 | 220000 | 仕上げ品質（200k+ の品質帯） |
| super slow | 3000 | 350000 | 最高の鮮明さ、非常に時間がかかる |

## テキストビニール

ゲーム内の文字ツールで表示できない文字（中国語、カタカナ、その他 CJK）には **Text vinyl**（テキストビニール）タブを使用します。

テキストビニールは PC にインストールされたフォント（例: 設定 > 個人用設定 > フォント）から識別します。インストール済みフォントを選ぶか、GB2312 ライブラリから文字を直接挿入できます。画像由来の文字は、参考画像パネルの **画像からトレース** を使用してください（`docs/TEXT_VINYL.md` 参照）。

## JSON インポート

### Import Final JSON（生成された geometry）

1. FH6 を起動し、`Vinyl Group Editor` を開いたままにします。
2. 多数の単純な sphere レイヤーで構成されたテンプレートを読み込むか作成します。
3. テンプレートを `Ungroup` し、ゲームに表示される**正確な**レイヤー数を控えます。
4. **Import Final JSON** を開き、`Refresh` をクリックして `forzahorizon6.exe` を選択します。
5. 正確なテンプレートレイヤー数を入力します（**必須**）。
6. 生成実行フォルダーを選ぶか、`.json` を追加するか、**Use generated outputs**（生成出力を使用）を使います。
7. **Import final JSON into FH6**（Final JSON を FH6 にインポート）をクリックします（サポートから指示されない限り、高度なアドレス欄は空のままにします）。

### Import Handmade JSON（タイプコード形状）

1. 上記と同じゲーム接続とテンプレートレイヤー数を使用します。
2. **Import Handmade JSON** を開き、手作り/タイプコード `.json` を追加し、プレビューで対応/非対応形状数を確認します。
3. インポート後、FH6 で**ビニールグループを保存して再読み込み**し、形状が正しく表示されるようにします。
4. 任意: インポート後にグループレイヤー数をトリム。実験的な形状コードは JSON の出所を理解している場合のみ許可してください。

### Export Game JSON（ゲーム JSON エクスポート）

1. FH6 の Vinyl Group Editor でコピーしたいビニールグループを開いた状態で、**Export Game JSON** を開きます。
2. **Export open FH6 group to JSON**（開いている FH6 グループを JSON にエクスポート）をクリックします（ファイルはアプリ横の `runtime/typecode-export/` に保存されます）。

FH はカバー保存と適用範囲を正しく処理するため、追加の境界レイヤー 4 つが必要です。例: 1000 レイヤーの JSON には少なくとも 1004 レイヤーのテンプレートを使用します。3000 レイヤーのテンプレートでは、描画可能な形状は約 2996 個までインポートできます。

## 重要なルール

- FH6 テンプレートはインポート前に Ungroup されている必要があります。
- アプリのレイヤー数はゲーム内の表示と**完全に一致**させてください。
- インポート中はゲームメニューを切り替えないでください。
- FH6 の再起動、テンプレートの再読み込み、レイヤー数の変更後は、新しい正しい数で再インポートしてください。
- JSON のレイヤー数がテンプレートより少ない場合、未使用のテンプレートレイヤーは非表示になります。
- JSON のレイヤー数がテンプレートより多い場合、超過分の形状はトリムされます。
- 透明 PNG の透明部分は、可視の背景色としてインポートされません。

## ランタイムファイル

単一 EXE は内部ファイルを一時展開し、通常のランタイムデータは EXE の外に保存します。正確なパスは起動ログと `Tools`（ツール）ページに表示されます。

EXE の横にできる外部フォルダー:

- `runtime/`: ログ、生成セッションデータ、一時ファイル。
- `webui-data/`: ローカルブラウザ/UI キャッシュ。

アプリを終了したあと、これらのフォルダーを削除するとローカルランタイムデータをリセットできます。

## トラブルシューティング

- **EXE が FH6 にインポートできない:** アプリを閉じ、EXE を管理者として実行してください。
- **GPU/OpenCL エラー:** NVIDIA/AMD/Intel のグラフィックスドライバーを更新してください。同梱生成器は OpenCL を使用します。
- **テンプレートを特定できない:** Vinyl Group Editor にいること、テンプレートが Ungroup されていること、レイヤー数が正確であること、スキャン中にメニューを切り替えていないことを確認してください。
- **インポート結果がぼやける:** より高レイヤーの JSON を使うか、`Output layers` / `Random samples` を増やしてください。
- **デバッグが必要:** アプリの `Export detailed log`（詳細ログをエクスポート）を使い、ログを issue に添付してください。

## リソース

- インポート解説動画: https://www.bilibili.com/video/BV1hG5Z6nENZ
- 同梱 GPU 生成器のソース/参考: https://github.com/zjl88858/forza-painter-geometrize-gpu
- 完全な変更履歴: [CHANGELOG.md](CHANGELOG.md)

## FAQ

*（the_adawg 版を基に改編）*

### このツールは具体的に何をするのですか？

[TRON](https://youtu.be/6Nn7J1Eb87E?si=m6VR8BdN_jAZZMgo) のようなリアルタイム分解を、画像に対して行うツールです。多くのユーザーは、アニメやカートゥンキャラクターなどを取り込む用途で使っています。

任意の画像を、Forza Horizon のビニールエディターで使える基本形状（正方形、長方形、円など、画像に最適な形状）に分解します。

6 つのプリセットから詳細度を選ぶか、独自設定を書けます。低詳細・高速から高詳細・長時間処理まで幅があります。

この版は GPU で形状生成を行います。高詳細生成中はゲームを閉じ、マシンの過熱を避けることを推奨します。警告システムも組み込まれており、生成中はログを時々確認してください。

### BAN されますか？

**免責:** 本ソフトウェアの利用は自己責任です。

非常に詳細なビニールを共有すると、他プレイヤーから通報される可能性があります。手軽に高品質なビニールが作れることへの不公平感を理由にする意見もあります。

*（多くのプレイヤーは通報しません。手作りビニールは通常レイヤー数が少なく効率的で、自動生成より「上手い」だけの場合もあります。）*

その意見は理解できますが、十分な時間と練習があれば手作りでも複雑な画像は再現可能です。本ツールは、その練習だけを強いる必要はない、という立場です。

Forza Painter は Windows のシステム API を通じて Forza Horizon 6 のメモリを直接読み書きします（Cheat Engine などと同様の低レベル手法）。変更対象はコスメティックなビニール/リバリエディタのデータのみで、速度、位置、クレジット、レースタイム、ステータスなどのゲームプレイ数値は変更しません。

実行中のゲームメモリにアクセスするため、アンチチートやアカウントシステムによる検知リスクはゼロではありません。**自己責任でご利用ください。**

### トラブルになりますか？

アップロードする内容次第です。ゲームの利用規約に従えば、通常は問題になりません。重要なのは作成する**内容**であり、必ずしもツールそのものではありません。

Forza Horizon は全年齢向けです。品位を保ってください。

## 謝辞

このプロジェクトは Forza Painter ワークフローを基にした派生プロジェクトであり、上流の MIT ライセンス表記を保持しています。

| 個人 / プロジェクト | リンク | 貢献 |
| --- | --- | --- |
| the_adawg (AE) | [forza-painter/forza-painter](https://github.com/forza-painter/forza-painter) | オリジナル Forza Painter：MIT ライセンスの FH インポートワークフロー、メモリ書き込み/インポート基盤、ジオメトリ→ビニール手法。 |
| Sam Twidale | [samcodes.co.uk](https://samcodes.co.uk/) | geometrize-lib；上流ライセンスでクレジットされるジオメトリ近似の原典。 |
| Michael Fogleman | [fogleman/primitive](https://github.com/fogleman/primitive) | Primitive ライブラリ；上流ライセンスでクレジットされるプリミティブベース画像近似。 |
| Omar Cornut | [ocornut/imgui](https://github.com/ocornut/imgui) | Dear ImGui；オリジナル forza-painter の GUI フレームワーク。 |
| DxBang | [Bang's Forza Color Converter](https://bang.systems/forza-colors/) | 「色」タブで使用する Forza H/S/B 色変換。 |
| bvzrays | [bvzrays/forza-painter-fh6](https://github.com/bvzrays/forza-painter-fh6) | FH6 向けデスクトップフォーク：UI、インポーター/ロケーター、パッケージング、FH6 ワークフロー。 |
| Kloudy (heyitshestia) | [kloudys-fh6-painter](https://github.com/heyitshestia/kloudys-fh6-painter) | FH6 ペインターフォーク：ランチャー、スタイルプリセット、Luma Prep、Edge Repair、完成チェックポイント、更新フロー、手作り/汎用インポーター。 |
| zjl88858 | [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu) | 同梱 GPU/OpenCL geometrize 生成器の系譜。 |
| LibreHardwareMonitor | [LibreHardwareMonitor/LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | リソースモニタータブのハードウェア監視バックエンド。 |
| H3XDaemon | [H3XDaemon](https://github.com/H3XDaemon) | 本リポジトリの貢献者。 |
| MaccLochlainn | [MaccLochlainn](https://github.com/MaccLochlainn) | 本リポジトリの貢献者。 |
| ree9622 | [ree9622](https://github.com/ree9622) | 上流履歴における韓国語ローカライズ貢献者。 |

全コミットの一覧は [contributor graph](https://github.com/ShepherdHL/forza-painter-fh6/graphs/contributors) を参照してください。

## 変更履歴

ここにはバージョン付きリリースのみを記載しています。アプリの更新プロンプト用の完全な履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

### v1.6.6 / 2026-05-26

- アプリバージョンを `v1.6.6` に更新。リリースパッケージは `forza-painter-fh6-v1.6.6.exe` を使用。
- RGB/BGR 処理の `luma_band` 前処理を修正し、前処理画像の書き込みをアトミック化。
- リリースビルドで `luma_band` が動作するよう OpenCV と NumPy を単一 EXE に同梱。
- インポート開始前に FH6 テンプレートレイヤー数の入力を必須化。
- 型付き例外と共有ユーティリティでコアモジュールをリファクタリング。

### v1.6.5 / 2026-05-25

- アプリバージョンを `v1.6.5` に更新。リリースパッケージは `forza-painter-fh6-v1.6.5.exe` を使用。
- 同梱 GPU 生成器を upstream `v1.2-Canary-20260525` に更新。
- 同梱プリセットの `forceOpaqueShapes` デフォルトを `false` に変更。
- サニタイズされた生成器環境と低速ファイルポーリングで生成中のメインアプリ負荷を軽減。

### v1.6.1 / 2026-05-24

- アプリバージョンを `v1.6.1` に更新。リリースパッケージは `forza-painter-fh6-v1.6.1.exe` を使用。
- 同梱プリセットで `luma_band` 前処理をデフォルト無効化。
- インポート時に `webui-data` の古い FH6 セッションを再利用せず、書き込み前に現在のテンプレートを再検出。
- JSON プレビューを単一の安定レンダラーパスに統一し、パッケージ EXE 間の楕円プレビュー歪み差を低減。

### v1.6.0 / 2026-05-24

- アプリバージョンを `v1.6.0` に更新。リリースパッケージは `forza-painter-fh6-v1.6.0.exe` を使用。
- 同梱 GPU 生成器を upstream `canary-26052401` に更新。
- upstream の `errorGridSize` プリセット対応を追加。
- 透明領域のはみ出し防止の upstream アルゴリズム調整を統合。
- 透明画像下部の大きな楕円の生成品質を大幅改善。

### v1.5.4 / 2026-05-23

- 高解像度ソース、生成器プレビュー PNG、JSON プレビューのスケーリングを修正し、パネル内で伸びずに全体表示。
- JSON プレビューの type 16 回転楕円レンダリングを修正し、インポート画面での扁平化/誤回転を解消。

### v1.5.3 / 2026-05-22

- EXE 向けカスタムプリセットインポート、画像/JSON リスト削除、チェックポイント再利用、安全な出力命名、Pillow プレビュー fallback を追加。

### v1.5.2 / 2026-05-22

- 一般ユーザー向けの真の単一 EXE を追加（Python、`.venv`、ヘルパーファイル不要）。
- GUI EXE がインポートと FH6 メモリプローブのため非表示ヘルパーモードで自身を再起動可能に。
- Tools ページと起動ログに外部ランタイム/キャッシュの場所を表示。

### v1.5.1 / 2026-05-22

- プロジェクト `.venv` に `pip` がない場合の起動時依存関係インストール失敗を修正。
- 不完全なソースパッケージ展開の診断メッセージを改善。

### v1.5.0 / 2026-05-22

- 同梱 GPU/OpenCL 生成器を upstream `canary-26052102` に更新。
- upstream PR #4 の work-group 評価アルゴリズムを追加し GPU 候補評価を高速化。
- 起動時更新確認、ルート `CHANGELOG.md`、ダークデスクトップ UI を追加。

### v1.4.1 / 2026-05-21

- FH6 テンプレート自動検出が v1.3 と v1.4 の両スキャン戦略を試行してから終了。
- RTTI vtable フォールバックロケーターと自動検出待機時間の延長。

### v1.4.0 / 2026-05-21

- 50000 文字上限の詳細ログエクスポートを追加。
- 大きな書き込み可能メモリ領域向け FH6 テンプレート自動検出を改善。

### v1.3.0 / 2026-05-21

- 同梱 GPU/OpenCL 生成器を upstream `canary-26052101` に更新。
- upstream の GPU デバイス選択修正と選択 OpenCL デバイスのログを追加。

### v1.2.0 / 2026-05-20

- 同梱 GPU/OpenCL 生成器を upstream `canary-26052001` に更新。
- 同梱およびカスタム生成設定に `forceOpaqueShapes = true` を明示。

### v1.1.1 / 2026-05-20

- アプリウィンドウ、CLI、リリースパッケージ名の集中バージョン管理を追加。
- リポジトリ構成とリリースパッケージングを整理。
