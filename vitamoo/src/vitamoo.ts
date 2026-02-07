// VitaMoo — main entry point.
// Loads Sims 1 character data (CMX, SKN, CFP) and renders via WebGL.

export { Vec2, Vec3, Quat, Bone, SkeletonData, MeshData, SuitData, SkillData, CMXFile } from './types.js';
export { parseCMX, parseSKN, parseCFP } from './parser.js';
export { buildSkeleton, findRoot, findBone, updateTransforms, deformMesh } from './skeleton.js';
export { Renderer } from './renderer.js';
export { TextReader, BinaryReader } from './reader.js';
export { parseBMP, loadTexture } from './texture.js';
