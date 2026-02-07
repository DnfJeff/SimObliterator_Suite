#!/usr/bin/env python3
"""obliterator.py — One CLI to rule them all.

This is the single command-line entry point for SimObliterator Suite.
Instead of importing Python modules and writing scripts, you run:

    python obliterator.py <command> <args>

It can inspect IFF game files, list FAR archives, read and edit
neighborhood save files, and generate MOOLLM character YAML.

HOW THIS FILE IS ORGANIZED:

1. COMMANDS table     — declares every available command and its arguments
2. Reference data     — PersonData indices, trait names, career tracks, etc.
3. Helpers            — load files, find characters, read traits/skills
4. Output formatters  — turn data into table/json/yaml/csv/raw text
5. Command functions  — one function per command (cmd_inspect, cmd_traits, etc.)
6. Parser builder     — reads the COMMANDS table and wires up argparse

The COMMANDS table at the top is the single source of truth for the CLI.
The parser at the bottom reads it and creates all the argument parsing
automatically. You never hand-wire argparse — add a command to the table
and it appears in the CLI.

PersonData indices verified against original Sims 1 documentation
(PersonData.h, Jamie Doornbos, 12/17/99). NOT FreeSO/TSO VM indices.
"""

# COMMANDS table — every command the CLI supports.
#
# Each entry has:
#   "group" — which category it belongs to (iff, far, save, bridge)
#   "help"  — one-line description shown in --help
#   "args"  — positional arguments (required, in order)
#   "opts"  — optional flags (--output, --type, etc.)
#
# The parser builder at the bottom of this file reads this table
# and creates all the argparse subcommands from it. When you add
# a new command here, it automatically shows up in the CLI.

COMMANDS = {
    # IFF file inspection — read any .iff file and show what's inside
    "iff-info": {
        "group": "iff",
        "help": "Show IFF file summary: chunk count, types, sizes",
        "args": [
            {"name": "file", "help": "Path to .iff file"},
        ],
    },
    "iff-chunks": {
        "group": "iff",
        "help": "List all chunks in an IFF file with type, ID, label, size",
        "args": [
            {"name": "file", "help": "Path to .iff file"},
        ],
        "opts": [
            {"flags": ["--type"], "help": "Filter by chunk type (e.g. BHAV, STR#, OBJD)"},
        ],
    },
    "iff-strings": {
        "group": "iff",
        "help": "Show all string tables (STR#/CTSS) in an IFF file",
        "args": [
            {"name": "file", "help": "Path to .iff file"},
        ],
        "opts": [
            {"flags": ["--lang"], "help": "Language index (0=US English, default: all)", "type": int},
            {"flags": ["--chunk-id"], "help": "Specific STR# chunk ID", "type": int},
        ],
    },
    "iff-objects": {
        "group": "iff",
        "help": "List all objects (OBJD) in an IFF with GUID, name, price",
        "args": [
            {"name": "file", "help": "Path to .iff file"},
        ],
    },
    "iff-bhav": {
        "group": "iff",
        "help": "List or decompile BHAV (behavior) chunks in an IFF",
        "args": [
            {"name": "file", "help": "Path to .iff file"},
        ],
        "opts": [
            {"flags": ["--id"], "help": "Decompile specific BHAV by chunk ID", "type": int},
        ],
    },

    # FAR archive operations — .far files are compressed archives holding .iff files
    "far-list": {
        "group": "far",
        "help": "List contents of a .far archive",
        "args": [
            {"name": "file", "help": "Path to .far file"},
        ],
    },
    "far-extract": {
        "group": "far",
        "help": "Extract files from a .far archive",
        "args": [
            {"name": "file", "help": "Path to .far file"},
            {"name": "output", "help": "Output directory"},
        ],
        "opts": [
            {"flags": ["--name"], "help": "Extract only this filename"},
        ],
    },

    # Neighborhood save file operations — Neighborhood.iff contains families and Sims
    "inspect": {
        "group": "save",
        "help": "List all families and characters in a neighborhood",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
        ],
    },
    "families": {
        "group": "save",
        "help": "List families with budgets and house assignments",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
        ],
    },
    "character": {
        "group": "save",
        "help": "Full character sheet: traits, skills, demographics, relationships",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name (partial match OK)"},
        ],
    },
    "traits": {
        "group": "save",
        "help": "Show personality traits with visual bars",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
    },
    "skills": {
        "group": "save",
        "help": "Show skill levels with visual bars",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
    },
    "set-trait": {
        "group": "save",
        "help": "Set a personality trait (0-10 scale, writes to file)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
            {"name": "trait", "help": "neat|outgoing|active|playful|nice|generous"},
            {"name": "value", "help": "0-10", "type": int},
        ],
    },
    "set-skill": {
        "group": "save",
        "help": "Set a skill level (0-10 scale, writes to file)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
            {"name": "skill", "help": "cooking|mechanical|charisma|logic|body|creativity|cleaning"},
            {"name": "value", "help": "0-10", "type": int},
        ],
    },
    "set-money": {
        "group": "save",
        "help": "Set a family's budget in Simoleons (writes to file)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "family_id", "help": "Family ID number", "type": int},
            {"name": "amount", "help": "Amount in Simoleons", "type": int},
        ],
    },
    "dump-raw": {
        "group": "save",
        "help": "Dump raw PersonData array with field name annotations",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
    },

    # Bridge commands — move characters between The Sims and MOOLLM
    "uplift": {
        "group": "bridge",
        "help": "Generate MOOLLM CHARACTER.yml sims: block from save data (fresh)",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
        ],
        "opts": [
            {"flags": ["-o", "--output"], "help": "Write to file instead of stdout"},
        ],
    },
    "sync": {
        "group": "bridge",
        "help": "Compare save file against existing CHARACTER.yml, emit merge events for LLM",
        "args": [
            {"name": "file", "help": "Path to Neighborhood.iff"},
            {"name": "name", "help": "Character name"},
            {"name": "character_yml", "help": "Path to existing CHARACTER.yml"},
        ],
        "opts": [
            {"flags": ["--apply"], "help": "Path to write merged sims: block",
             "default": None},
        ],
    },
}

