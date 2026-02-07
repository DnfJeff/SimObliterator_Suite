#!/usr/bin/env python3
"""obliterator.py — One CLI to rule them all.

Sniffable Python: the COMMANDS table below IS the interface.
Read it and you know everything. Single source of truth.
The argparse parser is BUILT FROM this table. They cannot drift.

PersonData indices verified against original Sims 1 documentation
(PersonData.h, Jamie Doornbos, 12/17/99). NOT FreeSO/TSO VM indices.
"""

# COMMANDS — The single source of truth.
# Read this table: you know every command, arg, output format.
# Implementation below is driven by it. Never hand-wire argparse.

COMMANDS = {
    # --- IFF FILE INSPECTION ---
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

    # --- FAR ARCHIVE OPERATIONS ---
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

    # --- NEIGHBORHOOD / SAVE EDITING ---
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

    # --- UPLIFT / DOWNLOAD / SYNC ---
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

# Output formats available for all commands
OUTPUT_FORMATS = ["table", "json", "yaml", "csv", "raw"]

# Global options for every command
GLOBAL_OPTS = [
    {"flags": ["-f", "--format"], "choices": OUTPUT_FORMATS, "default": "table",
     "help": "Output format: table (default), json, yaml, csv, raw"},
]

# REFERENCE DATA — PersonData layout, trait poles, career tracks.

TRAIT_INFO = {
    "nice":     {"index": 2,  "low": "Grouchy",  "high": "Nice"},
    "active":   {"index": 3,  "low": "Lazy",     "high": "Active"},
    "generous": {"index": 4,  "low": "Selfish",  "high": "Generous"},
    "playful":  {"index": 5,  "low": "Serious",  "high": "Playful"},
    "outgoing": {"index": 6,  "low": "Shy",      "high": "Outgoing"},
    "neat":     {"index": 7,  "low": "Sloppy",   "high": "Neat"},
}

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

VISIBLE_SKILLS = ["cooking", "mechanical", "charisma", "logic", "body", "creativity", "cleaning"]

CAREER_TRACKS = {
    0: "Unemployed", 1: "Cooking/Culinary", 2: "Entertainment",
    3: "Law Enforcement", 4: "Medicine", 5: "Military",
    6: "Politics", 7: "Pro Athlete", 8: "Science", 9: "Xtreme",
}

ZODIAC_SIGNS = {
    0: "Uncomputed", 1: "Aries", 2: "Taurus", 3: "Gemini",
    4: "Cancer", 5: "Leo", 6: "Virgo", 7: "Libra",
    8: "Scorpio", 9: "Sagittarius", 10: "Capricorn",
    11: "Aquarius", 12: "Pisces",
}

DEMO_FIELDS = {"age": 58, "skin_color": 60, "family_number": 61,
               "gender": 65, "ghost": 68, "zodiac": 70}
CAREER_FIELDS = {"job_type": 56, "job_status": 57, "job_performance": 63}


# IMPLEMENTATION — Driven by the tables above.

import sys
import json
import csv
import io
import argparse
from pathlib import Path
from typing import Any, Optional

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


# Lazy imports: only load what each command needs

def _save_manager():
    from Tools.save_editor.save_manager import SaveManager, PersonData
    return SaveManager, PersonData

def _iff_file():
    from formats.iff.iff_file import IffFile
    return IffFile

def _far1():
    from formats.far.far1 import FAR1Archive
    return FAR1Archive

def _far3():
    from formats.far.far3 import FAR3Archive
    return FAR3Archive

def _bhav_decompiler():
    from formats.iff.chunks.bhav_decompiler import BHAVDecompiler
    return BHAVDecompiler


# Helpers

def _load_save(path):
    SaveManager, _ = _save_manager()
    mgr = SaveManager(path)
    if not mgr.load():
        print(f"ERROR: Failed to load {path}", file=sys.stderr); sys.exit(1)
    return mgr

def _find(mgr, name):
    lo = name.lower()
    hits = [(nid, n) for nid, n in mgr.neighbors.items() if lo in n.name.lower()]
    if not hits:
        avail = sorted(n.name for n in mgr.neighbors.values() if n.name)
        print(f"ERROR: No match for '{name}'. Available: {', '.join(avail)}", file=sys.stderr); sys.exit(1)
    if len(hits) > 1:
        exact = [(nid, n) for nid, n in hits if n.name.lower() == lo]
        if len(exact) == 1: return exact[0]
        print(f"ERROR: Ambiguous '{name}':", file=sys.stderr)
        for nid, n in hits: print(f"  [{nid}] {n.name}", file=sys.stderr)
        sys.exit(1)
    return hits[0]

def _pd(data, idx):
    if data and 0 <= idx < len(data): return data[idx]
    return None

def _bar(v, w=10):
    v = max(0, min(v, w)); return "\u2588" * v + "\u2591" * (w - v)

def _read_traits(pd):
    return {n: {"raw": r, "display": round(r/100), "low": i["low"], "high": i["high"]}
            for n, i in TRAIT_INFO.items() if (r := _pd(pd, i["index"])) is not None}

def _read_skills(pd, hidden=False):
    return {n: {"raw": r, "display": round(r/100)}
            for n, i in SKILL_INFO.items()
            if (hidden or not i.get("hidden")) and (r := _pd(pd, i["index"])) is not None}

def _read_demo(pd):
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


# Output formatters

def _emit(data, fmt, headers=None):
    if fmt == "json": print(json.dumps(data, indent=2, default=str))
    elif fmt == "yaml": _emit_yaml(data)
    elif fmt == "csv": _emit_csv(data, headers)
    elif fmt == "raw": _emit_raw(data)
    elif fmt == "table":
        if isinstance(data, str): print(data)
        elif isinstance(data, list) and data and isinstance(data[0], dict): _emit_table(data, headers)
        else: print(data)

def _emit_yaml(d, indent=0):
    p = "  " * indent
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)): print(f"{p}{k}:"); _emit_yaml(v, indent+1)
            else: print(f"{p}{k}: {v}")
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    print(f"{p}{'- ' if first else '  '}{k}: {v}"); first = False
            else: print(f"{p}- {item}")
    else: print(f"{p}{d}")

