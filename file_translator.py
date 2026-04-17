import os
import re
from deep_translator import GoogleTranslator

# ── Language code → readable name ────────────────────────────────────────────
LANG_NAMES = {
    "af": "Afrikaans", "sq": "Albanian", "ar": "Arabic", "hy": "Armenian",
    "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian", "bn": "Bengali",
    "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "hr": "Croatian", "cs": "Czech",
    "da": "Danish", "nl": "Dutch", "en": "English", "eo": "Esperanto",
    "et": "Estonian", "fi": "Finnish", "fr": "French", "gl": "Galician",
    "ka": "Georgian", "de": "German", "el": "Greek", "gu": "Gujarati",
    "ht": "Haitian Creole", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian",
    "is": "Icelandic", "id": "Indonesian", "ga": "Irish", "it": "Italian",
    "ja": "Japanese", "kn": "Kannada", "kk": "Kazakh", "ko": "Korean",
    "lv": "Latvian", "lt": "Lithuanian", "mk": "Macedonian", "ms": "Malay",
    "ml": "Malayalam", "mt": "Maltese", "mr": "Marathi", "mn": "Mongolian",
    "ne": "Nepali", "no": "Norwegian", "fa": "Persian", "pl": "Polish",
    "pt": "Portuguese", "pa": "Punjabi", "ro": "Romanian", "ru": "Russian",
    "sr": "Serbian", "sk": "Slovak", "sl": "Slovenian", "es": "Spanish",
    "sw": "Swahili", "sv": "Swedish", "tl": "Filipino", "ta": "Tamil",
    "te": "Telugu", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian",
    "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese", "cy": "Welsh",
    "yi": "Yiddish",
}

def lang_label(code):
    return LANG_NAMES.get(code.lower(), code.upper())

def divider(char="─", width=56):
    print(char * width)

def section(title):
    print()
    divider()
    print(f"  {title}")
    divider()

def ask(prompt, default_yes=False):
    """Ask a yes/no question. Returns True for yes."""
    hint = "Y/n" if default_yes else "y/N"
    ans = input(f"  {prompt} [{hint}]: ").strip().lower()
    if not ans:
        return default_yes
    return ans == "y"


# ── Parenthetical tag handling ────────────────────────────────────────────────

_TAG_RE = re.compile(r"[\(\[][^\)\]]+[\)\]]")

def extract_tags(name):
    tags = _TAG_RE.findall(name)
    cleaned = _TAG_RE.sub("", name)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" _-")
    return cleaned, tags

def reinsert_tags(name, tags):
    if not tags:
        return name
    return name.strip() + " " + " ".join(tags)


# ── Casing ────────────────────────────────────────────────────────────────────

def smart_title(name):
    """
    Title-case each word. Treats hyphens and underscores as word boundaries.
    Preserves fully-uppercase words (AVC, HD, FLAC, etc.).
    """
    def cap_segment(seg):
        core = seg.strip("()[]{}.,!?")
        if core.isupper() and len(core) > 1:
            return seg
        return seg[0].upper() + seg[1:] if seg else seg

    def fix_word(word):
        parts = re.split(r"([-_])", word)
        return "".join(
            cap_segment(p) if not re.fullmatch(r"[-_]", p) else p
            for p in parts
        )

    return " ".join(fix_word(w) for w in name.split())


