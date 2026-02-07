// VitaMoo CMX/SKN parser — loads character data from text and binary files.
// CMX files contain skeleton definitions, suit definitions, and skill definitions.
// SKN files contain mesh geometry. BMF files are binary versions of SKN.

import { TextReader, BinaryReader } from './reader.js';
import {
    Vec3, Quat, vec3, quat,
    BoneData, SkeletonData, SkinData, SuitData, MotionData, SkillData,
    MeshData, Face, BoneBinding, BlendBinding, CMXFile,
} from './types.js';

// Read a Props block (key-value string pairs)
function readProps(r: TextReader): Map<string, string> {
    const count = r.readInt();
    const props = new Map<string, string>();
    for (let i = 0; i < count; i++) {
        const key = r.readString();
        const value = r.readString();
        props.set(key, value);
    }
    return props;
}

function readBone(r: TextReader): BoneData {
    const name = r.readString();
    const parentName = r.readString();
    const hasProps = r.readBool();
    const props = hasProps ? readProps(r) : new Map();
    const position = r.readVec3();
    const rotation = r.readQuat();
    const canTranslate = r.readBool();
    const canRotate = r.readBool();
    const canBlend = r.readBool();
    const canWiggle = r.readBool();
    const wigglePower = r.readFloat();
    return { name, parentName, position, rotation, canTranslate, canRotate,
             canBlend, canWiggle, wigglePower, props };
}

function readSkeleton(r: TextReader): SkeletonData {
    const name = r.readString();
    const boneCount = r.readInt();
    const bones: BoneData[] = [];
    for (let i = 0; i < boneCount; i++) {
        bones.push(readBone(r));
    }
    return { name, bones };
}

function readSkin(r: TextReader): SkinData {
    const name = r.readString();
    const boneName = r.readString();
    const flags = r.readInt();
    const meshName = r.readString();
    const hasProps = r.readBool();
    const props = hasProps ? readProps(r) : new Map();
    return { name, boneName, flags, meshName, props };
}

function readSuit(r: TextReader): SuitData {
    const name = r.readString();
    const type = r.readInt();
    const hasProps = r.readBool();
    const props = hasProps ? readProps(r) : new Map();
    const skinCount = r.readInt();
    const skins: SkinData[] = [];
    for (let i = 0; i < skinCount; i++) {
        skins.push(readSkin(r));
    }
    return { name, type, skins, props };
}

function readMotion(r: TextReader): MotionData {
    const boneName = r.readString();
    const frames = r.readInt();
    const duration = r.readFloat();
    const hasTranslation = r.readBool();
    const hasRotation = r.readBool();
    const translationsOffset = r.readInt();
    const rotationsOffset = r.readInt();
    const hasProps = r.readBool();
    const props = hasProps ? readProps(r) : new Map();
    const hasTimeProps = r.readBool();
    if (hasTimeProps) {
        // Read and discard time props for now
        const tpCount = r.readInt();
        for (let i = 0; i < tpCount; i++) {
            r.readInt(); // time key
            readProps(r); // props value
        }
    }
    return { boneName, frames, duration, hasTranslation, hasRotation,
             translationsOffset, rotationsOffset, props };
}

function readSkill(r: TextReader): SkillData {
    const name = r.readString();
    const animationFileName = r.readString();
    const duration = r.readFloat();
    const distance = r.readFloat();
    const isMoving = r.readBool();
    const numTranslations = r.readInt();
    const numRotations = r.readInt();
    const motionCount = r.readInt();
    const motions: MotionData[] = [];
    for (let i = 0; i < motionCount; i++) {
        motions.push(readMotion(r));
    }
    return { name, animationFileName, duration, distance, isMoving,
             numTranslations, numRotations, motions,
             translations: [], rotations: [] };
}

