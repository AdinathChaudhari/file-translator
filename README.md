# file-translator

Translate and rename files and folders from any language to any other — in one interactive session.

Paste a folder path, confirm the auto-detected language, edit one sample filename to show how you want things cleaned up, and the tool learns your pattern and applies it to everything.

---

## Features

- **Auto language detection** — scans filenames and identifies the source language automatically
- **Pattern learning** — translate one sample, edit it to your liking, and the tool infers rules for the entire folder
- **Tags preserved exactly** — parenthetical tags like `(AVC)`, `[1080p]`, `(BluRay)` are extracted from the original filename and reinserted verbatim — Google never sees them, so casing is never mangled
- **Smart title casing** — fully-uppercase words like `HD`, `FLAC`, `AVC` are preserved; only regular words are title-cased
- **Serial numbering** — add `01`, `02`... prefixes, with your choice of padding and separator
- **Undo** — after renaming, you're asked if you want to restore everything back to the original names
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

  Original   : 8103090_Жизнь - это Тайна_(AVC).mkv

  Translating sample... done.
  Translated : 8103090_Life Is A Mystery (AVC).mkv

  Edit this to how you want the final filename to look.
  (Just the name — no extension needed. Press Enter to keep as-is.)

  Your version: 01 Life Is A Mystery

────────────────────────────────────────────────────────
  Pattern:
  • Replace underscores with spaces
  • Remove parenthetical tags — (AVC), [1080p] etc.
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

  Undo everything and restore original names? (y / Enter to keep):
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
4. **Edit the sample** — the tool translates one file and shows you the result; type how you'd actually want it to look, or press Enter to keep it as-is
5. **Review learned rules** — the tool shows what it inferred from your edit; confirm or cancel
6. **Undo if needed** — after renaming completes, you're offered the option to restore everything

### Passing a path from an external drive (macOS)

External drives mount under `/Volumes/`. Drag the folder into the terminal when prompted — macOS will paste the full path automatically.

---

## Pattern learning

When you edit the translated sample, the tool compares your version to infer rules:

| What you did | Rule learned |
|---|---|
| Removed `(AVC)` or `[1080p]` | Strip all parenthetical/bracket tags |
| Replaced `_` with spaces | Normalize underscores to spaces |
| Added `01` at the start | Add sequential serial numbers |

If you keep tags in your edit, the rule is: **preserve tags exactly as they appear in the original** — casing and all.

Rules are shown back to you before anything is renamed.

---

## How tags are handled

Tags like `(AVC)`, `[1080p]`, `(BluRay)` are extracted from the **original filename** before sending anything to Google Translate. After translation, they are reinserted verbatim. This means:

- `(AVC)` always stays `(AVC)` — never becomes `(Avc)` or `(avc)`
- Google never sees or modifies them
- If you remove a tag in your sample edit, the tool strips all tags from every file

---

## Undo

After all files are renamed, the tool asks:

```
  Undo everything and restore original names? (y / Enter to keep):
```

Type `y` to reverse every rename in the correct order — files first, then subfolders, then the top-level folder.

---

## Serial numbering

If the tool detects you added a number prefix, it asks:

```
  Serial numbering detected.
  [1] Number by folder sort order (alphabetical)
  [2] Number sequentially starting from your number
```

- **Option 1** — files are numbered in alphabetical order of their original names
- **Option 2** — files are numbered starting from the number you typed (e.g. `01`, `001`)

Padding and separator (space, dot, dash) are inferred from your example automatically.

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

The tool auto-detects the source language — you just confirm or correct it.

---

## FAQ

**Will it rename files on an external hard drive?**
Yes — any path your OS can access works. Drag the folder into the terminal when prompted.

**What if two files translate to the same name?**
A `_2`, `_3` suffix is appended automatically so nothing is overwritten.

**Does it rename the top-level folder I pass in?**
Yes — after all inner files and subfolders are renamed, the root folder itself is renamed last.

**Can I skip the pattern learning and just translate?**
Yes — press Enter when shown the sample to accept the translation as-is with no cleaning rules applied.

**Does it work on Windows?**
Yes — illegal filename characters (`\ / * ? : " < > |`) are stripped automatically.

**What if I don't like the result?**
Type `y` at the undo prompt after processing and everything is restored to the original names.

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Acknowledgements

- [deep-translator](https://github.com/nidhaloff/deep-translator) — Google Translate wrapper
