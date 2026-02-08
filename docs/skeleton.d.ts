import { Vec3, Bone, SkeletonData, MeshData } from './types.js';
export declare function buildSkeleton(data: SkeletonData): Bone[];
export declare function findRoot(bones: Bone[]): Bone | null;
export declare function findBone(bones: Bone[], name: string): Bone | null;
export declare function updateTransforms(bones: Bone[]): void;
export declare function deformMesh(mesh: MeshData, bones: Bone[], boneMap: Map<string, Bone>): {
    vertices: Vec3[];
    normals: Vec3[];
};
