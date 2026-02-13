# IFF Chunks Directory - Complete Implementation Status

This document provides a comprehensive summary of all 59 files in the `src/formats/iff/chunks/` folder, their implementation status, and known issues.

---

## Quick Summary

| Status            | Count | Description                   |
| ----------------- | ----- | ----------------------------- |
| ✅ Complete (R/W) | 17    | Full read + write support     |
| ⚠️ Read-Only      | 32    | Read works, no write() method |
| 🔧 Partial        | 6     | Incomplete parsing or stub    |
| 📦 Wrapper/Alias  | 4     | Inherits from another chunk   |

---

## Implementation Matrix

### Core Object Chunks

| File      | Chunk Type | read() | write() | Notes                                                                            |
| --------- | ---------- | ------ | ------- | -------------------------------------------------------------------------------- |
| `objd.py` | OBJD       | ✅     | ❌      | Object Definition - THE main object chunk. 140+ fields. **CRITICAL: No write()** |
| `objf.py` | OBJf       | ✅     | ✅      | Object Functions - event→BHAV mapping                                            |
| `objt.py` | OBJT/objt  | ✅     | ❌      | Object Type Info - lot object list                                               |
| `objm.py` | OBJM       | ✅     | ❌      | Object Manager - all object instances (641 lines, complex)                       |

### Behavior (BHAV) System - 14 Files

| File                           | Purpose              | Status      | Notes                                                  |
| ------------------------------ | -------------------- | ----------- | ------------------------------------------------------ |
| `bhav.py`                      | Core BHAV chunk      | read() only | **CRITICAL: No write()** - can't save edited behaviors |
| `bhav_ast.py`                  | AST representation   | Complete    | 755 lines, 50+ dataclasses for operands                |
| `bhav_decompiler.py`           | Bytecode→AST         | Complete    | BHAVDecompiler class                                   |
| `bhav_formatter.py`            | Output formatting    | Complete    | Pseudocode/assembly/flowchart                          |
| `bhav_beautifier.py`           | Code readability     | Complete    | Variable naming, structure                             |
| `bhav_analysis.py`             | Code quality         | Complete    | Linter, complexity analyzer                            |
| `bhav_cross_reference.py`      | Call graph           | Complete    | callers_of(), callees_of()                             |
| `bhav_graph.py`                | CFG visualization    | Complete    | Mermaid, ASCII, DOT output                             |
| `bhav_validator.py`            | Static validation    | Complete    | Type/stack/control flow checks                         |
| `bhav_performance_analyzer.py` | Performance          | Complete    | Dead code, hot spots, loops                            |
| `bhav_package_decompiler.py`   | Whole-file decompile | Complete    | PackageAST with cross-refs                             |
| `bhav_operands.py`             | Operand decoders     | Complete    | 971 lines, ~50 decode\_\* functions                    |
| `bhav_editor.py`               | Tkinter GUI          | UI Complete | **Save not implemented**                               |
| `bhav_integration.py`          | Legacy stubs         | DEPRECATED  | All functions raise NotImplementedError                |

### Sprite & Graphics

| File               | Chunk Type | read() | write() | Notes                                   |
| ------------------ | ---------- | ------ | ------- | --------------------------------------- |
| `spr.py`           | SPR#, SPR2 | ✅     | ❌      | Sprite frames with RLE. No decode/write |
| `dgrp.py`          | DGRP       | ✅     | ❌      | Drawing Groups - 4 directions × 3 zooms |
| `palt.py`          | PALT       | ✅     | ✅      | Color palettes (256 RGB)                |
| `sprite_export.py` | Utility    | N/A    | N/A     | SPR2→PNG export with z-buffer support   |
| `bmp.py`           | BMP*, PNG* | ✅     | ✅      | Raw image data containers               |
| `thmb.py`          | THMB       | ✅     | ✅      | Thumbnail dimensions                    |
| `mtex.py`          | MTEX       | ✅     | ✅      | Mesh textures (jpg/png/bmp)             |

### Strings & Labels

