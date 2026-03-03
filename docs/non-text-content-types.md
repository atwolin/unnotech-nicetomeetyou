# Non-Text Content Types in UDN NBA Articles

Observed inside `#story_body_content` across scraped articles and manual inspection.

## Types Found Inside Article Body

### 1. Embedded Tweets (Twitter/X)

**HTML structure:**

```html
<p lang="en" dir="ltr">
  Tweet text here...
  <a href="https://t.co/...">pic.twitter.com/...</a>
</p>
```

**Detection:** All tweet `<p>` elements have a `lang` attribute (e.g., `lang="en"`). Chinese article paragraphs never carry a `lang` attribute.

**Spider handling:** Skipped via `if p.root.get("lang"): continue`

---

### 2. Live Score Widgets

Two distinct HTML structures exist for this type:

**Structure A — class on `<p>` itself:**

```html
<p class="liveupdates__points ...">-</p>
```

**Structure B — class on a descendant:**

```html
<p>
  <a>
    <div class="liveupdates__container">...</div>
  </a>
</p>
```

The underlying score data is embedded in an inline `<script>` tag on the same page:

```js
window.sGame = [{"date":"2026-02-25","home_team":"LAL","away_team":"ORL","home_score":109,"away_score":110}];
```

**Spider handling:** The widget `<p>` elements are skipped via XPath (both structures caught by `contains(@class,"liveupdates")`). The score data is separately extracted from the inline script via `_extract_livescores()` and stored in `item["livescores"]` as a list of game dicts.

---

### 3. Player Card Widgets

**HTML structure:**

```html
<p>
  <a class="player_card_link">
    <div class="player_card">
      <!-- player stats: position, points, rebounds, assists, steals, season -->
    </div>
  </a>
</p>
```

**Spider handling:** Skipped via `.//a[contains(@class,"player_card_link")]` in XPath filter.

---

### 4. Inline Photos (Figures)

**HTML structure:**

```html
<p>
  Article text here...
  <figure>
    <img src="https://pgw.udn.com.tw/..." />
    <figcaption>Photo caption / Reuters credit</figcaption>
  </figure>
</p>
```

**Spider handling:** The `<p>` itself is **not** skipped. Article text is preserved using XPath `.//text()[not(ancestor::figure)]`, which silently excludes caption text inside `<figure>`.

---

### 5. Inline `<script>` / `<iframe>` Tags

Occasionally a `<p>` may contain raw `<script>` or `<iframe>` elements (e.g., third-party video embeds).

**Spider handling:** Skipped via `.//script | .//iframe` in XPath filter.

---

## Summary Table

| Type | Detection Method | Spider Action |
|------|-----------------|---------------|
| Embedded tweets | `lang` attr on `<p>` | Skip entire `<p>` |
| Live score widget (class on `<p>`) | `contains(@class,"liveupdates")` on self | Skip `<p>`; score data extracted from `window.sGame` inline script |
| Live score widget (class on descendant) | `contains(@class,"liveupdates")` on `.//*` | Skip `<p>`; score data extracted from `window.sGame` inline script |
| Player card widget | `contains(@class,"player_card_link")` on `.//a` | Skip entire `<p>` |
| Inline photo / figure | `<figure>` inside `<p>` | Keep `<p>`, exclude figure text; image+caption stored in `inline_images` |
| Inline script/iframe | `.//script` or `.//iframe` inside `<p>` | Skip entire `<p>` |
