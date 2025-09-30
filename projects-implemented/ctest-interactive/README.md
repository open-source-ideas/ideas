# C-Test Creator & Evaluator

A lightweight, entirely client-side tool for creating and practising C-Tests (cloze tests
that remove the second half of words). Paste a paragraph, generate an interactive exercise,
and receive instant feedback as you fill the blanks.

## Features

- ✅ Generates C-Tests from any text (first sentence intact, subsequent words truncated by default).
- ✅ Adjustable settings: choose which sentence to start blanking from, ignore short words, remember preferences locally.
- ✅ Inline inputs with colour feedback for correct/incorrect answers.
- ✅ Per-gap "Hint" buttons reveal the next character when you are stuck.
- ✅ Optional score summary and answer reveal.
- ✅ Works offline—just open `index.html` in a browser.

## Getting Started

1. Open `index.html` in your preferred browser.
2. Paste a text of at least two sentences or click **Load sample text**.
3. Click **Generate C-Test**.
4. (Optional) Open the **Test settings** panel to tweak how gaps are generated.
5. Complete the gaps. Use **Hint**, **Check score**, or **Reveal answers** as needed.

## Implementation Notes

- All logic lives in `app.js`. It tokenises your text, removes the latter halves of
  words (starting from the second sentence), and renders inputs alongside the word
  prefixes.
- No data leaves your computer—everything runs in the browser.
- The project keeps the structure intentionally minimal so it can be embedded or
  extended in other projects (for example, integrating with spaced repetition or
  user accounts).

## Roadmap

- [ ] Support exporting and importing tests (JSON).
- [ ] Provide multiple truncation strategies (e.g. start from sentence 3, skip short words).
- [ ] Add keyboard shortcuts for hints and navigation.
- [ ] Offer light/dark theme toggle and accessibility tweaks.

## Reference

- [Wikipedia: C-Test](https://en.wikipedia.org/wiki/C-test)
- Inspiration based on the request in [open-source-ideas/ideas#174](https://github.com/open-source-ideas/ideas/issues/174).