# Every command supports these output format flags
OUTPUT_FORMATS = ["table", "json", "yaml", "csv", "raw"]
GLOBAL_OPTS = [
    {"flags": ["-f", "--format"], "choices": OUTPUT_FORMATS, "default": "table",
     "help": "Output format: table (default), json, yaml, csv, raw"},
]


# Reference data — field indices, display names, value mappings.
#
# These tables serve double duty: they define what the UI shows AND
# where to find each field in the PersonData binary array. The indices
# come from PersonData.h (the original Sims 1 header, 12/17/99).

# Personality traits live at PersonData indices 2-7.
# Each has a low-end name (e.g. "Sloppy") and high-end name (e.g. "Neat").
# Values are 0-1000 internally, displayed as 0-10.
TRAIT_INFO = {
    "nice":     {"index": 2,  "low": "Grouchy",  "high": "Nice"},
    "active":   {"index": 3,  "low": "Lazy",     "high": "Active"},
    "generous": {"index": 4,  "low": "Selfish",  "high": "Generous"},
    "playful":  {"index": 5,  "low": "Serious",  "high": "Playful"},
    "outgoing": {"index": 6,  "low": "Shy",      "high": "Outgoing"},
    "neat":     {"index": 7,  "low": "Sloppy",   "high": "Neat"},
}

# Skills live at PersonData indices 9-18. Some are hidden from the UI.
SKILL_INFO = {
    "cleaning":   {"index": 9},
    "cooking":    {"index": 10},
    "charisma":   {"index": 11},
    "mechanical": {"index": 12},
    "gardening":  {"index": 13, "hidden": True},
    "music":      {"index": 14, "hidden": True},
    "creativity": {"index": 15},
    "literacy":   {"index": 16, "hidden": True},
    "body":       {"index": 17},
    "logic":      {"index": 18},
}

# The 7 skills shown in the Sims 1 UI, in display order
VISIBLE_SKILLS = ["cooking", "mechanical", "charisma", "logic", "body", "creativity", "cleaning"]

# Career track IDs (PersonData[56])
CAREER_TRACKS = {
    0: "Unemployed", 1: "Cooking/Culinary", 2: "Entertainment",
    3: "Law Enforcement", 4: "Medicine", 5: "Military",
    6: "Politics", 7: "Pro Athlete", 8: "Science", 9: "Xtreme",
}

# Zodiac signs (PersonData[70], computed from traits)
ZODIAC_SIGNS = {
    0: "Uncomputed", 1: "Aries", 2: "Taurus", 3: "Gemini",
    4: "Cancer", 5: "Leo", 6: "Virgo", 7: "Libra",
    8: "Scorpio", 9: "Sagittarius", 10: "Capricorn",
    11: "Aquarius", 12: "Pisces",
}

# Demographic fields scattered across the PersonData array
DEMO_FIELDS = {"age": 58, "skin_color": 60, "family_number": 61,
               "gender": 65, "ghost": 68, "zodiac": 70}
CAREER_FIELDS = {"job_type": 56, "job_status": 57, "job_performance": 63}


# Implementation starts here. Everything above is data declarations
# that define the interface. Everything below is plumbing that reads
# those declarations and does the work.

import sys
import json
import csv
import io
import argparse
from pathlib import Path
from typing import Any, Optional

# Add SimObliterator's src/ to the Python import path so we can
# import its format parsers and save editor modules
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


# Lazy imports — each function below only loads the SimObliterator
# modules it actually needs. This keeps startup fast: if you're just
# listing FAR archives, you don't load the save editor, and vice versa.

def _save_manager():
    """Import the save file editing module (only when needed)."""
    from Tools.save_editor.save_manager import SaveManager, PersonData
    return SaveManager, PersonData

