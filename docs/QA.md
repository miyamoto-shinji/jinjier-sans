# QAマトリクス

## 自動検査

- `make test` — 設定、命名、ウェイト契約
- `make qa` — ビルド成果物、文字収録、可変／静的一致
- `make qa-external` — OTS Sanitizer、HarfBuzz、FontBakery（インストール済みのもの）

FontBakery 1.1は、固定したGen Interface JPビルダーとFreeType依存が競合するため、別の仮想環境へインストールして実行します。

```bash
python3 -m venv .fontbakery-venv
.fontbakery-venv/bin/pip install fontbakery==1.1.0
.fontbakery-venv/bin/fontbakery check-universal --configuration fontbakery.toml --succinct dist/desktop/jinjerSans-VF.ttf
```

`fontbakery.toml` では、フルCJKデスクトップ版では意図的となるファイル容量、上流由来のU+0488／U+0489ゼロ幅、採用範囲外の拡張ラテン等の大小文字ペアだけを理由付きで除外します。その他のFAILは許容しません。

### FontBakery／OTS警告記録

最終実行は`ERROR 0 / FATAL 0 / FAIL 0 / WARN 9 / PASS 93`です。警告は次の理由で記録・許容します。

- `gdef_mark_chars` — InterのMarkFilteringSetを合成グリフ順へ復元した結果。OTS受理とHarfBuzzシェーピングを優先する。
- `xavgcharwidth` — 欧文と全角CJKを同居させたOS/2平均幅。実際のadvanceと画面比較を基準にする。
- `cjk_chws_feature` — `chws`／`vchw`未搭載。v1は横書きUIで、和文の比例幅と字間はビルド時に適用済み。
- `mandatory_avar_table` — 公開`wght`は意図的に線形補間するため`avar`を持たない。
- `math_signs_width` — 半角欧文記号と全角CJK記号が混在する設計上の幅差。
- `ots-sanitize-warn` — 上流合成レイアウトのタグ順。サニタイズは成功し、エラーは0件。
- `soft_hyphen` — Inter由来のU+00ADを互換性のため保持する。
- `overlapping_path_segments` — 上流互換輪郭に由来。中間ウェイトの反転・飛びは別検査で発生していない。
- `unreachable_glyphs` — 合成時の代替字形を保持したもの。cmapと評価コーパスに欠落はない。

## 転送量

`performance-baseline.json` に評価コーパスで実測した現行Google Fonts版Inter＋Noto Sans JPの414,796 bytesを固定しています。評価コーパスを重複なしの先頭`jinjer UI core`スライスへまとめ、残りはGoogle方式の順序を維持します。ビルドは400／700静的分割版の合計が基準を超えると失敗します。可変分割版は検証用CSSとして残します。

## 手動検査

次を100／250／400／550／700／800／900、12／16／24／48pxで確認します。

- Chrome、Edge、Safari、Firefoxの最新2世代
- Windows 11とmacOSのMicrosoft 365
- Figma、Illustrator、PDF書き出し
- 社員一覧、勤怠、給与、コーポレートページ
- 英数字と和文の重心、行高、ボタン幅、金額の桁、メール・IDの判別性

`specimen/index.html` はブランド責任者、プロダクト、アクセシビリティ担当の承認用見本です。
