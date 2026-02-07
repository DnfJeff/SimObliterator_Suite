// VitaMoo core types — data structures for skeleton, mesh, and animation.
// Clean-room TypeScript, translated from C# patterns.

export interface Vec2 { x: number; y: number }
export interface Vec3 { x: number; y: number; z: number }
export interface Quat { x: number; y: number; z: number; w: number }

export const vec3 = (x = 0, y = 0, z = 0): Vec3 => ({ x, y, z });
export const quat = (x = 0, y = 0, z = 0, w = 1): Quat => ({ x, y, z, w });
export const vec2 = (x = 0, y = 0): Vec2 => ({ x, y });

export function vec3Add(a: Vec3, b: Vec3): Vec3 {
    return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

export function vec3Scale(v: Vec3, s: number): Vec3 {
    return { x: v.x * s, y: v.y * s, z: v.z * s };
}

export function vec3Lerp(a: Vec3, b: Vec3, t: number): Vec3 {
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t };
}

export function quatMultiply(a: Quat, b: Quat): Quat {
    return {
        x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
        y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
        z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
    };
}

export function quatRotateVec3(q: Quat, v: Vec3): Vec3 {
    // Rotate vector by quaternion: q * v * q_conjugate
    const qv: Quat = { x: v.x, y: v.y, z: v.z, w: 0 };
    const qc: Quat = { x: -q.x, y: -q.y, z: -q.z, w: q.w };
    const r = quatMultiply(quatMultiply(q, qv), qc);
    return { x: r.x, y: r.y, z: r.z };
}

export function quatSlerp(a: Quat, b: Quat, t: number): Quat {
    let dot = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w;
    // Ensure shortest path
    let bx = b.x, by = b.y, bz = b.z, bw = b.w;
    if (dot < 0) { dot = -dot; bx = -bx; by = -by; bz = -bz; bw = -bw; }
    if (dot > 0.9995) {
        // Close enough for linear interpolation
        return quatNormalize({
            x: a.x + (bx - a.x) * t, y: a.y + (by - a.y) * t,
            z: a.z + (bz - a.z) * t, w: a.w + (bw - a.w) * t,
        });
    }
    const theta = Math.acos(dot);
    const sinTheta = Math.sin(theta);
    const wa = Math.sin((1 - t) * theta) / sinTheta;
    const wb = Math.sin(t * theta) / sinTheta;
    return {
        x: wa * a.x + wb * bx, y: wa * a.y + wb * by,
        z: wa * a.z + wb * bz, w: wa * a.w + wb * bw,
    };
}

export function quatNormalize(q: Quat): Quat {
    const len = Math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
    if (len < 0.0001) return { x: 0, y: 0, z: 0, w: 1 };
    return { x: q.x / len, y: q.y / len, z: q.z / len, w: q.w / len };
}

// Bone in a skeleton hierarchy
export interface BoneData {
    name: string;
    parentName: string;
    position: Vec3;
    rotation: Quat;
    canTranslate: boolean;
    canRotate: boolean;
    canBlend: boolean;
    canWiggle: boolean;
    wigglePower: number;
    props: Map<string, string>;
}

// Runtime bone with world transforms
export interface Bone extends BoneData {
    index: number;
    parent: Bone | null;
    children: Bone[];
    worldPosition: Vec3;
    worldRotation: Quat;
    priority: number;
}

// Skeleton: bone hierarchy
export interface SkeletonData {
    name: string;
    bones: BoneData[];
}

// Triangle face
export interface Face { a: number; b: number; c: number }

// How vertices bind to a bone
export interface BoneBinding {
    boneIndex: number;
    firstVertex: number;
    vertexCount: number;
    firstBlendedVertex: number;
    blendedVertexCount: number;
}

// Blend between two vertex positions
export interface BlendBinding {
    otherVertexIndex: number;
    weight: number;
}

// A deformable mesh (body part)
export interface MeshData {
    name: string;
    textureName: string;
    boneNames: string[];
    faces: Face[];
    boneBindings: BoneBinding[];
    uvs: Vec2[];
    blendBindings: BlendBinding[];
    vertices: Vec3[];
    normals: Vec3[];
}

// A skin wraps a mesh and binds it to a specific bone
export interface SkinData {
    name: string;
    boneName: string;
    flags: number;
    meshName: string;
    props: Map<string, string>;
}

// A suit is a collection of skins (head suit, body suit, hand suits)
export interface SuitData {
    name: string;
    type: number;      // 0=normal, 1=censor
    skins: SkinData[];
    props: Map<string, string>;
}

// A motion animates one bone
export interface MotionData {
    boneName: string;
    frames: number;
    duration: number;
    hasTranslation: boolean;
    hasRotation: boolean;
    translationsOffset: number;
    rotationsOffset: number;
    props: Map<string, string>;
}

// A skill is a named animation containing motions for multiple bones
export interface SkillData {
    name: string;
    animationFileName: string;
    duration: number;
    distance: number;
    isMoving: boolean;
    numTranslations: number;
    numRotations: number;
    motions: MotionData[];
    translations: Vec3[];    // filled when animation file is loaded
    rotations: Quat[];       // filled when animation file is loaded
}

// A CMX file can contain any combination of skeletons, suits, and skills
export interface CMXFile {
    skeletons: SkeletonData[];
    suits: SuitData[];
    skills: SkillData[];
}