| File      | Chunk Type | read() | write() | Notes                                         |
| --------- | ---------- | ------ | ------- | --------------------------------------------- |
| `str_.py` | STR#, CTSS | ✅     | ❌      | String tables, multi-language. **No write()** |
| `ttas.py` | TTAs       | ✅     | ❌      | Pie menu strings (inherits STR)               |
| `fams.py` | FAMs       | ✅     | ❌      | Family strings (inherits STR)                 |
| `tprp.py` | TPRP       | ✅     | ✅      | BHAV param/local names                        |
| `trcn.py` | TRCN       | ✅     | ✅      | BCON constant labels                          |

### Interaction & Behavior Tables

| File      | Chunk Type | read() | write() | Notes                                     |
| --------- | ---------- | ------ | ------- | ----------------------------------------- |
| `ttab.py` | TTAB       | ✅     | ❌      | Tree Tables - interaction definitions     |
| `bcon.py` | BCON       | ✅     | ❌      | Constants chunk. 60 lines. **No write()** |
| `slot.py` | SLOT       | ✅     | ❌      | Routing slot positions                    |
| `glob.py` | GLOB       | ✅     | ❌      | Semi-global file reference (simple)       |
| `tree.py` | TREE       | ✅     | ✅      | IDE visual layout for behaviors           |
| `anim.py` | ANIM       | ✅     | ❌      | Keyframe animation data                   |

### Neighborhood & Family

| File      | Chunk Type | read() | write() | Notes                                |
| --------- | ---------- | ------ | ------- | ------------------------------------ |
| `fami.py` | FAMI       | ✅     | ❌      | Family data (budget, members, house) |
| `ngbh.py` | NGBH       | ✅     | ❌      | Neighborhood data + inventory        |
| `nbrs.py` | NBRS       | ✅     | ❌      | All Sims in neighborhood             |
| `char.py` | CHAR       | ✅     | ❌      | Character personality (374 lines)    |

### Lot/House Data

| File      | Chunk Type | read() | write() | Notes                                       |
| --------- | ---------- | ------ | ------- | ------------------------------------------- |
| `hous.py` | HOUS       | ✅     | ✅      | House metadata                              |
| `simi.py` | SIMI       | ✅     | ✅      | Sim instance + budget tracking              |
| `arry.py` | ARRY       | ✅     | ❌      | 2D arrays (terrain, floors, walls) with RLE |
| `walm.py` | WALm, FLRm | ✅     | ✅      | Wall/floor mappings                         |
| `posi.py` | POSI       | ⚠️     | ❌      | Object position - minimal stub              |

### Career & Jobs

| File      | Chunk Type | read() | write() | Notes                             |
| --------- | ---------- | ------ | ------- | --------------------------------- |
| `carr.py` | CARR       | ✅     | ❌      | Career levels with field encoding |

### Effects & Advanced

| File      | Chunk Type | read() | write() | Notes                                       |
| --------- | ---------- | ------ | ------- | ------------------------------------------- |
| `part.py` | PART       | ✅     | ✅      | Particle system parameters                  |
| `fwav.py` | FWAV       | ✅     | ✅      | Sound event names                           |
| `fsom.py` | FSOM       | ✅     | ✅      | 3D mesh data (GZip compressed)              |
| `fsor.py` | FSOR       | ✅     | ✅      | Mesh reconstruction params                  |
| `fsov.py` | FSOV       | ✅     | ✅      | FreeSO version container                    |
| `piff.py` | PIFF       | ✅     | ✅      | IFF patch format (add/remove/modify chunks) |
| `fcns.py` | FCNS       | ✅     | ❌      | Simulator float constants                   |

### Utility & Support

| File                    | Purpose            | Notes                                                  |
| ----------------------- | ------------------ | ------------------------------------------------------ |
| `__init__.py`           | Exports            | 130 lines, exports 38+ classes. Lazy-loads bhav_editor |
| `field_encode.py`       | Bit-packed decoder | Used by CARR, OBJM                                     |
| `primitive_registry.py` | Opcode metadata    | 387 lines, ~50 primitive definitions                   |
| `rsmp.py`               | Resource map       | Optional index chunk for fast lookup                   |

### Legacy/Minimal