def _emit_csv(data, headers=None):
    buf = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = headers or list(data[0].keys())
        w = csv.DictWriter(buf, fieldnames=keys); w.writeheader()
        for row in data: w.writerow({k: row.get(k,"") for k in keys})
    elif isinstance(data, dict):
        w = csv.writer(buf)
        for k, v in data.items(): w.writerow([k, v])
    print(buf.getvalue().rstrip())

def _emit_raw(data):
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                for k2, v2 in v.items(): print(f"{k}.{k2}={v2}")
            else: print(f"{k}={v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict): print("\t".join(str(v) for v in item.values()))
            else: print(item)
    else: print(data)

def _emit_table(rows, headers=None):
    if not rows: return
    keys = headers or list(rows[0].keys())
    widths = {k: max(len(str(k)), max((len(str(r.get(k,""))) for r in rows), default=0)) for k in keys}
    print("  ".join(str(k).ljust(widths[k]) for k in keys))
    print("  ".join("-"*widths[k] for k in keys))
    for row in rows:
        print("  ".join(str(row.get(k,"")).ljust(widths[k]) for k in keys))


# Commands: IFF

def cmd_iff_info(args):
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
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    rows = []
    for c in iff.chunks:
        t = c.type_code if hasattr(c, 'type_code') else type(c).__name__
        if args.type and t != args.type: continue
        rows.append({
            "type": t,
            "id": c.chunk_id,
            "label": getattr(c, 'chunk_label', ''),
            "size": getattr(c, 'chunk_size', 0),
        })
    _emit(rows, args.format, ["type", "id", "label", "size"])

def cmd_iff_strings(args):
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    from formats.iff.chunks.str_ import STR, CTSS
    results = []
    for chunk in iff.chunks:
        if not isinstance(chunk, (STR, CTSS)): continue
        if args.chunk_id is not None and chunk.chunk_id != args.chunk_id: continue
        for idx, lang_set in enumerate(chunk.strings):
            for lang_code, entry in lang_set.languages.items():
                if args.lang is not None and lang_code != args.lang: continue
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "chunk_type": chunk.type_code if hasattr(chunk, 'type_code') else type(chunk).__name__,
                    "index": idx,
                    "lang": lang_code,
                    "text": entry.value,
                })
    _emit(results, args.format, ["chunk_id", "chunk_type", "index", "lang", "text"])