def _iff_file():
    """Import the IFF file reader (only when needed)."""
    from formats.iff.iff_file import IffFile
    return IffFile

def _far1():
    """Import the FAR v1 archive reader (only when needed)."""
    from formats.far.far1 import FAR1Archive
    return FAR1Archive

def _far3():
    """Import the FAR v3 archive reader (only when needed)."""
    from formats.far.far3 import FAR3Archive
    return FAR3Archive

def _bhav_decompiler():
    """Import the BHAV bytecode decompiler (only when needed)."""
    from formats.iff.chunks.bhav_decompiler import BHAVDecompiler
    return BHAVDecompiler


# Helpers for save file operations

def _load_save(path):
    """Load a Neighborhood.iff save file via SaveManager. Exits on failure."""
    SaveManager, _ = _save_manager()
    mgr = SaveManager(path)
    if not mgr.load():
        print(f"ERROR: Failed to load {path}", file=sys.stderr)
        sys.exit(1)
    return mgr

def _find(mgr, name):
    """Find a Sim by name in the loaded neighborhood.

    Matches case-insensitively and allows partial matches.
    If "Bob" matches "Bob Newbie", that's a hit.
    If multiple Sims match, tries for an exact match first.
    Exits with an error if no match or ambiguous.
    """
    lo = name.lower()
    hits = [(nid, n) for nid, n in mgr.neighbors.items() if lo in n.name.lower()]
    if not hits:
        avail = sorted(n.name for n in mgr.neighbors.values() if n.name)
        print(f"ERROR: No match for '{name}'. Available: {', '.join(avail)}", file=sys.stderr)
        sys.exit(1)
    if len(hits) > 1:
        exact = [(nid, n) for nid, n in hits if n.name.lower() == lo]
        if len(exact) == 1:
            return exact[0]
        print(f"ERROR: Ambiguous '{name}':", file=sys.stderr)
        for nid, n in hits:
            print(f"  [{nid}] {n.name}", file=sys.stderr)
        sys.exit(1)
    return hits[0]

def _pd(data, idx):
    """Read one value from a PersonData array, safely. Returns None if out of bounds."""
    if data and 0 <= idx < len(data):
        return data[idx]
    return None

def _bar(v, w=10):
    """Render a visual bar like [████████░░] for a value 0-10."""
    v = max(0, min(v, w))
    return "\u2588" * v + "\u2591" * (w - v)

def _read_traits(pd):
    """Extract personality traits from a PersonData array.

    Returns a dict like {"neat": {"raw": 700, "display": 7, "low": "Sloppy", "high": "Neat"}}.
    The raw value is 0-1000 (as stored in the binary). Display is 0-10.
    """
    return {n: {"raw": r, "display": round(r/100), "low": i["low"], "high": i["high"]}
            for n, i in TRAIT_INFO.items() if (r := _pd(pd, i["index"])) is not None}

def _read_skills(pd, hidden=False):
    """Extract skills from a PersonData array.

    Returns a dict like {"cooking": {"raw": 300, "display": 3}}.
    Hidden skills (gardening, music, literacy) are excluded unless hidden=True.
    """
    return {n: {"raw": r, "display": round(r/100)}
            for n, i in SKILL_INFO.items()
            if (hidden or not i.get("hidden")) and (r := _pd(pd, i["index"])) is not None}

def _read_demo(pd):
    """Extract demographic fields (age, gender, career, zodiac, etc.) from PersonData.

    Returns a dict with human-readable string values.
    """
    age = _pd(pd, DEMO_FIELDS["age"])
    gen = _pd(pd, DEMO_FIELDS["gender"])
    skin = _pd(pd, DEMO_FIELDS["skin_color"])
    zod = _pd(pd, DEMO_FIELDS["zodiac"])
    jt = _pd(pd, CAREER_FIELDS["job_type"])
    jp = _pd(pd, CAREER_FIELDS["job_performance"])
    return {
        "age": {0:"child",1:"adult"}.get(age, str(age)),
        "gender": {0:"male",1:"female"}.get(gen, str(gen)),
        "skin_color": {0:"light",1:"medium",2:"dark"}.get(skin, str(skin)),
        "zodiac": ZODIAC_SIGNS.get(zod, f"unknown({zod})"),
        "career": CAREER_TRACKS.get(jt, f"unknown({jt})"),
        "job_performance": jp,
    }


# Output formatters — turn data into the requested format.
#
# Commands return Python dicts/lists. These functions render them
# as text. The -f/--format flag chooses which one to use.
# "table" is the default human-readable format.
# "json" is for machine consumption or piping to other tools.
# "yaml" is MOOLLM-compatible.
# "csv" is for spreadsheets.
# "raw" is key=value pairs, grep-friendly.

def _emit(data, fmt, headers=None):
    """Dispatch to the right formatter based on the --format flag."""
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "yaml":
        _emit_yaml(data)
    elif fmt == "csv":
        _emit_csv(data, headers)
    elif fmt == "raw":
        _emit_raw(data)
    elif fmt == "table":
        if isinstance(data, str):
            print(data)
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            _emit_table(data, headers)
        else:
            print(data)

