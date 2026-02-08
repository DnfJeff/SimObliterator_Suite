// VitaMoo — main entry point.
// Loads Sims 1 character data and renders via WebGL.
//
// Supports both text formats (CMX, SKN — the development tools)
// and binary formats (BCF, BMF, CFP — the game runtime).
export { parseCMX, parseSKN, parseBCF, parseBMF, parseCFP, writeCMX, writeSKN, writeReport, writeBCF, writeBMF, writeCFP, } from './parser.js';
export { buildSkeleton, findRoot, findBone, updateTransforms, deformMesh } from './skeleton.js';
export { Renderer } from './renderer.js';
export { TextReader, BinaryReader, BinaryWriter, buildDeltaTable, decompressFloats, compressFloats, } from './reader.js';
export { parseBMP, loadTexture } from './texture.js';
export { Practice, RepeatMode } from './animation.js';
//# sourceMappingURL=vitamoo.js.map