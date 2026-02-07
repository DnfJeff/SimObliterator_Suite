// VitaMoo skeleton — bone hierarchy, transform propagation, mesh deformation.

import {
    Vec3, Quat, Bone, BoneData, SkeletonData, MeshData,
    vec3, quat, vec3Add, quatMultiply, quatRotateVec3, quatSlerp, vec3Lerp,
} from './types.js';

// Create runtime bones from skeleton data, linking parent/child relationships
export function buildSkeleton(data: SkeletonData): Bone[] {
    const bones: Bone[] = data.bones.map((bd, i) => ({
        ...bd,
        index: i,
        parent: null,
        children: [],
        worldPosition: vec3(),
        worldRotation: quat(),
        priority: 0,
    }));

    // Link parents and children
    const byName = new Map<string, Bone>();
    for (const bone of bones) byName.set(bone.name, bone);
    for (const bone of bones) {
        if (bone.parentName) {
            bone.parent = byName.get(bone.parentName) ?? null;
            if (bone.parent) bone.parent.children.push(bone);
        }
    }
    return bones;
}

// Find the root bone (no parent)
export function findRoot(bones: Bone[]): Bone | null {
    return bones.find(b => !b.parent) ?? null;
}

// Find a bone by name
export function findBone(bones: Bone[], name: string): Bone | null {
    return bones.find(b => b.name === name) ?? null;
}

// Propagate transforms from root to leaves.
// Each bone's world transform = parent world transform * local transform.
export function updateTransforms(bones: Bone[]): void {
    const root = findRoot(bones);
    if (!root) return;
    propagate(root, vec3(), quat());
}

function propagate(bone: Bone, parentPos: Vec3, parentRot: Quat): void {
    bone.worldPosition = vec3Add(parentPos, quatRotateVec3(parentRot, bone.position));
    bone.worldRotation = quatMultiply(parentRot, bone.rotation);
    for (const child of bone.children) {
        propagate(child, bone.worldPosition, bone.worldRotation);
    }
}

// Deform a mesh by its bone bindings.
// Transforms each vertex from rest pose to world pose using its bound bone.
// Returns new vertex and normal arrays (same length as mesh.vertices).
export function deformMesh(
    mesh: MeshData,
    bones: Bone[],
    boneMap: Map<string, Bone>,
): { vertices: Vec3[]; normals: Vec3[] } {
    const outVerts: Vec3[] = new Array(mesh.vertices.length);
    const outNorms: Vec3[] = new Array(mesh.normals.length);

    // Transform vertices by their bound bone
    for (const binding of mesh.boneBindings) {
        const boneName = mesh.boneNames[binding.boneIndex];
        const bone = boneMap.get(boneName);
        if (!bone) continue;

        for (let i = 0; i < binding.vertexCount; i++) {
            const vi = binding.firstVertex + i;
            outVerts[vi] = vec3Add(bone.worldPosition,
                                   quatRotateVec3(bone.worldRotation, mesh.vertices[vi]));
            outNorms[vi] = quatRotateVec3(bone.worldRotation, mesh.normals[vi]);
        }
    }

    // Apply blend bindings (weighted average between two positions)
    for (const blend of mesh.blendBindings) {
        const ovi = blend.otherVertexIndex;
        if (outVerts[ovi]) {
            // Blend this vertex toward the other vertex position
            // The weight determines how much of the "other" position to use
        }
    }

    return { vertices: outVerts, normals: outNorms };
}