def cmd_iff_objects(args):
    IffFile = _iff_file()
    iff = IffFile.read(args.file)
    from formats.iff.chunks.objd import OBJD
    rows = []
    for c in iff.chunks:
        if not isinstance(c, OBJD): continue
        rows.append({
            "id": c.chunk_id,
            "guid": f"0x{c.guid:08X}" if c.guid else "0x00000000",
            "label": getattr(c, 'chunk_label', ''),
            "type": str(c.object_type) if hasattr(c, 'object_type') else "",
            "price": c.price if hasattr(c, 'price') else 0,
        })
    _emit(rows, args.format, ["id", "guid", "label", "type", "price"])

def cmd_iff_bhav(args):
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
                    print(f"  [{i:>3}] opcode=0x{opcode:04X}  T→{true_t}  F→{false_t}")
                return
        print(f"ERROR: BHAV #{args.id} not found", file=sys.stderr); sys.exit(1)
    rows = []
    for c in iff.chunks:
        if not isinstance(c, BHAV): continue
        rows.append({
            "id": c.chunk_id,
            "label": getattr(c, 'chunk_label', ''),
            "instructions": len(c.instructions),
        })
    _emit(rows, args.format, ["id", "label", "instructions"])


# Commands: FAR

def cmd_far_list(args):
    path = args.file
    try:
        FAR1Archive = _far1()
        arc = FAR1Archive(path)
        rows = [{"index": i, "name": e.filename, "size": e.file_size1}
                for i, e in enumerate(arc.entries)]
        if args.format == "table":
            print(f"FAR Archive: {path} ({len(rows)} files)")
        _emit(rows, args.format, ["index", "name", "size"])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)

def cmd_far_extract(args):
    try:
        FAR1Archive = _far1()
        arc = FAR1Archive(args.file)
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        if args.name:
            data = arc.get_entry(args.name)
            if data is None:
                print(f"ERROR: '{args.name}' not found in archive", file=sys.stderr); sys.exit(1)
            (out / args.name).write_bytes(data)
            print(f"Extracted: {args.name} ({len(data)} bytes)")
        else:
            arc.extract_all(str(out))
            print(f"Extracted {len(arc.entries)} files to {out}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)


# Commands: Save editing

def cmd_inspect(args):
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
        if families: print("FAMILIES"); _emit_table(families, ["id","house","budget","members","status"])
        if characters: print("\nCHARACTERS"); _emit_table(characters, ["id","name","traits"])
    else:
        _emit({"families": families, "characters": characters}, args.format)

def cmd_families(args):
    mgr = _load_save(args.file)
    rows = [{"id": fid, "house": f.house_number, "budget": f.budget,
             "members": f.num_members, "status": "townie" if f.is_townie else "resident"}
            for fid, f in sorted(mgr.families.items())]
    _emit(rows, args.format, ["id","house","budget","members","status"])

def cmd_character(args):
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: {n.name} has no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data); sk = _read_skills(n.person_data); dm = _read_demo(n.person_data)
    data = {"name": n.name, "neighbor_id": nid, "demographics": dm,
            "traits": {k:v["display"] for k,v in tr.items()},
            "traits_raw": {k:v["raw"] for k,v in tr.items()},
            "skills": {k:v["display"] for k,v in sk.items()},
            "skills_raw": {k:v["raw"] for k,v in sk.items()},
            "relationships": {str(k):v for k,v in n.relationships.items()}}
    if args.format == "table":
        print(f"{'='*50}\n  {n.name}  (neighbor #{nid})\n{'='*50}")
        print(f"\n  {dm['age']}  |  {dm['gender']}  |  {dm['zodiac']}  |  {dm['career']}")
        print(f"\n  PERSONALITY\n  {'─'*44}")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr: v=tr[t]; print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}")
        print(f"\n  SKILLS\n  {'─'*44}")
        for s in VISIBLE_SKILLS:
            if s in sk: v=sk[s]; print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}")
        if n.relationships:
            print(f"\n  RELATIONSHIPS\n  {'─'*44}")
            for rid,rv in list(n.relationships.items())[:10]:
                d=rv[0] if len(rv)>0 else "?"; l=rv[1] if len(rv)>1 else "?"
                print(f"  Neighbor {rid}: daily={d}, lifetime={l}")
    else: _emit(data, args.format)

