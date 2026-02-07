// VitaMoo file reader — parses CMX (text), SKN (text), BMF (binary), CFP (binary).
// CMX files contain skeletons, suits, and skill definitions.
// SKN/BMF files contain mesh geometry (vertices, normals, faces, UVs, bone bindings).
// CFP files contain compressed animation keyframe data.

import { Vec2, Vec3, Quat, vec2, vec3, quat } from './types.js';

// Text file reader (line-oriented, for CMX and SKN files)
export class TextReader {
    private lines: string[];
    private pos = 0;

    constructor(text: string) {
        this.lines = text.split(/\r?\n/);
    }

    get hasMore(): boolean { return this.pos < this.lines.length; }

    readLine(): string {
        if (this.pos >= this.lines.length) return '';
        return this.lines[this.pos++].trim();
    }

    readString(): string { return this.readLine(); }

    readInt(): number {
        const v = parseInt(this.readLine(), 10);
        return isNaN(v) ? 0 : v;
    }

    readFloat(): number {
        const v = parseFloat(this.readLine());
        return isNaN(v) ? 0 : v;
    }

    readBool(): boolean {
        const s = this.readLine().toLowerCase();
        return s === '1' || s === 'true' || s === 'yes';
    }

    readVec2(): Vec2 {
        const parts = this.readLine().split(/\s+/);
        return vec2(parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0);
    }

    readVec3(): Vec3 {
        const parts = this.readLine().split(/\s+/);
        return vec3(parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0, parseFloat(parts[2]) || 0);
    }

    readQuat(): Quat {
        const parts = this.readLine().split(/\s+/);
        return quat(
            parseFloat(parts[0]) || 0, parseFloat(parts[1]) || 0,
            parseFloat(parts[2]) || 0, parseFloat(parts[3]) || 1,
        );
    }
}

// Binary file reader (for BMF and CFP files)
export class BinaryReader {
    private view: DataView;
    private pos = 0;
    private littleEndian: boolean;

    constructor(buffer: ArrayBuffer, littleEndian = true) {
        this.view = new DataView(buffer);
        this.littleEndian = littleEndian;
    }

    get hasMore(): boolean { return this.pos < this.view.byteLength; }
    get position(): number { return this.pos; }

    readByte(): number {
        return this.view.getUint8(this.pos++);
    }

    readInt16(): number {
        const v = this.view.getInt16(this.pos, this.littleEndian);
        this.pos += 2;
        return v;
    }

    readInt32(): number {
        const v = this.view.getInt32(this.pos, this.littleEndian);
        this.pos += 4;
        return v;
    }

    readFloat32(): number {
        const v = this.view.getFloat32(this.pos, this.littleEndian);
        this.pos += 4;
        return v;
    }

    readString(): string {
        const len = this.readInt32();
        const bytes = new Uint8Array(this.view.buffer, this.pos, len);
        this.pos += len;
        // Trim null terminator if present
        const end = bytes.indexOf(0);
        const slice = end >= 0 ? bytes.subarray(0, end) : bytes;
        return new TextDecoder('latin1').decode(slice);
    }

    readBool(): boolean { return this.readByte() !== 0; }

    readVec2(): Vec2 {
        return vec2(this.readFloat32(), this.readFloat32());
    }

    readVec3(): Vec3 {
        return vec3(this.readFloat32(), this.readFloat32(), this.readFloat32());
    }

    readQuat(): Quat {
        return quat(this.readFloat32(), this.readFloat32(),
                    this.readFloat32(), this.readFloat32());
    }

    // CFP delta-compressed float decompression
    readCompressedFloats(count: number): number[] {
        const result = new Array<number>(count).fill(0);
        const deltaTable = buildDeltaTable();

        for (let col = 0; col < count; col++) {
            let value = 0;
            // First value is always a full float
            if (this.hasMore) {
                const code = this.readByte();
                if (code === 255) {
                    // Jump: read full float
                    value = this.readFloat32();
                } else if (code === 254) {
                    // Repeat: same as previous
                } else if (code < 253) {
                    value = deltaTable[code];
                }
            }
            result[col] = value;
        }
        return result;
    }
}

// Build the delta lookup table for CFP compression
// 253 entries mapping byte codes to delta values
function buildDeltaTable(): number[] {
    const epsilon = 0.00001;
    const spread = 0.1;
    const table: number[] = [];
    for (let i = 0; i < 253; i++) {
        const normalized = (i - 126) / 126.0; // -1 to +1
        table.push(normalized * spread);
    }
    return table;
}
