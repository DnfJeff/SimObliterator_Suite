// VitaMoo file reader/writer — text and binary I/O for The Sims character data.
//
// Text formats (CMX, SKN): line-oriented, one value per line.
// Binary formats (BMF, BCF, CFP): CTGFile-compatible, little-endian.
//
// The same data structures flow through both pipelines. A character's
// skeleton, mesh, and animation can be loaded from text files (as Maxis
// developers did 26 years ago) or from the binary formats the game
// runtime actually ships. The binary readers and writers here implement
// the original CTGFile protocol faithfully — every string is length-
// prefixed, every integer is 4 bytes little-endian, and the CFP delta
// compression uses the same quartic distribution table that's been
// decompressing walk cycles since the year 2000.
import { vec2, vec3, quat } from './types.js';
// Text file reader — parses line-oriented formats (CMX, SKN).
// Each primitive value occupies one line. Multi-value lines (faces, bindings)
// are handled by parseSKN using readLine() directly.
export class TextReader {
    constructor(text) {
        this.pos = 0;
        this.lines = text.split(/\r?\n/);
    }
    get hasMore() { return this.pos < this.lines.length; }
    readLine() {
        // Skip blank lines and comment lines (// ...)
        while (this.pos < this.lines.length) {
            const line = this.lines[this.pos++].trim();
            if (line === '' || line.startsWith('//'))
                continue;
            return line;
        }
        return '';
    }
    readString() { return this.readLine(); }
    readInt() {
        const v = parseInt(this.readLine(), 10);
        return isNaN(v) ? 0 : v;
    }
    readFloat() {
        const v = parseFloat(this.readLine());
        return isNaN(v) ? 0 : v;
    }
    readBool() {
        const s = this.readLine().toLowerCase();
        return s === '1' || s === 'true' || s === 'yes';
    }
    readVec2() {
        // Text CMX format: "u v" or "| u v |" (pipe-delimited)
        const parts = this.readLine().replace(/\|/g, '').trim().split(/\s+/);
        return vec2(parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0);
    }
    readVec3() {
        // Text CMX format: "x y z" or "| x y z |" (pipe-delimited)
        const parts = this.readLine().replace(/\|/g, '').trim().split(/\s+/);
        return vec3(parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0, parseFloat(parts[2]) || 0);
    }
    readQuat() {
        // Text CMX format: "x y z w" or "| x y z w |" (pipe-delimited)
        const parts = this.readLine().replace(/\|/g, '').trim().split(/\s+/);
        return quat(parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0, parseFloat(parts[2]) || 0, parseFloat(parts[3]) || 1);
    }
}
// Binary file reader — CTGFile-compatible, little-endian.
// Handles BMF (meshes), BCF (compiled skeletons/suits/skills), and CFP streams.
export class BinaryReader {
    constructor(buffer) {
        this.pos = 0;
        this.view = new DataView(buffer);
    }
    get hasMore() { return this.pos < this.view.byteLength; }
    get position() { return this.pos; }
    set position(v) { this.pos = v; }
    readByte() {
        return this.view.getUint8(this.pos++);
    }
    readUint16() {
        const v = this.view.getUint16(this.pos, true);
        this.pos += 2;
        return v;
    }
    readInt32() {
        const v = this.view.getInt32(this.pos, true);
        this.pos += 4;
        return v;
    }
    readFloat32() {
        const v = this.view.getFloat32(this.pos, true);
        this.pos += 4;
        return v;
    }
    // CTGFile string encoding: 1-byte length, or 0xFF marker + 4-byte int32 length
    // for strings >= 255 chars. Character data follows immediately, no null terminator.
    readString() {
        let len = this.readByte();
        if (len === 255) {
            len = this.readInt32();
        }
        const bytes = new Uint8Array(this.view.buffer, this.view.byteOffset + this.pos, len);
        this.pos += len;
        return new TextDecoder('latin1').decode(bytes);
    }
    // BCF/BMF booleans are int32 (0 or 1), matching CTGFile::WriteInteger.
    readBool() {
        return this.readInt32() !== 0;
    }
    // DataReader interface — readInt and readFloat map to the 32-bit LE versions.
    readInt() { return this.readInt32(); }
    readFloat() { return this.readFloat32(); }
    readVec2() {
        return vec2(this.readFloat32(), this.readFloat32());
    }
    readVec3() {
        return vec3(this.readFloat32(), this.readFloat32(), this.readFloat32());
    }
    readQuat() {
        return quat(this.readFloat32(), this.readFloat32(), this.readFloat32(), this.readFloat32());
    }
}
// Binary file writer — produces CTGFile-compatible output.
// Grows its internal buffer as needed. Call toArrayBuffer() to finalize.
export class BinaryWriter {
    constructor(initialSize = 8192) {
        this.pos = 0;
        this.buffer = new ArrayBuffer(initialSize);
        this.view = new DataView(this.buffer);
    }
    get position() { return this.pos; }
    ensure(bytes) {
        if (this.pos + bytes <= this.buffer.byteLength)
            return;
        const newSize = Math.max(this.buffer.byteLength * 2, this.pos + bytes);
        const newBuf = new ArrayBuffer(newSize);
        new Uint8Array(newBuf).set(new Uint8Array(this.buffer));
        this.buffer = newBuf;
        this.view = new DataView(this.buffer);
    }
    writeByte(v) {
        this.ensure(1);
        this.view.setUint8(this.pos++, v);
    }
    writeUint16(v) {
        this.ensure(2);
        this.view.setUint16(this.pos, v, true);
        this.pos += 2;
    }
    writeInt32(v) {
        this.ensure(4);
        this.view.setInt32(this.pos, v, true);
        this.pos += 4;
    }
    writeFloat32(v) {
        this.ensure(4);
        this.view.setFloat32(this.pos, v, true);
        this.pos += 4;
    }
    // CTGFile string format: 1-byte length prefix, or 0xFF + 4-byte int32
    // for strings >= 255 chars. No null terminator.
    writeString(s) {
        const encoded = new TextEncoder().encode(s);
        if (encoded.length < 255) {
            this.writeByte(encoded.length);
        }
        else {
            this.writeByte(255);
            this.writeInt32(encoded.length);
        }
        this.ensure(encoded.length);
        new Uint8Array(this.buffer, this.pos, encoded.length).set(encoded);
        this.pos += encoded.length;
    }
    writeBool(v) {
        this.writeInt32(v ? 1 : 0);
    }
    writeVec2(v) {
        this.writeFloat32(v.x);
        this.writeFloat32(v.y);
    }
    writeVec3(v) {
        this.writeFloat32(v.x);
        this.writeFloat32(v.y);
        this.writeFloat32(v.z);
    }
    writeQuat(q) {
        this.writeFloat32(q.x);
        this.writeFloat32(q.y);
        this.writeFloat32(q.z);
        this.writeFloat32(q.w);
    }
    writeBytes(data) {
        this.ensure(data.length);
        new Uint8Array(this.buffer, this.pos, data.length).set(data);
        this.pos += data.length;
    }
    toArrayBuffer() {
        return this.buffer.slice(0, this.pos);
    }
}
// --- CFP Delta Compression ---
//
// The delta table maps byte codes 0-252 to float deltas via a quartic curve.
// Values concentrate near zero — most animation keyframe deltas are tiny —
// then sweep out to ±0.1 at the extremes. Entry 126 is exactly zero.
//
// The key insight: compress COLUMNS, not rows. Instead of delta-encoding
// (x,y,z) tuples where all three components jump around, we process all
// X values first, then all Y values, then all Z values. Within a single
// dimension, consecutive keyframe values change very little. The deltas
// are tiny, and the quartic table concentrates 253 code points right
// near zero where they're needed most.
//
// The epsilon values and spread were "determined from histogram" — the
// full animation database was run through the codec and the parameters
// tuned to the actual data distribution over several iterations.
//
// When the delta between consecutive values exceeds the table's range,
// a JUMP code (255) writes the full float. For long runs of identical
// values, a REPEAT code (254) + uint16 count collapses them.
// Code 253 is unused/reserved. Codes 0-252 are delta lookups.
//
// The original code had an incomplete binary search for the closest
// delta table entry: "booboo: Brute force for now... It could be a
// binary search." (booboo = Eric Bowman, Maxis engineer.)
// The brute force was good enough. It shipped.
//
// The Sims shipped in February 2000 with this compression scheme
// decompressing every walk cycle, gesture, and idle fidget. The Sims
// franchise has since generated over $5 billion in lifetime revenue.
// Sometimes "good enough" ships for 26 years.
const DELTA_TABLE_SIZE = 253;
const SPREAD = 0.1;
const DELTA_EPSILON = 0.00001;
const DELTA_EPSILON_SMALL = 0.000001;
let _deltaTable = null;
// Build the quartic delta table. Cached after first call.
// 253 entries, range approximately -0.1 to +0.1, entry 126 ≈ 0.
export function buildDeltaTable() {
    if (_deltaTable)
        return _deltaTable;
    const table = new Float32Array(DELTA_TABLE_SIZE);
    for (let i = 0; i < DELTA_TABLE_SIZE; i++) {
        const unitRange = i / (DELTA_TABLE_SIZE - 1);
        const val = 2.0 * unitRange - 1.0;
        const sgn = val < 0 ? -1.0 : 1.0;
        // Quartic curve: sgn * |val|^4 * spread
        // Concentrates precision near zero where small animation deltas live.
        table[i] = sgn * val * val * val * val * SPREAD;
    }
    _deltaTable = table;
    return table;
}
// Decompress a CFP byte stream into an interleaved float buffer.
//
// The stream is organized dimension-first: all Xs, then all Ys, then all Zs
// for vec3 translations. Output is interleaved: [x0,y0,z0, x1,y1,z1, ...].
//
// Byte codes:
//   0-252  DELTA: accumulator += deltaTable[code]
//   253    (unused/reserved)
//   254    REPEAT + uint16: output current value (repeatCount + 1) more times
//   255    JUMP + float32: set accumulator to absolute value
//
// The accumulator carries across dimension boundaries, though in practice
// the encoder always emits a JUMP at the start of each new dimension.
export function decompressFloats(reader, count, dims) {
    const deltaTable = buildDeltaTable();
    const buf = new Float32Array(count * dims);
    let val = 0;
    let repeat = 0;
    for (let dim = 0; dim < dims; dim++) {
        for (let i = 0; i < count; i++) {
            if (repeat > 0) {
                repeat--;
            }
            else {
                const code = reader.readByte();
                if (code === 255) {
                    val = reader.readFloat32();
                }
                else if (code === 254) {
                    repeat = reader.readUint16();
                }
                else {
                    val += deltaTable[code];
                }
            }
            buf[dim + i * dims] = val;
        }
    }
    return buf;
}
// Compress an interleaved float buffer into a CFP byte stream.
//
// Processes dimension-first (all Xs, then Ys, etc.) to maximize delta coherence.
// Uses the quartic delta table for small changes, JUMP for large changes,
// and REPEAT to collapse runs of identical values.
export function compressFloats(buf, count, dims) {
    const deltaTable = buildDeltaTable();
    const minDelta = deltaTable[0];
    const maxDelta = deltaTable[DELTA_TABLE_SIZE - 1];
    const out = [];
    let val = 0;
    let repeat = 0;
    let jump;
    for (let dim = 0; dim < dims; dim++) {
        jump = true; // force absolute JUMP on first value of each dimension
        for (let i = 0; i < count; i++) {
            const newVal = buf[dim + i * dims];
            const diff = newVal - val;
            const diffAbs = Math.abs(diff);
            // Check if value is close enough to count as a repeat.
            // Looser threshold when already repeating (easy to continue),
            // tighter threshold otherwise (harder to start a new run).
            if (!jump &&
                (repeat > 0 ? diffAbs < DELTA_EPSILON : diffAbs < DELTA_EPSILON_SMALL)) {
                repeat++;
                if (repeat === 0xFFFF) {
                    out.push(254);
                    pushUint16LE(out, repeat - 1);
                    repeat = 0;
                }
            }
            else {
                // Flush any pending repeat run
                if (repeat > 0) {
                    out.push(254);
                    pushUint16LE(out, repeat - 1);
                    repeat = 0;
                }
                if (jump || diff < minDelta || diff > maxDelta) {
                    // Delta out of range — emit absolute JUMP
                    jump = false;
                    out.push(255);
                    pushFloat32LE(out, newVal);
                    val = newVal;
                }
                else {
                    // Find the closest delta table entry
                    let bestError = Infinity;
                    let bestCode = 0;
                    for (let j = 0; j < DELTA_TABLE_SIZE; j++) {
                        const error = Math.abs(newVal - (val + deltaTable[j]));
                        if (error < bestError) {
                            bestError = error;
                            bestCode = j;
                        }
                    }
                    out.push(bestCode);
                    val += deltaTable[bestCode];
                }
            }
        }
    }
    // Flush trailing repeat
    if (repeat > 0) {
        out.push(254);
        pushUint16LE(out, repeat - 1);
    }
    return new Uint8Array(out);
}
function pushUint16LE(out, v) {
    out.push(v & 0xFF, (v >> 8) & 0xFF);
}
function pushFloat32LE(out, v) {
    const tmp = new ArrayBuffer(4);
    new DataView(tmp).setFloat32(0, v, true);
    const bytes = new Uint8Array(tmp);
    out.push(bytes[0], bytes[1], bytes[2], bytes[3]);
}
//# sourceMappingURL=reader.js.map