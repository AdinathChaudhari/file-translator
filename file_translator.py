import os
import re
from deep_translator import GoogleTranslator, single_detection

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


# ── Parenthetical extraction ──────────────────────────────────────────────────

# Matches tags like (AVC), [1080p], (BluRay), etc.
_TAG_RE = re.compile(r"[\(\[][^\)\]]+[\)\]]")

def extract_tags(name):
    """
    Pull all parenthetical/bracket tags out of name.
    Returns (cleaned_name, [tags_in_order]).
    The cleaned_name has the tag tokens removed but spacing normalised.
    """
    tags = _TAG_RE.findall(name)
    cleaned = _TAG_RE.sub("", name)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" _-")
    return cleaned, tags

def reinsert_tags(translated_name, tags):
    """Append the original tags back, space-separated."""
    if not tags:
        return translated_name
    return translated_name.strip() + " " + " ".join(tags)


# ── Casing ────────────────────────────────────────────────────────────────────

def smart_title(name):
    """
    Title-case each word but preserve fully-uppercase words (AVC, HD, etc.).
    Tags are already extracted before this runs, so no parenthetical logic needed.
    """
    def fix_word(word):
        core = word.strip("()[]{}.,!?-_")
        if core.isupper() and len(core) > 1:
            return word
        return word.capitalize()
    return " ".join(fix_word(w) for w in name.split())


