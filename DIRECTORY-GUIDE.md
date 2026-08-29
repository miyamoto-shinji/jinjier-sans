# jinjer sans ディレクトリガイド

この資料は、フォント制作やPythonに詳しくない方が「どこに何があるか」を把握するための案内です。

最も重要なのは次の3点です。

1. 普段読む資料は`README.md`と`docs/`にあります。
2. ビルド設定や字形を変更するときだけ`src/jinjer_sans/`を編集します。
3. `dist/`は自動生成物です。中身を直接編集せず、配布には`dist/release/`のZIPを使います。

## 全体像

```text
jinjer-sans/
├── .cache/                  取得した元フォントの一時保管場所
├── .fontbakery-venv/        FontBakery専用の検査環境
├── .github/workflows/       GitHub上で自動ビルド・検査する設定
├── docs/                    人が読む仕様書・導入ガイド
├── specimen/                フォント比較見本の編集元
├── src/jinjer_sans/         フォントを作るPythonプログラム
├── tests/                   プログラムの自動テスト
└── dist/                    完成フォントなどの自動生成物
    ├── masters/             可変フォントを作るための中間ファイル
    ├── desktop/             PC・Figma向けフォント
    ├── web/                 Webサイト・プロダクト向けフォント
    ├── specimen/            比較見本の生成版
    └── release/             社内配布用の最終ZIP
```

## 普段確認するディレクトリ

### `docs/` — 仕様書と使い方

人が読んだり更新したりする資料です。自動生成ではないため、説明を直すときはここを編集します。

- `INSTALL.md` — Web、PC、Office、Figmaへの導入方法
- `QA.md` — 検査方法、対応環境、既知の警告
- `BRAND-GLYPHS.md` — jinjer独自字形26字の方針

### `specimen/` — 比較見本の編集元

ブラウザでフォントを比較・確認するページの原本です。役割ごとに3ファイルへ分けています。

- `index.html` — ページに載せる文章、見出し、タイプテスター、CDNガイドの内容
- `specimen.css` — 色、余白、文字サイズ、カード、PC／スマートフォン表示などのデザイン
- `specimen.js` — ウェイト・文字サイズのスライダー、サンプル切替、コードのコピーボタン
- 3ファイルは次回のリリース作成時に、まとめて`dist/specimen/`へコピーされます。
- ブランド責任者やプロダクト担当者との字形確認に使います。
- 実際のプロダクト画面ではありません。

### `dist/release/` — 最終配布物

社内へ渡す完成パッケージです。

- `jinjer-sans-1.0.0.zip` — フォント、Web用ファイル、ライセンス、導入ガイドをまとめたもの
- `manifest.json` — ZIPと収録ファイルの容量・SHA256チェックサム

通常、誰かへ共有するときはこのZIPを使います。

## フォントを作るプログラム

### `src/jinjer_sans/` — ビルド処理の本体

ここにはフォントを生成するPythonプログラムがあります。仕様変更がない限り、普段は編集する必要はありません。

| ファイル | 役割 |
|---|---|
| `config.py` | フォント名、4ウェイトの対応、独自字形26字、評価文章を定義する |
| `upstream.py` | Inter、Noto Sans JP、Gen Interface JPを取得し、SHA256が正しいか確認する |
| `brand.py` | 26字と関連字形へjinjer独自の有機的なアウトライン変形を適用する |
| `metadata.py` | フォント名、PostScript名、バージョン、著作権、STATなどを設定する |
| `build.py` | マスター、可変版、静的版、Web版、リリースZIPを順番に作る |
| `webfont.py` | WebフォントをUnicode-rangeで分割し、CSSと転送量マニフェストを作る |
| `qa.py` | 文字欠落、ウェイト、名前、HarfBuzz、OTS、FontBakeryを検査する |

変更の例：

- 評価文章を追加する → `config.py`の`CORPUS`
- 独自字形の対象を変える → `config.py`と`brand.py`
- Web分割方法を変える → `webfont.py`
- フォント名やバージョンを変える → `config.py`と`metadata.py`

### `tests/` — 自動テスト

プログラムを変更したときに、重要な仕様が壊れていないか確認します。

- `test_config.py` — 26字とウェイト対応の確認
- `test_metadata.py` — フォント名とPostScript名の確認
- `test_outputs.py` — 実際に生成したフォントの確認

`make test`で実行します。テストファイル自体は配布物に含めません。

## 自動生成されるディレクトリ

### `dist/` — ビルド結果

`make all`などで作られます。中身を直接修正しても、次回ビルドで上書きされます。

#### `dist/masters/`

100／400／700／900の4つの中間マスターです。この4ファイルの差から可変フォントを作ります。

- 開発・補間検査用です。
- 社内PCやWebへは配布しません。

