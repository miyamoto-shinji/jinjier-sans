# jinjer sans

`jinjer sans` は、Inter由来の欧文とNoto Sans JP由来の和文を調和させ、26字のjinjer独自アウトラインを加えた横書きUI向けブランドフォントです。

初めてこのリポジトリを触る場合は、最初に [ディレクトリガイド](DIRECTORY-GUIDE.md) を読んでください。どのフォルダが編集用・自動生成・配布用なのかを説明しています。

## 成果物

- `wght 100–900` 可変TTF／WOFF2
- Thin 100、Regular 400、Bold 700、Black 900の静的TTF
- Google Fonts方式の日本語Unicode-range分割WOFF2とCSS（Web既定は転送量を抑えた400／700、検証用に可変100–900も同梱）
- デスクトップ配布ZIP、ライセンス、クレジット、FONTLOG、チェックサム、比較見本

## ビルド

Python 3.11以降が必要です。上流フォントとGen Interface JPは `sources.lock.json` のコミット・SHA256へ固定されています。

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m jinjer_sans.build all --jobs 4
.venv/bin/python -m jinjer_sans.qa
```

初回は約40MBの上流アーカイブを取得し、約19,500グリフ×4マスターを処理するため時間がかかります。`dist/masters/` は再利用され、変更時は `--force` で再生成できます。

段階別コマンドは `make fetch`、`make masters`、`make font`、`make web`、`make release` です。

## 技術構成

1. Gen Interface JP v0.8.0の合成処理を固定上流ビルダーとして使用
2. InterとNotoを全ウェイトで同一の可変ソースから静的化
3. 和文92.5%、ベースライン+25、本文トラッキングを適用
4. 26字と関連OpenType字形へjinjerの有機的フローを適用
5. 4つの互換マスターからfontTools varLibで `wght` 可変フォントを生成
6. 可変版から静的4ウェイトとWeb分割版を生成

詳細は [導入ガイド](docs/INSTALL.md)、[QA](docs/QA.md)、[ブランド字形](docs/BRAND-GLYPHS.md) を参照してください。

## ライセンス

生成フォントはSIL Open Font License 1.1です。ビルドコードはMIT Licenseです。Inter、Noto Sans JP、Gen Interface JP、OFL Font Bakerの権利表示は [CREDITS.md](CREDITS.md) を参照してください。