def _emit_yaml(d, indent=0):
    """Print data as YAML. Simple recursive emitter, no pyyaml dependency."""
    p = "  " * indent
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                print(f"{p}{k}:")
                _emit_yaml(v, indent+1)
            else:
                print(f"{p}{k}: {v}")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    print(f"{p}{'- ' if first else '  '}{k}: {v}")
                    first = False
            else:
                print(f"{p}- {item}")
    else:
        print(f"{p}{d}")

def _emit_csv(data, headers=None):
    """Print data as CSV."""
    buf = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = headers or list(data[0].keys())
        w = csv.DictWriter(buf, fieldnames=keys)
        w.writeheader()
        for row in data:
            w.writerow({k: row.get(k,"") for k in keys})
    elif isinstance(data, dict):
        w = csv.writer(buf)
        for k, v in data.items():
            w.writerow([k, v])
    print(buf.getvalue().rstrip())

def _emit_raw(data):
    """Print data as key=value pairs, one per line. Good for grep."""
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print(f"{k}.{k2}={v2}")
            else:
                print(f"{k}={v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                print("\t".join(str(v) for v in item.values()))
            else:
                print(item)
    else:
        print(data)

def _emit_table(rows, headers=None):
    """Print a list of dicts as an aligned text table with column headers."""
    if not rows:
        return
    keys = headers or list(rows[0].keys())
    widths = {k: max(len(str(k)), max((len(str(r.get(k,""))) for r in rows), default=0)) for k in keys}
    print("  ".join(str(k).ljust(widths[k]) for k in keys))
    print("  ".join("-"*widths[k] for k in keys))
    for row in rows:
        print("  ".join(str(row.get(k,"")).ljust(widths[k]) for k in keys))


# Command functions — one per CLI command.
#
# Each function is named cmd_<command> where <command> matches the
# COMMANDS table key (with dashes replaced by underscores).
# They receive the parsed argparse args and do the work.

def cmd_iff_info(args):
    """Show a summary of an IFF file: how many chunks, what types."""
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    types = {}
    for c in iff.chunks:
        t = c.type_code if hasattr(c, 'type_code') else type(c).__name__
        types[t] = types.get(t, 0) + 1
    data = {"file": args.file, "chunks": len(iff.chunks), "types": types}
    if args.format == "table":
        print(f"IFF: {args.file}")
        print(f"Chunks: {len(iff.chunks)}")
        print(f"\nType    Count")
        print(f"----    -----")
        for t, c in sorted(types.items(), key=lambda x: -x[1]):
            print(f"{t:<8} {c}")
    else:
        _emit(data, args.format)

def cmd_iff_chunks(args):
    """List every chunk in an IFF file. Optionally filter by type."""
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    rows = []
    for c in iff.chunks:
        t = c.type_code if hasattr(c, 'type_code') else type(c).__name__
        if args.type and t != args.type:
            continue
        rows.append({
            "type": t, "id": c.chunk_id,
            "label": getattr(c, 'chunk_label', ''),
            "size": getattr(c, 'chunk_size', 0),
        })
    _emit(rows, args.format, ["type", "id", "label", "size"])

def cmd_iff_strings(args):
    """Show string tables in an IFF file. Strings are how objects get their names,
    descriptions, and menu text. Each string has up to 20 language translations."""
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    from formats.iff.chunks.str_ import STR, CTSS
    results = []
    for chunk in iff.chunks:
        if not isinstance(chunk, (STR, CTSS)):
            continue
        if args.chunk_id is not None and chunk.chunk_id != args.chunk_id:
            continue
        for idx, lang_set in enumerate(chunk.strings):
            for lang_code, entry in lang_set.languages.items():
                if args.lang is not None and lang_code != args.lang:
                    continue
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "chunk_type": chunk.type_code if hasattr(chunk, 'type_code') else type(chunk).__name__,
                    "index": idx, "lang": lang_code, "text": entry.value,
                })
    _emit(results, args.format, ["chunk_id", "chunk_type", "index", "lang", "text"])

def cmd_iff_objects(args):
    """List all object definitions (OBJD chunks) in an IFF file.
    Shows GUID, name, type, and catalog price."""
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    from formats.iff.chunks.objd import OBJD
    rows = []
    for c in iff.chunks:
        if not isinstance(c, OBJD):
            continue
        rows.append({
            "id": c.chunk_id,
            "guid": f"0x{c.guid:08X}" if c.guid else "0x00000000",
            "label": getattr(c, 'chunk_label', ''),
            "type": str(c.object_type) if hasattr(c, 'object_type') else "",
            "price": c.price if hasattr(c, 'price') else 0,
        })
    _emit(rows, args.format, ["id", "guid", "label", "type", "price"])

