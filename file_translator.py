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


# ── Casing: preserve ALL-CAPS words, title-case the rest ─────────────────────

def smart_title(name):
    """
    Title-case a string but preserve words that are fully uppercase (e.g. AVC, HD, MKV).
    Also preserves parenthetical tags like (AVC) intact.
    """
    def fix_word(word):
        # Strip surrounding punctuation to inspect the core
        core = word.strip("()[]{}.,!?")
        if core.isupper() and len(core) > 1:
            return word  # preserve AVC, HD, etc.
        return word.capitalize()

    return " ".join(fix_word(w) for w in name.split())


def clean_illegal_chars(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


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


# ── Pattern inference ─────────────────────────────────────────────────────────

def infer_pattern(translated_sample, user_edited):
    """
    Compare the translated filename (no extension) against what the user
    typed they want it to look like. Returns a dict of learned rules.
    """
    rules = {
        "strip_leading_numbers": False,   # strip leading digits+separator prefix
        "strip_parentheticals": False,    # strip all (...) and [...] tags
        "strip_underscores": False,       # replace _ with space
        "serial_number": False,           # prepend serial number
        "serial_start": 1,               # starting number
        "serial_padding": 2,             # zero-pad width e.g. 2 → "01"
        "serial_separator": " ",         # separator after serial e.g. " " or ". "
    }

    t = translated_sample
    u = user_edited

    # Detect serial number added by user FIRST — so we can strip it before
    # comparing the rest of the structure.
    serial_match = re.match(r"^(\d+)([\s\.\-_]+)", u)
    t_has_long_prefix = bool(re.match(r"^\d{3,}[_\-\.\s]", t))  # 3+ digit content prefix

    if serial_match:
        serial_digits = serial_match.group(1)
        # It's a user-added serial if: translated didn't start with same digits,
        # OR translated had a long content prefix (like 8103090_)
        serial_in_translated = re.match(r"^" + re.escape(serial_digits) + r"[_\-\.\s]", t)
        if not serial_in_translated or t_has_long_prefix:
            rules["serial_number"] = True
            rules["serial_start"] = int(serial_digits)
            rules["serial_padding"] = len(serial_digits)
            rules["serial_separator"] = serial_match.group(2)
        # Strip the serial from u before further comparison
        u_stripped = u[serial_match.end():]
    else:
        u_stripped = u

    # Detect: leading number prefix removed (e.g. "8103090_Life..." → "Life...")
    if t_has_long_prefix and not re.match(r"^\d{3,}[_\-\.\s]", u_stripped):
        rules["strip_leading_numbers"] = True

    # Detect: underscores were replaced with spaces
    if "_" in t and "_" not in u_stripped:
        rules["strip_underscores"] = True

    # Detect: parenthetical tags were removed e.g. _(Avc) or (1080p)
    if re.search(r"[\(\[].*?[\)\]]", t) and not re.search(r"[\(\[].*?[\)\]]", u_stripped):
        rules["strip_parentheticals"] = True

    return rules


def describe_rules(rules):
    """Return a human-readable list of what was learned."""
    lines = []
    if rules["strip_leading_numbers"]:
        lines.append("  • Strip leading number prefix (e.g. 8103090_)")
    if rules["strip_underscores"]:
        lines.append("  • Replace underscores with spaces")
    if rules["strip_parentheticals"]:
        lines.append("  • Remove parenthetical tags e.g. (AVC), [1080p]")
    if rules["serial_number"]:
        pad = rules["serial_padding"]
        sep = repr(rules["serial_separator"])
        lines.append(f"  • Add serial number prefix (starting {str(rules['serial_start']).zfill(pad)}, separator {sep})")
    if not lines:
        lines.append("  • No structural changes — translate and title-case only")
    return lines


# ── Apply learned pattern to a single translated name ────────────────────────

def apply_pattern(translated_name, rules, serial_index=None):
    name = translated_name

    # 1. Replace underscores with spaces first (before other stripping)
    if rules["strip_underscores"]:
        name = name.replace("_", " ")

    # 2. Strip leading number prefix: digits followed by _ - . or space
    if rules["strip_leading_numbers"]:
        name = re.sub(r"^\d+[_\-\.\s]+", "", name)

    # 3. Strip parenthetical/bracket tags
    if rules["strip_parentheticals"]:
        name = re.sub(r"\s*[\(\[].*?[\)\]]", "", name)

    # 4. Clean illegal filesystem characters
    name = clean_illegal_chars(name)

    # 5. Smart title case (preserve ALL-CAPS words)
    name = smart_title(name).strip()

    # 6. Prepend serial number
    if rules["serial_number"] and serial_index is not None:
        pad = rules["serial_padding"]
        sep = rules["serial_separator"]
        number = str(serial_index).zfill(pad)
        name = f"{number}{sep}{name}"

    return name


# ── Get a sample file to show the user ───────────────────────────────────────

def get_sample_file(directory):
    """Return the first file found in the directory (non-recursive)."""
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if entry.is_file():
            return entry.name
    # Fall back to recursive if top level has no files
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            return f
    return None


# ── Core rename logic ─────────────────────────────────────────────────────────

def translate_and_rename(directory, source_lang, target_lang, rules):
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    renamed_files = 0
    renamed_folders = 0
    errors = 0

    # Collect all files per directory for serial numbering (sorted)
    file_serial_map = {}  # path → serial index
    if rules["serial_number"]:
        for root, _, files in os.walk(directory):
            sorted_files = sorted(files)
            for idx, f in enumerate(sorted_files):
                serial = rules["serial_start"] + idx
                file_serial_map[os.path.join(root, f)] = serial

    section(f"Renaming: {os.path.basename(directory)}")
    print()

    for root, dirs, files in os.walk(directory, topdown=False):

        # --- FILES ---
        for file in sorted(files):
            name, ext = os.path.splitext(file)
            old_path = os.path.join(root, file)
            try:
                translated = translator.translate(name)
                serial_idx = file_serial_map.get(old_path)
                formatted = apply_pattern(translated, rules, serial_index=serial_idx)
                new_name = f"{formatted}{ext}"
                new_path = os.path.join(root, new_name)

                # Conflict guard: append _2, _3 etc. if name already exists
                counter = 2
                while os.path.exists(new_path) and new_path != old_path:
                    new_name = f"{formatted}_{counter}{ext}"
                    new_path = os.path.join(root, new_name)
                    counter += 1

                os.rename(old_path, new_path)
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
                # Folders: apply pattern but no serial numbering
                folder_rules = {**rules, "serial_number": False}
                formatted = apply_pattern(translated, folder_rules)
                new_path = os.path.join(root, formatted)

                counter = 2
                while os.path.exists(new_path) and new_path != old_path:
                    formatted_c = f"{formatted}_{counter}"
                    new_path = os.path.join(root, formatted_c)
                    counter += 1

                os.rename(old_path, new_path)
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
        formatted = apply_pattern(translated, folder_rules)
        new_dir = os.path.join(parent, formatted)

        counter = 2
        while os.path.exists(new_dir) and new_dir != directory:
            new_dir = os.path.join(parent, f"{formatted}_{counter}")
            counter += 1

        os.rename(directory, new_dir)
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

    # ── Step 4: Translate a sample file and show user ─────────────────────────
    section("Pattern Learning")
    print()
    sample_file = get_sample_file(target_dir)

    if sample_file:
        sample_name, sample_ext = os.path.splitext(sample_file)
        print(f"  Sample file found:")
        print(f"  Original   : {sample_file}")
        print()
        print("  Translating sample...", end="", flush=True)

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_sample = translator.translate(sample_name)
            # Apply basic smart_title so user sees clean output
            translated_sample_display = smart_title(clean_illegal_chars(translated_sample))
            print(" done.\n")
            print(f"  Translated : {translated_sample_display}{sample_ext}")
        except Exception as e:
            print(f" failed ({e})\n")
            translated_sample = sample_name
            translated_sample_display = sample_name

        print()
        print("  Edit this to how you want the final filename to look.")
        print("  (Just the name — no extension needed)")
        print()
        user_edited = input(f"  Your version: ").strip()

        if not user_edited:
            # User pressed Enter — no pattern changes, use translated as-is
            user_edited = translated_sample_display
            rules = infer_pattern(translated_sample_display, user_edited)
        else:
            rules = infer_pattern(translated_sample_display, user_edited)

        # ── Step 5: Show learned rules and confirm ────────────────────────────
        print()
        divider()
        print("  Learned pattern:")
        for line in describe_rules(rules):
            print(line)
        divider()

        # If serial numbers detected, ask about ordering
        if rules["serial_number"]:
            print()
            print("  Serial numbering detected.")
            print("  [1] Number by folder sort order (alphabetical)")
            print("  [2] Number sequentially starting from your number")
            choice = input("  Choose (1/2) [default: 2]: ").strip()
            if choice == "1":
                # Will be re-computed at rename time in folder sort order
                rules["serial_order"] = "folder"
            else:
                rules["serial_order"] = "sequential"
        else:
            rules["serial_order"] = "sequential"

        print()
        go = input("  Apply this pattern to all files? (Enter / n): ").strip().lower()
        if go == "n":
            print("\n  Cancelled.\n")
            exit(0)

    else:
        print("  No files found in folder — using default pattern.")
        rules = infer_pattern("", "")
        go = input("\n  Proceed with translation only? (Enter / n): ").strip().lower()
        if go == "n":
            print("\n  Cancelled.\n")
            exit(0)

    # ── Step 6: Final summary before processing ───────────────────────────────
    print()
    divider("═")
    print(f"  Folder  : {target_dir}")
    print(f"  From    : {lang_label(source_lang)} ({source_lang})")
    print(f"  To      : {lang_label(target_lang)} ({target_lang})")
    divider("═")
    print()

    translate_and_rename(target_dir, source_lang, target_lang, rules)
    print()
