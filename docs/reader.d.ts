import { Vec2, Vec3, Quat } from './types.js';
export interface DataReader {
    readString(): string;
    readInt(): number;
    readFloat(): number;
    readBool(): boolean;
    readVec2(): Vec2;
    readVec3(): Vec3;
    readQuat(): Quat;
}
export declare class TextReader implements DataReader {
    private lines;
    private pos;
    constructor(text: string);
    get hasMore(): boolean;
    readLine(): string;
    readString(): string;
    readInt(): number;
    readFloat(): number;
    readBool(): boolean;
    readVec2(): Vec2;
    readVec3(): Vec3;
    readQuat(): Quat;
}
export declare class BinaryReader implements DataReader {
    private view;
    private pos;
    constructor(buffer: ArrayBuffer);
    get hasMore(): boolean;
    get position(): number;
    set position(v: number);
    readByte(): number;
    readUint16(): number;
    readInt32(): number;
    readFloat32(): number;
    readString(): string;
    readBool(): boolean;
    readInt(): number;
    readFloat(): number;
    readVec2(): Vec2;
    readVec3(): Vec3;
    readQuat(): Quat;
}
export declare class BinaryWriter {
    private buffer;
    private view;
    private pos;
    constructor(initialSize?: number);
    get position(): number;
    private ensure;
    writeByte(v: number): void;
    writeUint16(v: number): void;
    writeInt32(v: number): void;
    writeFloat32(v: number): void;
    writeString(s: string): void;
    writeBool(v: boolean): void;
    writeVec2(v: Vec2): void;
    writeVec3(v: Vec3): void;
    writeQuat(q: Quat): void;
    writeBytes(data: Uint8Array): void;
    toArrayBuffer(): ArrayBuffer;
}
export declare function buildDeltaTable(): Float32Array;
export declare function decompressFloats(reader: BinaryReader, count: number, dims: number): Float32Array;
export declare function compressFloats(buf: Float32Array, count: number, dims: number): Uint8Array;
