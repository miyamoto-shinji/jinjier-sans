# jinjer sans 導入ガイド

## Web／プロダクト

`web/` を会社管理CDNへバージョン付きで配置し、`jinjer-sans.css` を読み込みます。公開CSSのURLはリリースごとに固定し、`latest` のような可変URLは使いません。転送量の完了条件に合わせ、既定CSSは400／700の静的Unicode-range版です。可変版は`jinjer-sans-variable.css`として、見本、Figma、機能フラグ付き検証で利用できます。

```html
<link rel="preload" href="/fonts/jinjer-sans/1.0.0/jinjer-sans.css" as="style">
<link rel="stylesheet" href="/fonts/jinjer-sans/1.0.0/jinjer-sans.css">
```

```css
:root {
  --font-family-sans: "jinjer sans", Inter, "Noto Sans JP", sans-serif;
}

body {
  font-family: var(--font-family-sans);
  font-weight: 400;
}
```

100〜900の連続ウェイトをWebで試す画面だけ、読み込むCSSを`jinjer-sans-variable.css`へ変更します。可変フォント非対応環境や問題切り分け時には、従来のInter／Noto Sans JPスタックへ戻します。

## 社内PC／Office／Adobe

`desktop/` の静的4ファイルだけをインストールします。旧版を削除してOSのフォントキャッシュを更新してから新版を入れてください。PowerPointへ埋め込む場合は、共有先のライセンス表示と社内情報管理ルールを確認してください。

- `jinjerSans-Thin.ttf` — 100
- `jinjerSans-Regular.ttf` — 400
- `jinjerSans-Bold.ttf` — 700
- `jinjerSans-Black.ttf` — 900

Figmaでは `jinjerSans-VF.ttf` を利用し、ウェイトを100〜900で指定します。

## 制約

- v1は横書き・直立体のみです。
- 絵文字はOSの絵文字フォントへフォールバックします。
- フォントソフトウェアはSIL Open Font License 1.1です。制作物自体へOFLが波及することはありません。
