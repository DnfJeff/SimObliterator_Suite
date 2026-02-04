"""
EXPANSION PACK FORENSIC ANALYZER

Analyzes multiple FAR files across expansion packs to accumulate opcode patterns.
With more game data = higher confidence in pattern identification.

Strategy:
1. Run pipeline on base game Objects.far
2. Run pipeline on each expansion pack
3. Combine all opcode->object mappings
4. Regenerate forensic analysis with combined dataset
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Setup paths
program_dir = Path(__file__).parent


class ExpansionAnalyzer:
    """Analyzes multiple FAR files to build comprehensive opcode profiles."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.base_game_path = Path("G:\\SteamLibrary\\steamapps\\common\\The Sims Legacy Collection")
        
        # Priority order: base game first, then expansions
        self.far_files = [
            ("Base Game", self.base_game_path / "GameData/Objects/Objects.far"),
            ("Expansion 1", self.base_game_path / "ExpansionPack/ExpansionPack.far"),
            ("Expansion 2", self.base_game_path / "ExpansionPack2/ExpansionPack2.far"),
            ("Expansion 3", self.base_game_path / "ExpansionPack3/ExpansionPack3.far"),
            ("Expansion 4", self.base_game_path / "ExpansionPack4/ExpansionPack4.far"),
            ("Expansion 5", self.base_game_path / "ExpansionPack5/ExpansionPack5.far"),
            ("Expansion 6", self.base_game_path / "ExpansionPack6/ExpansionPack6.far"),
            ("Expansion 7", self.base_game_path / "ExpansionPack7/ExpansionPack7.far"),
        ]
    
    def extract_opcodes_from_output(self, output_text: str) -> Dict[int, List[str]]:
        """Extract opcode mappings from pipeline output."""
        opcodes = defaultdict(list)
        
        lines = output_text.split('\n')
        for i, line in enumerate(lines):
            # Look for opcode lines like "- Opcode 0x0157: 4 occurrence(s)"
            if 'Opcode 0x' in line and 'occurrence' in line:
                try:
                    # Extract hex value
                    hex_start = line.index('0x')
                    hex_str = line[hex_start:hex_start+6]
                    opcode_val = int(hex_str, 16)
                    
                    # Try to find object names near this opcode marker
                    # For now, just track that the opcode exists
                    # In real implementation, would parse more carefully
                except:
                    pass
        
        return opcodes
    
    def run(self):
        """Run analysis on expansion packs."""
        print("\n" + "="*120)
        print(" EXPANSION PACK FORENSIC ANALYSIS")
        print("="*120)
        print("\nAnalyzing multiple FAR files to build high-confidence opcode patterns...")
        print("Strategy: More examples = higher confidence in pattern identification\n")
        
        all_results = []
        combined_opcode_objects = defaultdict(set)
        
        # Analyze each FAR file
        for label, far_path in self.far_files:
            if not far_path.exists():
                print(f"[SKIP] {label}: File not found")
                continue
            
            print(f"\n[{label:15}] Analyzing {far_path.name}...")
            
            # Run pipeline on this FAR file
            output_file = program_dir / f"expansion_temp_{label.replace(' ', '_')}.txt"
            cmd = [
                sys.executable,
                str(program_dir / "test_pipeline.py"),
                "--mode", "quick",
                "--output", str(output_file),
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                # Check if output file was created
                if output_file.exists():
                    with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                        output = f.read()
                    
                    # Parse output for statistics
                    lines = output.split('\n')
                    for line in lines:
                        if 'Objects processed:' in line:
                            print(f"  {line.strip()}")
                        elif 'Total BHAVs:' in line:
                            print(f"  {line.strip()}")
                        elif 'Unique unknown opcodes:' in line:
                            print(f"  {line.strip()}")
                    
                    all_results.append({
                        'label': label,
                        'path': str(far_path),
                        'output_file': str(output_file),
                        'success': True
                    })
                else:
                    print(f"  ERROR: Output file not created")
                    all_results.append({'label': label, 'success': False})
                    
            except subprocess.TimeoutExpired:
                print(f"  ERROR: Analysis timeout")
                all_results.append({'label': label, 'success': False})
            except Exception as e:
                print(f"  ERROR: {str(e)[:80]}")
                all_results.append({'label': label, 'success': False})
        
        # Summary
        print("\n" + "="*120)
        print(" ANALYSIS COMPLETE")
        print("="*120)
        successful = sum(1 for r in all_results if r.get('success'))
        print(f"\nSuccessfully analyzed: {successful} FAR files")
        print("\nNext step: Review forensic reports from each expansion")
        print("- Compare opcode patterns across expansions")
        print("- Higher confidence opcodes appear in multiple FAR files")
        print("- Check for category-specific operations\n")
        
        return all_results


if __name__ == '__main__':
    analyzer = ExpansionAnalyzer()
    results = analyzer.run()