def cmd_iff_bhav(args):
    """List all behavior scripts (BHAV chunks) in an IFF file.
    With --id, shows the individual instructions of one specific BHAV."""
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    from formats.iff.chunks.bhav import BHAV
    if args.id is not None:
        for c in iff.chunks:
            if isinstance(c, BHAV) and c.chunk_id == args.id:
                print(f"BHAV #{c.chunk_id}: {getattr(c, 'chunk_label', '')}")
                print(f"Instructions: {len(c.instructions)}")
                for i, inst in enumerate(c.instructions):
                    opcode = inst.opcode if hasattr(inst, 'opcode') else 0
                    true_t = inst.true_target if hasattr(inst, 'true_target') else 0
                    false_t = inst.false_target if hasattr(inst, 'false_target') else 0
                    print(f"  [{i:>3}] opcode=0x{opcode:04X}  T->{true_t}  F->{false_t}")
                return
        print(f"ERROR: BHAV #{args.id} not found", file=sys.stderr)
        sys.exit(1)
    rows = []
    for c in iff.chunks:
        if not isinstance(c, BHAV):
            continue
        rows.append({
            "id": c.chunk_id,
            "label": getattr(c, 'chunk_label', ''),
            "instructions": len(c.instructions),
        })
    _emit(rows, args.format, ["id", "label", "instructions"])


def cmd_far_list(args):
    """List every file inside a .far archive (The Sims' compressed archive format)."""
    try:
        FAR1Archive = _far1()
        arc = FAR1Archive(args.file)
        rows = [{"index": i, "name": e.filename, "size": e.file_size1}
                for i, e in enumerate(arc.entries)]
        if args.format == "table":
            print(f"FAR Archive: {args.file} ({len(rows)} files)")
        _emit(rows, args.format, ["index", "name", "size"])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_far_extract(args):
    """Extract files from a .far archive to a directory."""
    try:
        FAR1Archive = _far1()
        arc = FAR1Archive(args.file)
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        if args.name:
            data = arc.get_entry(args.name)
            if data is None:
                print(f"ERROR: '{args.name}' not found in archive", file=sys.stderr)
                sys.exit(1)
            (out / args.name).write_bytes(data)
            print(f"Extracted: {args.name} ({len(data)} bytes)")
        else:
            arc.extract_all(str(out))
            print(f"Extracted {len(arc.entries)} files to {out}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_inspect(args):
    """List all families and all characters in a neighborhood save file.
    This is the starting point: see who lives here."""
    mgr = _load_save(args.file)
    families = [{"id": fid, "house": f.house_number, "budget": f.budget,
                 "members": f.num_members, "status": "townie" if f.is_townie else "resident"}
                for fid, f in sorted(mgr.families.items())]
    characters = []
    for nid, n in sorted(mgr.neighbors.items()):
        tr = _read_traits(n.person_data) if n.person_data else {}
        ts = " ".join(f"{k[0].upper()}{v['display']}" for k,v in tr.items()
                      if k in ["neat","outgoing","active","playful","nice"])
        characters.append({"id": nid, "name": n.name, "traits": ts})
    if args.format == "table":
        print(f"Neighborhood: {args.file}")
        print(f"Families: {len(families)}  |  Characters: {len(characters)}\n")
        if families:
            print("FAMILIES")
            _emit_table(families, ["id","house","budget","members","status"])
        if characters:
            print("\nCHARACTERS")
            _emit_table(characters, ["id","name","traits"])
    else:
        _emit({"families": families, "characters": characters}, args.format)

def cmd_families(args):
    """List families with their house numbers, budgets, and member counts."""
    mgr = _load_save(args.file)
    rows = [{"id": fid, "house": f.house_number, "budget": f.budget,
             "members": f.num_members, "status": "townie" if f.is_townie else "resident"}
            for fid, f in sorted(mgr.families.items())]
    _emit(rows, args.format, ["id","house","budget","members","status"])

def cmd_character(args):
    """Show a full character sheet for one Sim: traits, skills, demographics,
    and relationships. The name can be a partial match ('Bob' finds 'Bob Newbie')."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: {n.name} has no person_data", file=sys.stderr)
        sys.exit(1)
    tr = _read_traits(n.person_data)
    sk = _read_skills(n.person_data)
    dm = _read_demo(n.person_data)
    data = {"name": n.name, "neighbor_id": nid, "demographics": dm,
            "traits": {k:v["display"] for k,v in tr.items()},
            "traits_raw": {k:v["raw"] for k,v in tr.items()},
            "skills": {k:v["display"] for k,v in sk.items()},
            "skills_raw": {k:v["raw"] for k,v in sk.items()},
            "relationships": {str(k):v for k,v in n.relationships.items()}}
    if args.format == "table":
        print(f"  {n.name}  (neighbor #{nid})")
        print(f"\n  {dm['age']}  |  {dm['gender']}  |  {dm['zodiac']}  |  {dm['career']}")
        print(f"\n  PERSONALITY")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr:
                v = tr[t]
                print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}")
        print(f"\n  SKILLS")
        for s in VISIBLE_SKILLS:
            if s in sk:
                v = sk[s]
                print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}")
        if n.relationships:
            print(f"\n  RELATIONSHIPS")
            for rid, rv in list(n.relationships.items())[:10]:
                d = rv[0] if len(rv)>0 else "?"
                l = rv[1] if len(rv)>1 else "?"
                print(f"  Neighbor {rid}: daily={d}, lifetime={l}")
    else:
        _emit(data, args.format)

def cmd_traits(args):
    """Show personality traits for one Sim with visual bars and raw values."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: no person_data", file=sys.stderr)
        sys.exit(1)
    tr = _read_traits(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Personality")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr:
                v = tr[t]
                print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}  (raw {v['raw']})")
    else:
        _emit({"name": n.name, "traits": {k:v["display"] for k,v in tr.items()}}, args.format)