def cmd_traits(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Personality")
        for t in ["neat","outgoing","active","playful","nice","generous"]:
            if t in tr: v=tr[t]; print(f"  {v['low']:>8} [{_bar(v['display'])}] {v['high']:<8} {v['display']:>2}  (raw {v['raw']})")
    else: _emit({"name": n.name, "traits": {k:v["display"] for k,v in tr.items()}}, args.format)

def cmd_skills(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    sk = _read_skills(n.person_data)
    if args.format == "table":
        print(f"{n.name} — Skills")
        for s in VISIBLE_SKILLS:
            if s in sk: v=sk[s]; print(f"  {s:>12} [{_bar(v['display'])}] {v['display']:>2}  (raw {v['raw']})")
    else: _emit({"name": n.name, "skills": {k:v["display"] for k,v in sk.items()}}, args.format)

def cmd_set_trait(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_personality(nid, args.trait, raw): mgr.save(); print(f"Saved. {n.name} {args.trait} = {args.value}")
    else: sys.exit(1)

def cmd_set_skill(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    raw = max(0, min(args.value, 10)) * 100
    if mgr.set_sim_skill(nid, args.skill, raw): mgr.save(); print(f"Saved. {n.name} {args.skill} = {args.value}")
    else: sys.exit(1)

def cmd_set_money(args):
    mgr = _load_save(args.file)
    if mgr.set_family_money(args.family_id, args.amount): mgr.save(); print(f"Saved. Family {args.family_id} = §{args.amount:,}")
    else: sys.exit(1)

def cmd_dump_raw(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    known = {}
    for name, info in TRAIT_INFO.items(): known[info["index"]] = f"personality.{name}"
    for name, info in SKILL_INFO.items(): known[info["index"]] = f"skill.{name}"
    for name, idx in DEMO_FIELDS.items(): known[idx] = f"demo.{name}"
    for name, idx in CAREER_FIELDS.items(): known[idx] = f"career.{name}"
    known.update({0:"idle_state", 1:"npc_fee_amount", 8:"current_outfit"})
    rows = [{"index":i, "value":v, "field":known.get(i,""), "nz":"*" if v!=0 else ""}
            for i,v in enumerate(n.person_data)]
    if args.format == "table":
        print(f"PersonData for {n.name} ({len(n.person_data)} fields)\n{'─'*55}")
        for r in rows: print(f"  [{r['index']:>3}] {r['value']:>6}{r['nz']:>2}  {r['field']}")
    else: _emit(rows, args.format, ["index","value","field"])


# Commands: Uplift/Download

def cmd_uplift(args):
    mgr = _load_save(args.file); nid, n = _find(mgr, args.name)
    if not n.person_data: print(f"ERROR: no person_data", file=sys.stderr); sys.exit(1)
    tr = _read_traits(n.person_data); sk = _read_skills(n.person_data); dm = _read_demo(n.person_data)
    lines = [f"# {n.name} — Uplifted from Sims 1 save data",
             f"# Neighbor ID: {nid}  |  Source: {args.file}", "", "sims:", "  traits:"]
    for t in ["neat","outgoing","active","playful","nice","generous"]:
        if t in tr:
            v=tr[t]; lines.append(f"    {t}: {v['display']:<3}  # {v['low']} {v['display']}/10 {v['high']}")
    lines.append("  skills:")
    for s in VISIBLE_SKILLS:
        if s in sk: lines.append(f"    {s}: {sk[s]['display']}")
    lines += ["  career:", f"    track: {dm['career'].lower().replace('/','_')}",
              f"    performance: {dm['job_performance']}",
              "  identity:", f"    age: {dm['age']}", f"    gender: {dm['gender']}",
              f"    zodiac: {dm['zodiac'].lower()}", f"    skin_color: {dm['skin_color']}"]
    out = "\n".join(lines) + "\n"
    if args.output:
        p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out); print(f"Wrote {p}")
    else: print(out, end="")


def cmd_sync(args):
    """Compare save file against existing CHARACTER.yml, emit merge events.

    This is an event generator, not a writer. It reads both sources,
    diffs them, and emits structured events that tell the LLM what
    changed and what decisions need to be made. The LLM then processes
    the events and updates the CHARACTER.yml accordingly.

    Event types:
      NEW_CHARACTER  — no existing file, full uplift needed
      TRAIT_MATCH    — values agree, no action
      TRAIT_DRIFT    — values differ, LLM decides how to merge
      SKILL_GAINED   — save shows higher skill (Sim learned something)
      SKILL_LOST     — save shows lower skill (unusual)
      CAREER_CHANGE  — different career track
      CAREER_ADVANCE — same track, higher status/performance
      RELATIONSHIP_NEW     — save has relationship not in YAML
      RELATIONSHIP_CHANGED — scores differ
      DEMOGRAPHIC_MATCH    — age/gender/zodiac agree
      DEMOGRAPHIC_DRIFT    — demographic changed (age up, etc.)
      NARRATIVE_STALE      — traits changed enough that soul_philosophy needs revisiting
      NEEDS_NOTE           — reminder that motives are runtime, not in save
    """
    mgr = _load_save(args.file)
    nid, n = _find(mgr, args.name)
    if not n.person_data:
        print(f"ERROR: {n.name} has no person_data", file=sys.stderr)
        sys.exit(1)

    save_traits = _read_traits(n.person_data)
    save_skills = _read_skills(n.person_data)
    save_demo = _read_demo(n.person_data)

    # Try to parse the existing CHARACTER.yml
    yml_path = Path(args.character_yml)
    yml_traits = {}
    yml_skills = {}
    yml_demo = {}
    yml_relationships = {}
    yml_exists = False

    if yml_path.is_file():
        yml_exists = True
        yml_text = yml_path.read_text()
        yml_traits, yml_skills, yml_demo, yml_relationships = _parse_character_yml(yml_text)

    events = []

    if not yml_exists:
        events.append({
            "type": "NEW_CHARACTER",
            "severity": "action",
            "message": f"No existing CHARACTER.yml at {yml_path}. Full uplift needed.",
            "suggestion": f"Run: obliterator uplift {args.file} '{args.name}' -o {yml_path}",
        })
        _emit(events, args.format)
        return

    # Trait comparison
    trait_drift_count = 0
    for t in ["neat", "outgoing", "active", "playful", "nice", "generous"]:
        save_val = save_traits.get(t, {}).get("display")
        yml_val = yml_traits.get(t)
        if save_val is None:
            continue
        if yml_val is None:
            events.append({"type": "TRAIT_DRIFT", "severity": "info",
                           "field": t, "save": save_val, "yaml": None,
                           "message": f"{t}: save={save_val}, YAML missing"})
            trait_drift_count += 1
        elif save_val != yml_val:
            delta = save_val - yml_val
            direction = "higher" if delta > 0 else "lower"
            events.append({"type": "TRAIT_DRIFT", "severity": "warning",
                           "field": t, "save": save_val, "yaml": yml_val,
                           "delta": delta,
                           "message": f"{t}: save={save_val} vs yaml={yml_val} ({direction} by {abs(delta)})",
                           "suggestion": f"Update sims.traits.{t} to {save_val}, "
                                        f"or keep {yml_val} if MOOLLM changes are intentional"})
            trait_drift_count += 1
        else:
            events.append({"type": "TRAIT_MATCH", "severity": "ok",
                           "field": t, "value": save_val,
                           "message": f"{t}: {save_val} (matches)"})

    # Skill comparison
    for s in VISIBLE_SKILLS:
        save_val = save_skills.get(s, {}).get("display")
        yml_val = yml_skills.get(s)
        if save_val is None:
            continue
        if yml_val is None:
            events.append({"type": "SKILL_GAINED", "severity": "info",
                           "field": s, "save": save_val, "yaml": 0,
                           "message": f"{s}: save={save_val}, YAML missing"})
        elif save_val > yml_val:
            events.append({"type": "SKILL_GAINED", "severity": "info",
                           "field": s, "save": save_val, "yaml": yml_val,
                           "delta": save_val - yml_val,
                           "message": f"{s}: {yml_val} → {save_val} (+{save_val - yml_val})",
                           "suggestion": f"Sim gained {s} skill in The Sims. "
                                        f"Update and add a memory about learning."})
        elif save_val < yml_val:
            events.append({"type": "SKILL_LOST", "severity": "warning",
                           "field": s, "save": save_val, "yaml": yml_val,
                           "delta": save_val - yml_val,
                           "message": f"{s}: {yml_val} → {save_val} ({save_val - yml_val})",
                           "suggestion": f"Skill decreased. Unusual. Check if save "
                                        f"is older or was manually edited."})
        else:
            events.append({"type": "SKILL_MATCH", "severity": "ok",
                           "field": s, "value": save_val,
                           "message": f"{s}: {save_val} (matches)"})

    # Career comparison
    save_career = save_demo.get("career", "Unemployed")
    yml_career = yml_demo.get("career")
    if yml_career and save_career.lower() != yml_career.lower():
        events.append({"type": "CAREER_CHANGE", "severity": "warning",
                       "save": save_career, "yaml": yml_career,
                       "message": f"Career: {yml_career} → {save_career}",
                       "suggestion": f"Sim changed careers. Update career track "
                                    f"and consider adding a memory about the switch."})
    elif yml_career:
        events.append({"type": "CAREER_MATCH", "severity": "ok",
                       "value": save_career,
                       "message": f"Career: {save_career} (matches)"})

    # Demographic comparison
    for field in ["age", "gender", "zodiac"]:
        save_val = save_demo.get(field)
        yml_val = yml_demo.get(field)
        if yml_val and save_val and str(save_val).lower() != str(yml_val).lower():
            events.append({"type": "DEMOGRAPHIC_DRIFT", "severity": "warning",
                           "field": field, "save": save_val, "yaml": yml_val,
                           "message": f"{field}: {yml_val} → {save_val}",
                           "suggestion": f"Update identity.{field} to {save_val}"})
        elif yml_val:
            events.append({"type": "DEMOGRAPHIC_MATCH", "severity": "ok",
                           "field": field, "value": save_val,
                           "message": f"{field}: {save_val} (matches)"})

    # Relationship comparison
    for rel_id, rel_vals in n.relationships.items():
        daily = rel_vals[0] if len(rel_vals) > 0 else 0
        lifetime = rel_vals[1] if len(rel_vals) > 1 else 0
        yml_rel = yml_relationships.get(str(rel_id))
        if yml_rel is None:
            events.append({"type": "RELATIONSHIP_NEW", "severity": "info",
                           "target_id": rel_id, "daily": daily, "lifetime": lifetime,
                           "message": f"New relationship with neighbor {rel_id}: "
                                     f"daily={daily}, lifetime={lifetime}",
                           "suggestion": f"Add relationship entry. LLM should generate "
                                        f"a narrative based on the scores."})
        else:
            yml_daily = yml_rel.get("daily")
            yml_lifetime = yml_rel.get("lifetime")
            if (yml_daily is not None and yml_daily != daily) or \
               (yml_lifetime is not None and yml_lifetime != lifetime):
                events.append({"type": "RELATIONSHIP_CHANGED", "severity": "info",
                               "target_id": rel_id,
                               "save_daily": daily, "save_lifetime": lifetime,
                               "yaml_daily": yml_daily, "yaml_lifetime": yml_lifetime,
                               "message": f"Relationship {rel_id}: "
                                         f"daily {yml_daily}→{daily}, "
                                         f"lifetime {yml_lifetime}→{lifetime}",
                               "suggestion": f"Update scores. If big change, "
                                            f"LLM should update the narrative."})

    # Narrative staleness check
    if trait_drift_count >= 2:
        events.append({"type": "NARRATIVE_STALE", "severity": "action",
                       "drift_count": trait_drift_count,
                       "message": f"{trait_drift_count} traits drifted. "
                                 f"soul_philosophy and description may need revision.",
                       "suggestion": f"LLM should re-read the updated traits and "
                                    f"revise the character's voice and self-description "
                                    f"to reflect who they've become."})

    # Motives reminder
    events.append({"type": "NEEDS_NOTE", "severity": "info",
                   "message": "Motives (hunger, comfort, etc.) are runtime state. "
                             "Not in save file. CHARACTER.yml needs values may be "
                             "stale or fictional — update based on narrative context."})

    # Summary
    actions = sum(1 for e in events if e["severity"] == "action")
    warnings = sum(1 for e in events if e["severity"] == "warning")
    infos = sum(1 for e in events if e["severity"] == "info")
    oks = sum(1 for e in events if e["severity"] == "ok")

    if args.format == "table":
        print(f"SYNC: {n.name}")
        print(f"Save: {args.file}  |  YAML: {args.character_yml}")
        print(f"Events: {len(events)} ({actions} actions, {warnings} warnings, "
              f"{infos} info, {oks} ok)\n")
        for e in events:
            icon = {"ok": "  ", "info": "->", "warning": "!!", "action": ">>"}
            sev = icon.get(e["severity"], "  ")
            print(f"  {sev} [{e['type']}] {e['message']}")
            if "suggestion" in e:
                print(f"     {e['suggestion']}")
    else:
        _emit({"name": n.name, "save_file": args.file,
               "character_yml": args.character_yml,
               "summary": {"actions": actions, "warnings": warnings,
                           "info": infos, "ok": oks},
               "events": events}, args.format)


def _parse_character_yml(text):
    """Minimal YAML parser for CHARACTER.yml sims: block.

    Not a full YAML parser — just extracts the fields we need for
    sync comparison. Works on the subset of YAML that CHARACTER.yml
    uses. Returns (traits, skills, demo, relationships).
    """
    traits = {}
    skills = {}
    demo = {}
    relationships = {}

    lines = text.split("\n")
    section = None
    subsection = None

    for line in lines:
        stripped = line.split("#")[0].rstrip()  # strip comments
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        # Detect sections
        if indent == 0 or (indent <= 2 and ":" in stripped):
            if "sims:" in stripped:
                section = "sims"
                continue
            elif "relationships:" in stripped and section != "sims":
                section = "relationships"
                continue
            elif stripped.endswith(":") and not stripped.startswith(" "):
                section = None
                continue

        if section == "sims":
            if "traits:" in stripped and indent <= 4:
                subsection = "traits"; continue
            elif "skills:" in stripped and indent <= 4:
                subsection = "skills"; continue
            elif "career:" in stripped and indent <= 4:
                subsection = "career"; continue
            elif "identity:" in stripped and indent <= 4:
                subsection = "identity"; continue
            elif "needs:" in stripped and indent <= 4:
                subsection = "needs"; continue
            elif stripped.endswith(":") and indent <= 4:
                subsection = None; continue

            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if not val:
                    continue
                # Try to parse as number
                try:
                    num_val = int(val)
                except ValueError:
                    try:
                        num_val = float(val)
                    except ValueError:
                        num_val = None

                if subsection == "traits" and num_val is not None:
                    traits[key] = int(num_val)
                elif subsection == "skills" and num_val is not None:
                    skills[key] = int(num_val)
                elif subsection == "career":
                    if key == "track":
                        demo["career"] = val
                    elif key == "performance" and num_val is not None:
                        demo["job_performance"] = int(num_val)
                elif subsection == "identity":
                    demo[key] = val

        if section == "relationships":
            # Simple: just detect neighbor IDs and daily/lifetime
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "daily" or key == "lifetime":
                    pass  # handled below
                elif key == "type":
                    pass
                # Crude relationship parsing — the LLM handles the real merge

    return traits, skills, demo, relationships


# Parser builder — driven by COMMANDS table

def build_parser():
    parser = argparse.ArgumentParser(
        prog="obliterator",
        description="One CLI to rule The Sims 1 files. IFF inspection, FAR archives, "
                    "save editing, character uplift.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Formats: table json yaml csv raw | "
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
            if "type" in a: kw["type"] = a["type"]
            p.add_argument(a["name"], **kw)
        for o in spec.get("opts", []):
            kw = {"help": o["help"]}
            if "type" in o: kw["type"] = o["type"]
            if "choices" in o: kw["choices"] = o["choices"]
            if "default" in o: kw["default"] = o["default"]
            p.add_argument(*o["flags"], **kw)
        fn = "cmd_" + cmd_name.replace("-", "_")
        dispatch[cmd_name] = globals().get(fn)
    return parser, dispatch

def main():
    parser, dispatch = build_parser()
    args = parser.parse_args()
    if not args.command: parser.print_help(); sys.exit(0)
    fn = dispatch.get(args.command)
    if fn: fn(args)
    else: parser.print_help()

if __name__ == "__main__":
    main()
