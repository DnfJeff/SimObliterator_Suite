export interface Vec2 {
    x: number;
    y: number;
}
export interface Vec3 {
    x: number;
    y: number;
    z: number;
}
export interface Quat {
    x: number;
    y: number;
    z: number;
    w: number;
}
export declare const vec3: (x?: number, y?: number, z?: number) => Vec3;
export declare const quat: (x?: number, y?: number, z?: number, w?: number) => Quat;
export declare const vec2: (x?: number, y?: number) => Vec2;
export declare function vec3Add(a: Vec3, b: Vec3): Vec3;
export declare function vec3Scale(v: Vec3, s: number): Vec3;
export declare function vec3Lerp(a: Vec3, b: Vec3, t: number): Vec3;
export declare function quatMultiply(a: Quat, b: Quat): Quat;
export declare function quatRotateVec3(q: Quat, v: Vec3): Vec3;
export declare function quatSlerp(a: Quat, b: Quat, t: number): Quat;
export declare function quatNormalize(q: Quat): Quat;
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
export interface Bone extends BoneData {
    index: number;
    parent: Bone | null;
    children: Bone[];
    worldPosition: Vec3;
    worldRotation: Quat;
    priority: number;
}
export interface SkeletonData {
    name: string;
    bones: BoneData[];
}
export interface Face {
    a: number;
    b: number;
    c: number;
}
export interface BoneBinding {
    boneIndex: number;
    firstVertex: number;
    vertexCount: number;
    firstBlendedVertex: number;
    blendedVertexCount: number;
}
export interface BlendBinding {
    otherVertexIndex: number;
    weight: number;
}
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
export interface SkinData {
    name: string;
    boneName: string;
    flags: number;
    meshName: string;
    props: Map<string, string>;
}
export interface SuitData {
    name: string;
    type: number;
    skins: SkinData[];
    props: Map<string, string>;
}
export interface MotionData {
    boneName: string;
    frames: number;
    duration: number;
    hasTranslation: boolean;
    hasRotation: boolean;
    translationsOffset: number;
    rotationsOffset: number;
    props: Map<string, string>;
    timeProps: Map<number, Map<string, string>>;
}
export interface SkillData {
    name: string;
    animationFileName: string;
    duration: number;
    distance: number;
    isMoving: boolean;
    numTranslations: number;
    numRotations: number;
    motions: MotionData[];
    translations: Vec3[];
    rotations: Quat[];
}
export interface CMXFile {
    skeletons: SkeletonData[];
    suits: SuitData[];
    skills: SkillData[];
}