def cmd_skills(args):
    """Show skill levels for one Sim with visual bars and raw values."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: no person_data", file=sys.stderr)
        sys.exit(1)
    sk = _read_skills(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Skills")
        for s in VISIBLE_SKILLS:
            if s in sk:
                v = sk[s]
                print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}  (raw {v['raw']})")
    else:
        _emit({"name": n.name, "skills": {k:v["display"] for k,v in sk.items()}}, args.format)

def cmd_set_trait(args):
    """Write a new personality trait value to the save file. Scale is 0-10."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_personality(nid, args.trait, raw):
        mgr.save()
        print(f"Saved. {n.name} {args.trait} = {args.value}")
    else:
        sys.exit(1)

def cmd_set_skill(args):
    """Write a new skill level to the save file. Scale is 0-10."""
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_skill(nid, args.skill, raw):
        mgr.save()
        print(f"Saved. {n.name} {args.skill} = {args.value}")
    else:
        sys.exit(1)

def cmd_set_money(args):
    """Write a new family budget to the save file."""
    mgr = _load_save(args.file)
    if mgr.set_family_money(args.family_id, args.amount):
        mgr.save()
        print(f"Saved. Family {args.family_id} = \u00a7{args.amount:,}")
    else:
        sys.exit(1)

def cmd_dump_raw(args):
    """Dump the entire PersonData array for one Sim.

    Shows all 80+ field indices with their values and known field names.
    Nonzero values are marked with * so you can spot the interesting ones.
    Useful for debugging and verifying the field indices are correct.
    """
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: no person_data", file=sys.stderr)
        sys.exit(1)
    # Build a lookup of index -> field name from our reference tables
    known = {}
    for name, info in TRAIT_INFO.items():
        known[info["index"]] = f"personality.{name}"
    for name, info in SKILL_INFO.items():
        known[info["index"]] = f"skill.{name}"
    for name, idx in DEMO_FIELDS.items():
        known[idx] = f"demo.{name}"
    for name, idx in CAREER_FIELDS.items():
        known[idx] = f"career.{name}"
    known.update({0:"idle_state", 1:"npc_fee_amount", 8:"current_outfit"})
    rows = [{"index":i, "value":v, "field":known.get(i,""), "nz":"*" if v!=0 else ""}
            for i,v in enumerate(n.person_data)]
    if args.format == "table":
        print(f"PersonData for {n.name} ({len(n.person_data)} fields)")
        for r in rows:
            print(f"  [{r['index']:>3}] {r['value']:>6}{r['nz']:>2}  {r['field']}")
    else:
        _emit(rows, args.format, ["index","value","field"])


def cmd_uplift(args):
    """Generate a MOOLLM-compatible sims: YAML block from a Sim's save data.

    This is a fresh extraction — it reads the binary save file and produces
    YAML that can go directly into a CHARACTER.yml file. If the character
    already has a CHARACTER.yml and you want to merge instead of replace,
    use the 'sync' command instead.
    """
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: no person_data", file=sys.stderr)
        sys.exit(1)
    tr = _read_traits(n.person_data)
    sk = _read_skills(n.person_data)
    dm = _read_demo(n.person_data)
    lines = [f"# {n.name} — Uplifted from Sims 1 save data",
             f"# Neighbor ID: {nid}  |  Source: {args.file}", "", "sims:", "  traits:"]
    for t in ["neat","outgoing","active","playful","nice","generous"]:
        if t in tr:
            v = tr[t]
            lines.append(f"    {t}: {v['display']:<3}  # {v['low']} {v['display']}/10 {v['high']}")
    lines.append("  skills:")
    for s in VISIBLE_SKILLS:
        if s in sk:
            lines.append(f"    {s}: {sk[s]['display']}")
    lines += ["  career:", f"    track: {dm['career'].lower().replace('/','_')}",
              f"    performance: {dm['job_performance']}",
              "  identity:", f"    age: {dm['age']}", f"    gender: {dm['gender']}",
              f"    zodiac: {dm['zodiac'].lower()}", f"    skin_color: {dm['skin_color']}"]
    out = "\n".join(lines) + "\n"
    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out)
        print(f"Wrote {p}")
    else:
        print(out, end="")


