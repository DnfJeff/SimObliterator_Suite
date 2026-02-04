#!/usr/bin/env python3
"""
Batch analyze all expansion packs and merge forensic results.

Usage:
    python run_expansion_analysis.py
"""

import sys
import subprocess
from pathlib import Path
from collections import defaultdict

base_path = Path("G:\\SteamLibrary\\steamapps\\common\\The Sims Legacy Collection")

# All available FAR files to analyze
expansions = [
    ("Base Game", base_path / "GameData/Objects/Objects.far"),
    ("Expansion 1", base_path / "ExpansionPack/ExpansionPack.far"),
    ("Expansion 2", base_path / "ExpansionPack2/ExpansionPack2.far"),
    ("Expansion 3", base_path / "ExpansionPack3/ExpansionPack3.far"),
    ("Expansion 4", base_path / "ExpansionPack4/ExpansionPack4.far"),
    ("Expansion 5", base_path / "ExpansionPack5/ExpansionPack5.far"),
    ("Expansion 6", base_path / "ExpansionPack6/ExpansionPack6.far"),
    ("Expansion 7", base_path / "ExpansionPack7/ExpansionPack7.far"),
]

def run_analysis(label, far_path):
    """Run pipeline analysis on a FAR file."""
    if not far_path.exists():
        print(f"[SKIP] {label}: File not found")
        return None
    
    output_file = f"expansion_forensic_{label.lower().replace(' ', '_')}.txt"
    cmd = [
        sys.executable,
        "Program/test_pipeline.py",
        "--mode", "quick",
        "--limit", "0",
        "--far-file", str(far_path),
        "--output", output_file,
    ]
    
    print(f"[RUNNING] {label} ({far_path.name})...", end=" ", flush=True)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print("OK")
        return output_file
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    print("\n" + "="*120)
    print(" BATCH EXPANSION PACK FORENSIC ANALYSIS")
    print("="*120 + "\n")
    
    results = []
    for label, far_path in expansions:
        output = run_analysis(label, far_path)
        if output:
            results.append((label, output))
    
    print(f"\n[COMPLETE] Analyzed {len(results)} archives")
    print("\nGenerated output files:")
    for label, output in results:
        print(f"  - {output}")
    
    print("\n" + "="*120)
    print("Next: Review forensic reports for high-confidence opcode patterns")
    print("="*120 + "\n")

if __name__ == '__main__':
    main()
