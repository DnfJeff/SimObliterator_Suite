#!/usr/bin/env python3
"""Deep scan Global.iff for all BHAV chunks"""

import struct

# First extract Global.iff from Global.far
global_far = r"G:\SteamLibrary\steamapps\common\The Sims Legacy Collection\GameData\Global\Global.far"

with open(global_far, 'rb') as f:
    f.seek(12)
    manifest_offset = struct.unpack('<I', f.read(4))[0]
    f.seek(manifest_offset)
    entry_count = struct.unpack('<I', f.read(4))[0]
    
    for i in range(entry_count):
        data_size = struct.unpack('<I', f.read(4))[0]
        data_size2 = struct.unpack('<I', f.read(4))[0]
        data_offset = struct.unpack('<I', f.read(4))[0]
        filename_len = struct.unpack('<I', f.read(4))[0]
        filename = f.read(filename_len).decode('latin1').rstrip(chr(0))
        
        if filename == 'Global.iff':
            f.seek(data_offset)
            iff_data = f.read(data_size)
            
            # Find all BHAV chunks
            bhav_chunks = []
            idx = 0
            while True:
                idx = iff_data.find(b'BHAV', idx)
                if idx == -1:
                    break
                
                # BE chunk size
                chunk_size = struct.unpack('>I', iff_data[idx+4:idx+8])[0]
                
                # BHAV header format (after chunk header):
                # Offset 0-1: Chunk ID (LE)
                # Offset 2-63: Name (null-terminated)
                # Offset 64-65: Flags/version?
                
                chunk_id = struct.unpack('<H', iff_data[idx+8:idx+10])[0]
                
                # Name is at offset 10 in chunk
                name_bytes = iff_data[idx+10:idx+72]  # Up to 62 chars
                name = ''
                for b in name_bytes:
                    if b == 0:
                        break
                    if 32 <= b < 127:
                        name += chr(b)
                
                bhav_chunks.append((chunk_id, name.strip(), chunk_size))
                idx += 8 + chunk_size  # Move past this chunk
            
            # Sort by ID
            bhav_chunks.sort()
            
            print(f"BHAV chunks in Global.iff ({len(bhav_chunks)} total):")
            print()
            
            # Group by range
            ranges = {
                "256-511 (Base)": [],
                "512-767 (LL?)": [],
                "768-1023 (HP?)": [],
                "1024-1279 (HD?)": [],
                "1280-1535 (DT?)": [],
                "1536-1791 (VAC?)": [],
                "1792-2047 (UNL?)": [],
                "2048-2303 (SS?)": [],
                "2304-2559 (MM?)": [],
                "2560+ (Other)": [],
            }
            
            for chunk_id, name, size in bhav_chunks:
                if 256 <= chunk_id <= 511:
                    ranges["256-511 (Base)"].append((chunk_id, name))
                elif 512 <= chunk_id <= 767:
                    ranges["512-767 (LL?)"].append((chunk_id, name))
                elif 768 <= chunk_id <= 1023:
                    ranges["768-1023 (HP?)"].append((chunk_id, name))
                elif 1024 <= chunk_id <= 1279:
                    ranges["1024-1279 (HD?)"].append((chunk_id, name))
                elif 1280 <= chunk_id <= 1535:
                    ranges["1280-1535 (DT?)"].append((chunk_id, name))
                elif 1536 <= chunk_id <= 1791:
                    ranges["1536-1791 (VAC?)"].append((chunk_id, name))
                elif 1792 <= chunk_id <= 2047:
                    ranges["1792-2047 (UNL?)"].append((chunk_id, name))
                elif 2048 <= chunk_id <= 2303:
                    ranges["2048-2303 (SS?)"].append((chunk_id, name))
                elif 2304 <= chunk_id <= 2559:
                    ranges["2304-2559 (MM?)"].append((chunk_id, name))
                else:
                    ranges["2560+ (Other)"].append((chunk_id, name))
            
            for range_name, chunks in ranges.items():
                if chunks:
                    print(f"{range_name}: {len(chunks)} chunks")
                    for chunk_id, name in chunks[:5]:
                        print(f"  {chunk_id}: '{name}'")
                    if len(chunks) > 5:
                        print(f"  ... ({len(chunks)} total)")
                    print()
            
            # Check if expansion chunks have names
            print("Checking if expansion IDs have names...")
            for chunk_id, name, size in bhav_chunks:
                if chunk_id >= 512 and name:
                    print(f"  Found named expansion chunk: {chunk_id} = '{name}'")
            break