def cmd_sync(args):
    """Compare a save file against an existing CHARACTER.yml and emit merge events.

    Instead of replacing the YAML wholesale, sync diffs both sources field by
    field and emits structured events telling the LLM what changed:

      TRAIT_MATCH      — values agree, no action needed
      TRAIT_DRIFT      — values differ, LLM decides how to merge
      SKILL_GAINED     — Sim learned in The Sims, update + add memory
      SKILL_LOST       — unusual decrease, investigate
      CAREER_CHANGE    — switched tracks
      RELATIONSHIP_NEW — met someone new in The Sims
      NARRATIVE_STALE  — enough changed that the prose needs revision

    The LLM reads these events, makes merge decisions, updates the YAML,
    and can re-run sync to verify convergence. Iterate until clean.
    """
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: {n.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    save_traits = _read_traits(n.person_data)
    save_skills = _read_skills(n.person_data)
    save_demo = _read_demo(n.person_data)

    yml_path = Path(args.character_yml)
    if not yml_path.is_file():
        _emit([{"type": "NEW_CHARACTER", "severity": "action",
                "message": f"No existing CHARACTER.yml at {yml_path}. Full uplift needed.",
                "suggestion": f"Run: obliterator uplift {args.file} '{args.name}' -o {yml_path}"}],
              args.format)
        return

    yml_traits, yml_skills, yml_demo, yml_rels = _parse_character_yml(yml_path.read_text())
    events = []
    trait_drift_count = 0

    # Compare traits
    for t in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
        sv = save_traits.get(t, {}).get("display")
        yv = yml_traits.get(t)
        if sv is None:
            continue
        if yv is None:
            events.append({"type": "TRAIT_DRIFT", "severity": "info",
                           "field": t, "save": sv, "yaml": None,
                           "message": f"{t}: save={sv}, YAML missing"})
            trait_drift_count += 1
        elif sv != yv:
            delta = sv - yv
            events.append({"type": "TRAIT_DRIFT", "severity": "warning",
                           "field": t, "save": sv, "yaml": yv, "delta": delta,
                           "message": f"{t}: save={sv} vs yaml={yv} ({'higher' if delta>0 else 'lower'} by {abs(delta)})",
                           "suggestion": f"Update sims.traits.{t} to {sv}, or keep {yv} if MOOLLM changes intentional"})
            trait_drift_count += 1
        else:
            events.append({"type": "TRAIT_MATCH", "severity": "ok",
                           "field": t, "value": sv, "message": f"{t}: {sv} (matches)"})

    # Compare skills
    for s in VISIBLE_SKILLS:
        sv = save_skills.get(s, {}).get("display")
        yv = yml_skills.get(s)
        if sv is None:
            continue
        if yv is None or sv > (yv or 0):
            events.append({"type": "SKILL_GAINED", "severity": "info",
                           "field": s, "save": sv, "yaml": yv or 0,
                           "message": f"{s}: {yv or 0} -> {sv} (+{sv - (yv or 0)})",
                           "suggestion": f"Sim gained {s}. Update and add a memory."})
        elif sv < yv:
            events.append({"type": "SKILL_LOST", "severity": "warning",
                           "field": s, "save": sv, "yaml": yv,
                           "message": f"{s}: {yv} -> {sv} (decreased)",
                           "suggestion": "Unusual. Check if save is older."})
        else:
            events.append({"type": "SKILL_MATCH", "severity": "ok",
                           "field": s, "value": sv, "message": f"{s}: {sv} (matches)"})

    # Compare career
    sc = save_demo.get("career", "Unemployed")
    yc = yml_demo.get("career")
    if yc and sc.lower() != yc.lower():
        events.append({"type": "CAREER_CHANGE", "severity": "warning",
                       "save": sc, "yaml": yc,
                       "message": f"Career: {yc} -> {sc}",
                       "suggestion": "Update career track and add a memory."})

    # Compare demographics
    for field in ["age", "gender", "zodiac"]:
        sv = save_demo.get(field)
        yv = yml_demo.get(field)
        if yv and sv and str(sv).lower() != str(yv).lower():
            events.append({"type": "DEMOGRAPHIC_DRIFT", "severity": "warning",
                           "field": field, "save": sv, "yaml": yv,
                           "message": f"{field}: {yv} -> {sv}"})

    # New relationships
    for rel_id, rel_vals in n.relationships.items():
        daily = rel_vals[0] if len(rel_vals) > 0 else 0
        lifetime = rel_vals[1] if len(rel_vals) > 1 else 0
        if str(rel_id) not in yml_rels:
            events.append({"type": "RELATIONSHIP_NEW", "severity": "info",
                           "target_id": rel_id, "daily": daily, "lifetime": lifetime,
                           "message": f"New relationship with neighbor {rel_id}: daily={daily}, lifetime={lifetime}",
                           "suggestion": "LLM should generate a narrative from the scores."})

    # Narrative staleness
    if trait_drift_count >= 2:
        events.append({"type": "NARRATIVE_STALE", "severity": "action",
                       "drift_count": trait_drift_count,
                       "message": f"{trait_drift_count} traits drifted. soul_philosophy may need revision.",
                       "suggestion": "LLM should re-read traits and revise the character's voice."})

    events.append({"type": "NEEDS_NOTE", "severity": "info",
                   "message": "Motives are runtime state, not in save file. Update needs based on narrative."})

    # Output
    actions = sum(1 for e in events if e["severity"] == "action")
    warnings = sum(1 for e in events if e["severity"] == "warning")
    infos = sum(1 for e in events if e["severity"] == "info")
    oks = sum(1 for e in events if e["severity"] == "ok")

    if args.format == "table":
        print(f"SYNC: {n.name}")
        print(f"Save: {args.file}  |  YAML: {args.character_yml}")
        print(f"Events: {len(events)} ({actions} actions, {warnings} warnings, {infos} info, {oks} ok)\n")
        for e in events:
            icon = {"ok": "  ", "info": "->", "warning": "!!", "action": ">>"}
            print(f"  {icon.get(e['severity'], '  ')} [{e['type']}] {e['message']}")
            if "suggestion" in e:
                print(f"     {e['suggestion']}")
    else:
        _emit({"name": n.name, "save_file": args.file,
               "character_yml": args.character_yml,
               "summary": {"actions": actions, "warnings": warnings, "info": infos, "ok": oks},
               "events": events}, args.format)


def _parse_character_yml(text):
    """Read trait/skill/demographic values from a CHARACTER.yml file.

    This is a minimal YAML parser — just enough to extract the sims: block
    fields for comparison. It doesn't need pyyaml because CHARACTER.yml
    uses a predictable subset of YAML.

    Returns (traits_dict, skills_dict, demographics_dict, relationships_dict).
    """
    traits = {}
    skills = {}
    demo = {}
    rels = {}
    section = None
    subsection = None

    for line in text.split("\n"):
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())

        if indent <= 2 and "sims:" in stripped:
            section = "sims"; continue
        if indent <= 2 and "relationships:" in stripped and section != "sims":
            section = "relationships"; continue
        if stripped.endswith(":") and indent == 0:
            section = None; continue

        if section == "sims":
            if "traits:" in stripped and indent <= 4:
                subsection = "traits"; continue
            elif "skills:" in stripped and indent <= 4:
                subsection = "skills"; continue
            elif "career:" in stripped and indent <= 4:
                subsection = "career"; continue
            elif "identity:" in stripped and indent <= 4:
                subsection = "identity"; continue
            elif stripped.endswith(":") and indent <= 4:
                subsection = None; continue

            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if not val:
                    continue
                try:
                    num = int(val)
                except ValueError:
                    num = None

                if subsection == "traits" and num is not None:
                    traits[key] = num
                elif subsection == "skills" and num is not None:
                    skills[key] = num
                elif subsection == "career":
                    if key == "track": demo["career"] = val
                elif subsection == "identity":
                    demo[key] = val

    return traits, skills, demo, rels