| File      | Chunk Type | read() | write() | Notes                          |
| --------- | ---------- | ------ | ------- | ------------------------------ |
| `xxxx.py` | XXXX       | ✅     | ✅      | Filler/padding chunk           |
| `tmpl.py` | TMPL       | ✅     | ✅      | Template - stores raw bytes    |
| `cats.py` | CATS       | ⚠️     | ⚠️      | Pet cat data - minimal stub    |
| `pers.py` | pers       | ⚠️     | ⚠️      | Person metadata - minimal stub |

---

## Critical Gaps

### 🚨 Missing write() Methods (Blockers for Editing)

These chunks can be read but **cannot be saved back**:

1. **`bhav.py`** - Can't save edited behaviors
2. **`objd.py`** - Can't modify object definitions
3. **`str_.py`** - Can't edit strings/translations
4. **`ttab.py`** - Can't modify interactions
5. **`bcon.py`** - Can't change constants
6. **`spr.py`** - Can't export/modify sprites
7. **`dgrp.py`** - Can't change drawing groups
8. **`slot.py`** - Can't edit routing slots
9. **`arry.py`** - Can't modify terrain/floor data

### ⚠️ Incomplete Implementations

1. **`spr.py`**: RLE decode not implemented (frame.decode() returns empty)
2. **`bhav_editor.py`**: Save button shows "Not implemented" messagebox
3. **`bhav_integration.py`**: All functions raise NotImplementedError (deprecated)
4. **`posi.py`**: Minimal stub, structure guessed
5. **`cats.py` / `pers.py`**: Raw byte storage only

---

## Architecture Notes

### Chunk Registration

```python
@register_chunk("TYPE")  # Registers class with IffFile loader
@dataclass
class TYPE(IffChunk):
    def read(self, iff, io): ...    # Parse binary data
    def write(self, iff, io): ...   # Optional: serialize back
```

### Common Patterns

1. **Header Pattern**: `pad(4) + version(4) + magic(4) + data...`
2. **Field Encoding**: Used by CARR, OBJM for bit-packed compression
3. **String Alignment**: Null-terminated strings often padded to 2-byte boundary
4. **STR Inheritance**: TTAs, FAMs, CTSS all inherit from STR

### Dependencies

```
BHAV → BCON (constants), TPRP (labels), TREE (layout)
OBJD → SPR2/DGRP (graphics), SLOT (routing), TTAB (interactions)
TTAB → TTAs (strings), BHAV (action/test functions)
OBJM → OBJT (type lookup), field_encode (compression)
SPR2 → PALT (colors), sprite_export (PNG conversion)
```

---

## File Statistics

| Metric       | Value                                     |
| ------------ | ----------------------------------------- |
| Total Files  | 59                                        |
| Total Lines  | ~12,000                                   |
| Largest File | `bhav_operands.py` (971 lines)            |
| Most Complex | `objm.py` (641 lines, nested dataclasses) |
| Deprecated   | `bhav_integration.py`                     |

---

## Usage Examples

### Reading an IFF file

```python
from src.formats.iff import IffFile
from src.formats.iff.chunks import OBJD, BHAV, STR

iff = IffFile.load("object.iff")
objd = iff.get_by_type_code("OBJD")[0]
print(f"Object: {objd.guid:08x}, Price: ${objd.price}")
```

### Decompiling all BHAVs

```python
from src.formats.iff.chunks.bhav_package_decompiler import decompile_iff_package

package_ast = decompile_iff_package("object.iff")
for bhav_id, metadata in package_ast.bhav_map.items():
    print(f"BHAV {bhav_id}: {metadata.instruction_count} instructions")
```

### Exporting Sprites

```python
from src.formats.iff.chunks.sprite_export import SPR2Decoder, export_sprite_png

decoder = SPR2Decoder(palette)
sprite = decoder.decode_frame(spr2.frames[0])
export_sprite_png(sprite, "output.png")
```

---

## Recommendations for Next Steps

1. **Priority 1**: Add `write()` to BHAV, OBJD, STR - enables basic modding
2. **Priority 2**: Complete SPR2 RLE decode - enables sprite extraction
3. **Priority 3**: Implement BHAV recompiler (AST→bytes) - closes the edit loop
4. **Cleanup**: Remove deprecated `bhav_integration.py`
5. **Testing**: Add unit tests for read→write→read roundtrip

---

_Generated from comprehensive file analysis. Last updated: See git log._