def clean_illegal_chars(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def clean_trailing_punct(name):
    """Strip trailing dots, spaces, dashes, underscores left by translation."""
    return name.strip(". _-")


# ── Language detection ────────────────────────────────────────────────────────

def detect_language(directory):
    samples = []
    for entry in os.scandir(directory):
        name = os.path.splitext(entry.name)[0]
        if name.strip():
            samples.append(name)
        if len(samples) >= 5:
            break
    if not samples:
        return None
    try:
        return single_detection(" ".join(samples), api_key=None)
    except Exception:
        return None


# ── Pattern inference (number stripping removed) ─────────────────────────────

def infer_pattern(translated_sample, user_edited):
    """
    Compare translated filename against user's edited version.
    Infers: underscore normalisation, tag stripping, serial numbering.
    Number-prefix stripping has been removed — originals are kept as-is.
    """
    rules = {
        "strip_parentheticals": False,
        "strip_underscores": False,
        "serial_number": False,
        "serial_start": 1,
        "serial_padding": 2,
        "serial_separator": " ",
        "serial_order": "sequential",
    }

    t = translated_sample
    u = user_edited

    # Detect serial number added by user FIRST so we strip it before comparing.
    serial_match = re.match(r"^(\d+)([\s\.\-_]+)", u)
    t_has_long_prefix = bool(re.match(r"^\d{3,}[_\-\.\s]", t))

    if serial_match:
        serial_digits = serial_match.group(1)
        serial_in_translated = re.match(r"^" + re.escape(serial_digits) + r"[_\-\.\s]", t)
        if not serial_in_translated or t_has_long_prefix:
            rules["serial_number"] = True
            rules["serial_start"] = int(serial_digits)
            rules["serial_padding"] = len(serial_digits)
            rules["serial_separator"] = serial_match.group(2)
        u_stripped = u[serial_match.end():]
    else:
        u_stripped = u

    # Detect: underscores replaced with spaces
    if "_" in t and "_" not in u_stripped:
        rules["strip_underscores"] = True

    # Detect: parenthetical tags removed
    if re.search(r"[\(\[].*?[\)\]]", t) and not re.search(r"[\(\[].*?[\)\]]", u_stripped):
        rules["strip_parentheticals"] = True

    return rules


def describe_rules(rules):
    lines = []
    if rules["strip_underscores"]:
        lines.append("  • Replace underscores with spaces")
    if rules["strip_parentheticals"]:
        lines.append("  • Remove parenthetical tags — (AVC), [1080p] etc.")
    else:
        lines.append("  • Preserve parenthetical tags exactly as original")
    if rules["serial_number"]:
        pad = rules["serial_padding"]
        sep = repr(rules["serial_separator"])
        lines.append(f"  • Add serial number prefix (starting {str(rules['serial_start']).zfill(pad)}, separator {sep})")
    if not lines or lines == ["  • Preserve parenthetical tags exactly as original"]:
        lines = ["  • Translate and title-case only (tags preserved)"]
    return lines


# ── Apply pattern to a single translated name ─────────────────────────────────

def format_translated(original_name, translated_name, rules, serial_index=None):
    """
    Build the final filename stem from the translated text.
    - Tags are extracted from the ORIGINAL name so their casing is preserved.
    - The translated portion is title-cased and cleaned.
    - Tags are reinserted unless the user chose to strip them.
    """
    # Extract original tags (preserves AVC, 1080p, etc. exactly)
    _, original_tags = extract_tags(original_name)

    name = translated_name

    # 1. Normalise underscores
    if rules["strip_underscores"]:
        name = name.replace("_", " ")

    # 2. Remove tags from the translated string (Google may have translated them)
    name, _ = extract_tags(name)

    # 3. Clean illegal chars
    name = clean_illegal_chars(name)

    # 4. Smart title case
    name = smart_title(name)

    # 5. Strip trailing punctuation artifacts
    name = clean_trailing_punct(name)

    # 6. Reinsert original tags unless user said to strip them
    if not rules["strip_parentheticals"] and original_tags:
        name = reinsert_tags(name, original_tags)

    # 7. Prepend serial number
    if rules["serial_number"] and serial_index is not None:
        pad = rules["serial_padding"]
        sep = rules["serial_separator"]
        number = str(serial_index).zfill(pad)
        name = f"{number}{sep}{name}"

    return name.strip()


# ── Get a sample file ─────────────────────────────────────────────────────────

def get_sample_file(directory):
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if entry.is_file():
            return entry.name
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            return f
    return None


# ── Core rename logic ─────────────────────────────────────────────────────────

def translate_and_rename(directory, source_lang, target_lang, rules):
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    rename_log = []   # list of (new_path, original_path) for undo
    renamed_files = 0
    renamed_folders = 0
    errors = 0

    # Pre-build serial map (sorted order)
    file_serial_map = {}
    if rules["serial_number"]:
        for root, _, files in os.walk(directory):
            for idx, f in enumerate(sorted(files)):
                serial = rules["serial_start"] + idx
                file_serial_map[os.path.join(root, f)] = serial

    section(f"Renaming: {os.path.basename(directory)}")
    print()

    for root, dirs, files in os.walk(directory, topdown=False):

        # --- FILES ---
        for file in sorted(files):
            stem, ext = os.path.splitext(file)
            old_path = os.path.join(root, file)
            try:
                translated = translator.translate(stem)
                serial_idx = file_serial_map.get(old_path)
                formatted = format_translated(stem, translated, rules, serial_index=serial_idx)
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
            old_path = os.path.join(root, folder)
            try:
                translated = translator.translate(folder)
                folder_rules = {**rules, "serial_number": False}
                formatted = format_translated(folder, translated, folder_rules)
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
    parent = os.path.dirname(directory)
    top_name = os.path.basename(directory)
    try:
        translated = translator.translate(top_name)
        folder_rules = {**rules, "serial_number": False}
        formatted = format_translated(top_name, translated, folder_rules)
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
    """Reverse all renames in reverse order (deepest first → top-level last)."""
    section("Undoing Renames")
    print()
    success = 0
    failed = 0
    # Reverse so folders are restored after their contents
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

    # ── Step 2: Detect source language ───────────────────────────────────────
    print()
    print("  Detecting language...", end="", flush=True)
    detected = detect_language(target_dir)

    if detected:
        print(f" done.\n")
        print(f"  Detected : {lang_label(detected)} ({detected})")
        print()
        confirm = input("  Press Enter to confirm, or type the correct code: ").strip()
        source_lang = confirm if confirm else detected
    else:
        print(" could not detect.\n")
        source_lang = input("  Source language code (e.g. ru, fr, ja): ").strip()

    # ── Step 3: Target language ───────────────────────────────────────────────
    print()
    target_input = input("  Translate to (code) [default: en]: ").strip()
    target_lang = target_input if target_input else "en"

    # ── Step 4: Translate a sample and show user ──────────────────────────────
    section("Pattern Learning")
    print()
    sample_file = get_sample_file(target_dir)

    if sample_file:
        sample_stem, sample_ext = os.path.splitext(sample_file)
        print(f"  Original   : {sample_file}")
        print()
        print("  Translating sample...", end="", flush=True)

        try:
            translator_obj = GoogleTranslator(source=source_lang, target=target_lang)
            translated_sample_raw = translator_obj.translate(sample_stem)
            # Build display: extract tags from original, title-case translation
            _, _tags = extract_tags(sample_stem)
            _trans_clean, _ = extract_tags(translated_sample_raw)
            _trans_clean = clean_trailing_punct(smart_title(clean_illegal_chars(_trans_clean)))
            translated_sample_display = reinsert_tags(_trans_clean, _tags)
            print(" done.\n")
            print(f"  Translated : {translated_sample_display}{sample_ext}")
        except Exception as e:
            print(f" failed ({e})\n")
            translated_sample_raw = sample_stem
            translated_sample_display = sample_stem

        print()
        print("  Edit this to how you want the final filename to look.")
        print("  (Just the name — no extension needed. Press Enter to keep as-is.)")
        print()
        user_edited = input("  Your version: ").strip()

        if not user_edited:
            user_edited = translated_sample_display

        rules = infer_pattern(translated_sample_display, user_edited)

        # ── Step 5: Show learned rules ────────────────────────────────────────
        print()
        divider()
        print("  Pattern:")
        for line in describe_rules(rules):
            print(line)
        divider()

        if rules["serial_number"]:
            print()
            print("  Serial numbering detected.")
            print("  [1] Number by folder sort order (alphabetical)")
            print("  [2] Number sequentially starting from your number")
            choice = input("  Choose (1/2) [default: 2]: ").strip()
            rules["serial_order"] = "folder" if choice == "1" else "sequential"
        else:
            rules["serial_order"] = "sequential"

        print()
        go = input("  Apply this pattern to all files? (Enter / n): ").strip().lower()
        if go == "n":
            print("\n  Cancelled.\n")
            exit(0)

    else:
        print("  No files found — translating names only.")
        rules = infer_pattern("", "")
        go = input("\n  Proceed? (Enter / n): ").strip().lower()
        if go == "n":
            print("\n  Cancelled.\n")
            exit(0)

    # ── Step 6: Summary ───────────────────────────────────────────────────────
    print()
    divider("═")
    print(f"  Folder  : {target_dir}")
    print(f"  From    : {lang_label(source_lang)} ({source_lang})")
    print(f"  To      : {lang_label(target_lang)} ({target_lang})")
    divider("═")
    print()

    rename_log = translate_and_rename(target_dir, source_lang, target_lang, rules)

    # ── Step 7: Offer undo ────────────────────────────────────────────────────
    print()
    undo = input("  Undo everything and restore original names? (y / Enter to keep): ").strip().lower()
    if undo == "y":
        undo_renames(rename_log)
    else:
        print("\n  All done.\n")