# Parser builder — reads the COMMANDS table and creates argparse subcommands.
#
# This is the glue between the data table at the top and Python's argparse
# library. For each entry in COMMANDS, it creates a subcommand with the
# specified arguments and options. It also looks up the matching cmd_*
# function to call when that command is invoked.
#
# This means you never write argparse code by hand. You add a command to
# the COMMANDS dict, write a cmd_* function, and it just works.

def build_parser():
    """Build the argparse parser from the COMMANDS table."""
    parser = argparse.ArgumentParser(
        prog="obliterator",
        description="One CLI to rule The Sims 1 files. "
                    "IFF inspection, FAR archives, save editing, character uplift.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Formats: table json yaml csv raw\n"
               "PersonData verified against Sims 1 docs.",
    )
    for opt in GLOBAL_OPTS:
        parser.add_argument(*opt["flags"], choices=opt.get("choices"),
                            default=opt.get("default"), help=opt["help"])

    sub = parser.add_subparsers(dest="command")
    dispatch = {}

    for cmd_name, spec in COMMANDS.items():
        p = sub.add_parser(cmd_name, help=spec["help"])
        for a in spec.get("args", []):
            kw = {"help": a["help"]}
            if "type" in a:
                kw["type"] = a["type"]
            p.add_argument(a["name"], **kw)
        for o in spec.get("opts", []):
            kw = {"help": o["help"]}
            if "type" in o: kw["type"] = o["type"]
            if "choices" in o: kw["choices"] = o["choices"]
            if "default" in o: kw["default"] = o["default"]
            p.add_argument(*o["flags"], **kw)
        # cmd_name "iff-info" maps to function cmd_iff_info
        fn_name = "cmd_" + cmd_name.replace("-", "_")
        dispatch[cmd_name] = globals().get(fn_name)

    return parser, dispatch


def main():
    """Parse command line arguments and run the requested command."""
    parser, dispatch = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