#### `dist/desktop/`

PC、Figma、Adobe製品向けの完成フォントです。

- `jinjerSans-VF.ttf` — 100〜900の可変版。主にFigmaや検証用
- `jinjerSans-Thin.ttf` — 100
- `jinjerSans-Regular.ttf` — 400
- `jinjerSans-Bold.ttf` — 700
- `jinjerSans-Black.ttf` — 900
- `jinjerSans-VF.woff2` — 分割していないWeb用可変版。診断・検証用

社内PCへインストールする場合は、基本的に静的4ファイルだけを使います。

#### `dist/web/`

Webサイトやjinjerプロダクトへ配置するファイルです。

- `jinjer-sans.css` — 本番用。転送量を抑えた400／700静的版
- `jinjer-sans-variable.css` — 100〜900可変版。見本や機能フラグ付き検証用
- `jinjer-sans-full.css` — 分割なしの診断用。通常の本番配信には使わない
- `tokens.css` — `--font-family-sans`デザイントークン
- `w/400/`、`w/700/` — 本番CSSが読む分割WOFF2
- `w/vf/` — 可変版CSSが読む分割WOFF2
- `nam/` — 各分割ファイルに入るUnicode一覧
- `manifest.json` — 容量、チェックサム、転送量判定

Webへ導入するときは、必要なWOFF2を選んで手作業でコピーするのではなく、`web/`ディレクトリ全体をCDNへ配置します。

#### `dist/specimen/`

`specimen/`からコピーされた確認用見本です。リリースZIPにはこちらが入ります。

#### `dist/release/`

デスクトップ版、Web版、見本、ライセンス、導入ガイドをひとつにまとめます。ここだけを配布窓口として扱います。

### `.cache/` — 元データのキャッシュ

固定したGen Interface JP、Inter、Noto Sans JPが保存されます。

- 自動取得されるため、通常は編集しません。
- リポジトリへコミットしません。
- 削除しても再取得できますが、次のビルドに時間がかかります。
- `make clean-all`で`dist/`と一緒に削除できます。

### `.fontbakery-venv/` — FontBakery専用環境

FontBakeryと通常ビルドのFreeType依存関係が競合しないように分離したPython環境です。

- フォント本体や配布物ではありません。
- リポジトリへコミットしません。
- 削除しても、`docs/QA.md`の手順で再作成できます。

## GitHubとプロジェクト設定

### `.github/workflows/`

GitHubへ変更を送ったときに、自動でビルドと検査を行うCI設定です。フォントのデザイン内容ではなく、検査手順を管理します。

### ルート直下の主なファイル

| ファイル | 役割 |
|---|---|
| `README.md` | プロジェクトの概要とビルド方法 |
| `Makefile` | `make all`などの短い操作コマンド |
| `pyproject.toml` | 必要なPythonとライブラリの定義 |
| `sources.lock.json` | 元フォントのバージョン、取得先、SHA256を固定する |
| `performance-baseline.json` | 現行Inter＋Noto構成の転送量基準 |
| `fontbakery.toml` | FontBakeryで理由付き除外にする検査項目 |
| `OFL.txt` | 生成フォントのSIL Open Font License 1.1 |
| `CREDITS.md` | Inter、Noto、Gen Interface JPなどの権利表示 |
| `FONTLOG.md` | フォントの変更履歴 |
| `LICENSE-CODE` | ビルドプログラムのライセンス |

## 目的別に見る場所

| やりたいこと | 見る場所 |
|---|---|
| 完成フォントを社内へ共有したい | `dist/release/jinjer-sans-1.0.0.zip` |
| PCへフォントを入れたい | `docs/INSTALL.md`と`dist/desktop/` |
| Webへ導入したい | `docs/INSTALL.md`と`dist/web/` |
| フォントの見た目を確認したい | `dist/specimen/index.html` |
| 独自字形の考え方を確認したい | `docs/BRAND-GLYPHS.md` |
| 検査結果や既知の警告を確認したい | `docs/QA.md` |
| フォントを最初から作り直したい | `README.md`のビルド手順 |

## 削除してよいもの／いけないもの

削除しても再生成できるもの：

- `dist/`
- `.cache/`
- `.fontbakery-venv/`
- `.pytest_cache/`
- `__pycache__/`

削除・直接編集しないもの：

- `src/` — フォント生成ロジック
- `docs/` — 導入・QA資料
- `specimen/` — 比較見本の原本
- `sources.lock.json` — 元データの固定情報
- `OFL.txt`、`CREDITS.md` — ライセンスと権利表示

判断に迷った場合は、`dist/`の中を直接直すのではなく、元になる`src/`、`docs/`、`specimen/`のどれを変更すべきか確認してください。