def clean_illegal_chars(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def clean_trailing_punct(name):
    return name.strip(". _-")


# ── File helpers ──────────────────────────────────────────────────────────────

def is_junk_file(name):
    """Skip macOS metadata files and other dot-files."""
    return name.startswith(".") or name.startswith("._")

def get_sample_file(directory):
    """Return the first non-junk file found in the directory."""
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if entry.is_file() and not is_junk_file(entry.name):
            return entry.name
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if not is_junk_file(f):
                return f
    return None


# ── Format a single translated stem ──────────────────────────────────────────

def format_translated(original_stem, translated_stem, rules, serial_index=None):
    """
    Build the final filename stem.
    - Tags extracted from original are reinserted verbatim (unless strip_tags).
    - Number prefix is stripped from original before passing to translator
      so it never appears in the output (handled in translate_and_rename).
    """
    _, original_tags = extract_tags(original_stem)

    name = translated_stem

    # Remove any tags Google may have included in the translation
    name, _ = extract_tags(name)

    # Clean illegal chars
    name = clean_illegal_chars(name)

    # Smart title case
    name = smart_title(name)

    # Strip trailing punctuation artifacts
    name = clean_trailing_punct(name)

    # Reinsert original tags unless user chose to strip them
    if not rules["strip_tags"] and original_tags:
        name = reinsert_tags(name, original_tags)

    # Prepend serial number
    if rules["serial_number"] and serial_index is not None:
        pad = rules["serial_padding"]
        sep = rules["serial_separator"]
        name = f"{str(serial_index).zfill(pad)}{sep}{name}"

    return name.strip()


# ── Core rename logic ─────────────────────────────────────────────────────────

def translate_and_rename(directory, source_lang, target_lang, rules, rename_root=True):
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    rename_log = []
    renamed_files = 0
    renamed_folders = 0
    errors = 0

    # Pre-build serial map keyed by original path (sorted, skipping junk)
    file_serial_map = {}
    if rules["serial_number"]:
        for root, _, files in os.walk(directory):
            valid = [f for f in sorted(files) if not is_junk_file(f)]
            for idx, f in enumerate(valid):
                file_serial_map[os.path.join(root, f)] = rules["serial_start"] + idx

    section(f"Renaming: {os.path.basename(directory)}")
    print()

    for root, dirs, files in os.walk(directory, topdown=False):

        # --- FILES ---
        for file in sorted(files):
            if is_junk_file(file):
                continue
            stem, ext = os.path.splitext(file)
            old_path = os.path.join(root, file)

            # Strip leading number prefix before translating if requested
            stem_to_translate = re.sub(r"^\d+[_\-\.\s]+", "", stem) if rules["strip_numbers"] else stem

            try:
                translated = translator.translate(stem_to_translate)
                serial_idx = file_serial_map.get(old_path)
                formatted = format_translated(stem_to_translate, translated, rules, serial_index=serial_idx)
                new_name = f"{formatted}{ext}"
                new_path = os.path.join(root, new_name)

                counter = 2
                while os.path.exists(new_path) and new_path != old_path:
                    new_name = f"{formatted}_{counter}{ext}"
                    new_path = os.path.join(root, new_name)
                    counter += 1

                os.rename(old_path, new_path)
                rename_log.append((new_path, old_path))
                print(f"  [FILE]   {file}")
                print(f"       →   {new_name}")
                renamed_files += 1
            except Exception as e:
                print(f"  [ERROR]  '{file}' — {e}")
                errors += 1

        # --- SUBDIRECTORIES ---
        for folder in dirs:
            if is_junk_file(folder):
                continue
            old_path = os.path.join(root, folder)
            folder_to_translate = re.sub(r"^\d+[_\-\.\s]+", "", folder) if rules["strip_numbers"] else folder
            try:
                translated = translator.translate(folder_to_translate)
                folder_rules = {**rules, "serial_number": False}
                formatted = format_translated(folder_to_translate, translated, folder_rules)
                new_path = os.path.join(root, formatted)

                counter = 2
                while os.path.exists(new_path) and new_path != old_path:
                    new_path = os.path.join(root, f"{formatted}_{counter}")
                    counter += 1

                os.rename(old_path, new_path)
                rename_log.append((new_path, old_path))
                print(f"  [FOLDER] {folder}")
                print(f"       →   {formatted}")
                renamed_folders += 1
            except Exception as e:
                print(f"  [ERROR]  '{folder}' — {e}")
                errors += 1

    # --- TOP-LEVEL FOLDER ---
    if rename_root:
        parent = os.path.dirname(directory)
        top_name = os.path.basename(directory)
        top_to_translate = re.sub(r"^\d+[_\-\.\s]+", "", top_name) if rules["strip_numbers"] else top_name
        try:
            translated = translator.translate(top_to_translate)
            folder_rules = {**rules, "serial_number": False}
            formatted = format_translated(top_to_translate, translated, folder_rules)
            new_dir = os.path.join(parent, formatted)

            counter = 2
            while os.path.exists(new_dir) and new_dir != directory:
                new_dir = os.path.join(parent, f"{formatted}_{counter}")
                counter += 1

            os.rename(directory, new_dir)
            rename_log.append((new_dir, directory))
            print(f"  [FOLDER] {top_name}")
            print(f"       →   {formatted}")
            renamed_folders += 1
        except Exception as e:
            print(f"  [ERROR]  '{top_name}' — {e}")
            errors += 1

    print()
    divider()
    print(f"  Done — {renamed_files} file(s), {renamed_folders} folder(s) renamed.", end="")
    if errors:
        print(f"  ({errors} error(s))")
    else:
        print()
    divider()

    return rename_log


# ── Undo ──────────────────────────────────────────────────────────────────────

def undo_renames(rename_log):
    section("Undoing Renames")
    print()
    success = 0
    failed = 0
    for new_path, original_path in reversed(rename_log):
        try:
            os.rename(new_path, original_path)
            print(f"  [RESTORED] {os.path.basename(new_path)}")
            print(f"         →   {os.path.basename(original_path)}")
            success += 1
        except Exception as e:
            print(f"  [ERROR]    Could not restore '{os.path.basename(new_path)}': {e}")
            failed += 1
    print()
    divider()
    print(f"  Restored {success} item(s).", end="")
    if failed:
        print(f"  ({failed} could not be restored)")
    else:
        print()
    divider()


# ── Main interactive flow ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    divider("═")
    print("    FILE & FOLDER TRANSLATOR / RENAMER  v2")
    divider("═")

    # ── Step 1: Folder path ───────────────────────────────────────────────────
    print()
    user_input = input("  Folder path: ").strip().strip('"').strip("'")
    if not os.path.isdir(user_input):
        print(f"\n  Error: '{user_input}' is not a valid folder.\n")
        exit(1)
    target_dir = user_input

    # ── Step 2: Languages (asked directly, no auto-detect) ───────────────────
    print()
    source_lang = input("  Source language code (e.g. ru, fr, ja, auto): ").strip() or "auto"
    print()
    target_lang = input("  Translate to (code) [default: en]: ").strip() or "en"

    # ── Step 3: Show sample translation ──────────────────────────────────────
    section("Sample Translation")
    print()
    sample_file = get_sample_file(target_dir)

    if sample_file:
        print(f"  Original   : {sample_file}")
        sample_stem, sample_ext = os.path.splitext(sample_file)
        print()
        print("  Translating sample...", end="", flush=True)
        try:
            _stem_clean = re.sub(r"^\d+[_\-\.\s]+", "", sample_stem)
            _, _tags = extract_tags(_stem_clean)
            _trans_raw = GoogleTranslator(source=source_lang, target=target_lang).translate(_stem_clean)
            _trans_clean, _ = extract_tags(_trans_raw)
            _trans_clean = clean_trailing_punct(smart_title(clean_illegal_chars(_trans_clean)))
            sample_translated = reinsert_tags(_trans_clean, _tags)
            print(f" done.\n")
            print(f"  Translated : {sample_translated}{sample_ext}")
        except Exception as e:
            print(f" failed ({e})")
            sample_translated = sample_stem
    else:
        print("  No files found in folder.")

    # ── Step 4: Options ───────────────────────────────────────────────────────
    section("Options")
    print()

    strip_numbers = ask("Strip leading number prefix? (e.g. 8411305_Title → Title)")
    print()
    strip_tags    = ask("Remove parenthetical tags? (e.g. (AVC), [1080p])")
    print()
    add_serial    = ask("Add serial numbers? (e.g. 01 Title, 02 Title...)")
    print()
    rename_root   = ask("Rename the top-level folder itself?", default_yes=True)

    serial_start    = 1
    serial_padding  = 2
    serial_separator = " "

    if add_serial:
        print()
        raw = input("  Start from (e.g. 01, 001, 1) [default: 01]: ").strip()
        if raw and raw.isdigit():
            serial_start   = int(raw)
            serial_padding = len(raw)
        else:
            serial_start   = 1
            serial_padding = 2
        sep_raw = input("  Separator after number (space / dot / dash) [default: space]: ").strip()
        serial_separator = {"dot": ". ", "dash": "- ", "space": " "}.get(sep_raw, " ")

    rules = {
        "strip_numbers":   strip_numbers,
        "strip_tags":      strip_tags,
        "serial_number":   add_serial,
        "serial_start":    serial_start,
        "serial_padding":  serial_padding,
        "serial_separator": serial_separator,
    }

    # ── Step 5: Confirm ───────────────────────────────────────────────────────
    print()
    divider("═")
    print(f"  Folder  : {target_dir}")
    print(f"  From    : {lang_label(source_lang)} ({source_lang})")
    print(f"  To      : {lang_label(target_lang)} ({target_lang})")
    divider()
    print(f"  Strip number prefixes  : {'yes' if strip_numbers else 'no'}")
    print(f"  Strip tags (AVC etc.)  : {'yes' if strip_tags else 'no'}")
    print(f"  Serial numbering       : {'yes, from ' + str(serial_start).zfill(serial_padding) if add_serial else 'no'}")
    print(f"  Rename top-level folder: {'yes' if rename_root else 'no'}")
    divider("═")
    print()

    go = input("  Start renaming? (Enter to proceed, n to cancel): ").strip().lower()
    if go == "n":
        print("\n  Cancelled.\n")
        exit(0)

    rename_log = translate_and_rename(target_dir, source_lang, target_lang, rules, rename_root=rename_root)

    # ── Step 6: Offer undo ────────────────────────────────────────────────────
    print()
    undo = input("  Undo everything and restore original names? (y / Enter to keep): ").strip().lower()
    if undo == "y":
        undo_renames(rename_log)
    else:
        print("\n  All done.\n")
