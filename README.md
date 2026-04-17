# file-translator

Translate and rename files and folders from any language to any other — in one interactive session.

Paste a folder path, confirm the auto-detected language, edit one sample filename to show how you want things cleaned up, and the tool learns your pattern and applies it to everything.

---

## Features

- **Auto language detection** — scans filenames and identifies the source language automatically
- **Pattern learning** — translate one sample, edit it to your liking, and the tool infers rules for the entire folder
- **Smart cleaning** — strips leading number prefixes, parenthetical tags `(AVC)`, `[1080p]`, underscores, and more — based on what you actually showed it
- **Serial numbering** — add `01`, `02`... prefixes, with your choice of padding and separator
- **Preserves ALL-CAPS tags** — `(AVC)`, `HD`, `FLAC` stay uppercase; only regular words are title-cased
- **Conflict guard** — if two files translate to the same name, appends `_2`, `_3` etc. automatically
- **Works anywhere** — local folders, external drives, NAS — any path your OS can see
- **50+ languages supported** — powered by Google Translate via `deep-translator`

---

## Demo

```
════════════════════════════════════════════════════════
    FILE & FOLDER TRANSLATOR / RENAMER  v2
════════════════════════════════════════════════════════

  Folder path: /Volumes/MyDrive/Русские Фильмы

  Detecting language... done.
  Detected : Russian (ru)
  Press Enter to confirm, or type the correct code:

  Translate to (code) [default: en]:

────────────────────────────────────────────────────────
  Pattern Learning
────────────────────────────────────────────────────────

  Sample file found:
  Original   : 8103090_Жизнь - это Тайна_(AVC).mkv

  Translating sample... done.
  Translated : 8103090_Life Is A Mystery_(Avc).mkv

  Edit this to how you want the final filename to look.
  (Just the name — no extension needed)

  Your version: 01 Life Is A Mystery

────────────────────────────────────────────────────────
  Learned pattern:
  • Strip leading number prefix (e.g. 8103090_)
  • Replace underscores with spaces
  • Remove parenthetical tags e.g. (AVC), [1080p]
  • Add serial number prefix (starting 01, separator ' ')
────────────────────────────────────────────────────────

  Apply this pattern to all files? (Enter / n):

════════════════════════════════════════════════════════
  Folder  : /Volumes/MyDrive/Русские Фильмы
  From    : Russian (ru)
  To      : English (en)
════════════════════════════════════════════════════════

────────────────────────────────────────────────────────
  Renaming: Russian Movies
────────────────────────────────────────────────────────

  [FILE]   8103090_Жизнь - это Тайна_(AVC).mkv
       →   01 Life Is A Mystery.mkv
  [FILE]   8209841_Война и Мир_(AVC).mkv
       →   02 War And Peace.mkv
  [FOLDER] Русские Фильмы
       →   Russian Movies

────────────────────────────────────────────────────────
  Done — 2 file(s), 1 folder(s) renamed.
────────────────────────────────────────────────────────
```

---

## Requirements

- Python 3.8+
- `deep-translator`

```bash
pip install deep-translator
```

---

## Installation

```bash
git clone https://github.com/AdinathChaudhari/file-translator.git
cd file-translator
pip install deep-translator
```

---

## Usage

```bash
python file_translator.py
```

The tool is fully interactive — no flags or config needed.

### Step-by-step

1. **Paste the folder path** — drag and drop from Finder/Explorer into the terminal, or type it manually
2. **Confirm the detected language** — press Enter to accept, or type the correct language code (e.g. `fr`, `ja`)
3. **Choose the target language** — defaults to `en` (English)
4. **Edit the sample** — the tool translates one file and shows you the result; type how you'd actually want it to look
5. **Review learned rules** — the tool shows what it inferred from your edit; confirm or cancel
6. **Done** — all files and folders are renamed

### Passing a path from an external drive (macOS)

External drives mount under `/Volumes/`. Drag the folder into the terminal when prompted — macOS will paste the full path automatically.

---

## Pattern learning

When you edit the translated sample, the tool compares your version against the raw translation to infer rules:

| What you did | Rule learned |
|---|---|
| Removed `8103090_` prefix | Strip all leading number prefixes |
| Removed `(Avc)` or `[1080p]` | Strip all parenthetical/bracket tags |
| Replaced `_` with spaces | Normalize underscores to spaces |
| Added `01` at the start | Add sequential serial numbers |

Rules are shown back to you before anything is renamed.

---

## Serial numbering

If the tool detects you added a number prefix, it asks:

```
  Serial numbering detected.
  [1] Number by folder sort order (alphabetical)
  [2] Number sequentially starting from your number
```

- **Option 1** — files are numbered in the alphabetical order they appear in the folder
- **Option 2** — files are numbered starting from the number you typed (e.g. `01`, `001`)

Padding and separator (space, dot, dash) are inferred from your example.

---

## Supported languages

Any language supported by Google Translate. Common codes:

| Code | Language | Code | Language |
|------|----------|------|----------|
| `ar` | Arabic | `ja` | Japanese |
| `zh-cn` | Chinese (Simplified) | `ko` | Korean |
| `fr` | French | `pt` | Portuguese |
| `de` | German | `ru` | Russian |
| `hi` | Hindi | `es` | Spanish |
| `it` | Italian | `tr` | Turkish |

Pass `auto` as the source language to let Google detect it. The tool does this automatically.

---

## FAQ

**Will it rename files on an external hard drive?**
Yes — any path your OS can access works. Drag the folder into the terminal when prompted.

**What if two files translate to the same name?**
A `_2`, `_3` suffix is appended automatically so nothing is overwritten.

**Does it rename the top-level folder I pass in?**
Yes — after all inner files and subfolders are done, the root folder itself is also renamed.

**Can I skip the pattern learning and just translate?**
Yes — when the sample is shown, press Enter without typing anything to accept the translation as-is with no cleaning rules applied.

**Does it work on Windows?**
Yes — illegal filename characters are stripped automatically for all platforms.

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Acknowledgements

- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate wrapper