// Parse a CMX text file. Contains any combination of skeletons, suits, skills.
export function parseCMX(text: string): CMXFile {
    const r = new TextReader(text);
    const result: CMXFile = { skeletons: [], suits: [], skills: [] };

    // CMX format: version, then sections
    const version = r.readInt(); // usually 300

    const skeletonCount = r.readInt();
    for (let i = 0; i < skeletonCount; i++) {
        result.skeletons.push(readSkeleton(r));
    }

    const suitCount = r.readInt();
    for (let i = 0; i < suitCount; i++) {
        result.suits.push(readSuit(r));
    }

    const skillCount = r.readInt();
    for (let i = 0; i < skillCount; i++) {
        result.skills.push(readSkill(r));
    }

    return result;
}

// Parse a SKN text mesh file. Returns one MeshData.
export function parseSKN(text: string): MeshData {
    const r = new TextReader(text);
    const version = r.readInt(); // usually 300

    const name = r.readString();
    const textureName = r.readString();

    const boneCount = r.readInt();
    const boneNames: string[] = [];
    for (let i = 0; i < boneCount; i++) {
        boneNames.push(r.readString());
    }

    const faceCount = r.readInt();
    const faces: Face[] = [];
    for (let i = 0; i < faceCount; i++) {
        const parts = r.readLine().split(/\s+/);
        faces.push({
            a: parseInt(parts[0]) || 0,
            b: parseInt(parts[1]) || 0,
            c: parseInt(parts[2]) || 0,
        });
    }

    const bindingCount = r.readInt();
    const boneBindings: BoneBinding[] = [];
    for (let i = 0; i < bindingCount; i++) {
        boneBindings.push({
            boneIndex: r.readInt(),
            firstVertex: r.readInt(),
            vertexCount: r.readInt(),
            firstBlendedVertex: r.readInt(),
            blendedVertexCount: r.readInt(),
        });
    }

    const uvCount = r.readInt();
    const uvs = [];
    for (let i = 0; i < uvCount; i++) {
        uvs.push(r.readVec2());
    }

    const blendCount = r.readInt();
    const blendBindings: BlendBinding[] = [];
    for (let i = 0; i < blendCount; i++) {
        const otherVertexIndex = r.readInt();
        const fixedWeight = r.readInt();
        blendBindings.push({ otherVertexIndex, weight: fixedWeight / 0x8000 });
    }

    const vertexCount = r.readInt();
    const vertices: Vec3[] = [];
    const normals: Vec3[] = [];
    for (let i = 0; i < vertexCount; i++) {
        // Each vertex line: vx vy vz nx ny nz
        const parts = r.readLine().split(/\s+/).map(parseFloat);
        vertices.push(vec3(parts[0] || 0, parts[1] || 0, parts[2] || 0));
        normals.push(vec3(parts[3] || 0, parts[4] || 0, parts[5] || 0));
    }

    return { name, textureName, boneNames, faces, boneBindings,
             uvs, blendBindings, vertices, normals };
}

// Load compressed animation data from a CFP binary file
export function parseCFP(buffer: ArrayBuffer, skill: SkillData): void {
    const r = new BinaryReader(buffer);

    // Read translations
    if (skill.numTranslations > 0) {
        const floats = r.readCompressedFloats(skill.numTranslations * 3);
        skill.translations = [];
        for (let i = 0; i < skill.numTranslations; i++) {
            // Note: z is negated in the file format
            skill.translations.push(vec3(
                floats[i * 3], floats[i * 3 + 1], -floats[i * 3 + 2]
            ));
        }
    }

    // Read rotations
    if (skill.numRotations > 0) {
        const floats = r.readCompressedFloats(skill.numRotations * 4);
        skill.rotations = [];
        for (let i = 0; i < skill.numRotations; i++) {
            // Note: w is negated in the file format
            skill.rotations.push(quat(
                floats[i * 4], floats[i * 4 + 1],
                floats[i * 4 + 2], -floats[i * 4 + 3]
            ));
        }
    }
}
