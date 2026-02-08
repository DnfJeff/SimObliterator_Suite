// VitaMoo core types — data structures for skeleton, mesh, and animation.
//
// The naming vocabulary is an extended metaphor of body and performance,
// from the original VitaBoy C++ code (Don Hopkins, Maxis, 1997),
// inspired by Ken Perlin's "Improv" system for scripting interactive
// actors in virtual worlds (Perlin & Goldberg, SIGGRAPH '96).
//
// Improv separated character animation into an Animation Engine (layered,
// continuous, non-repetitive motions with smooth transitions) and a
// Behavior Engine (rules governing how actors communicate and decide).
// Actions were organized into compositing groups — actions in the same
// group competed (one fades in, others fade out), while actions in
// different groups layered like image compositing (back to front).
// Perlin's key insight: "the author thinks of motion as being layered,
// just as composited images can be layered back to front. The difference
// is that whereas an image maps pixels to colors, an action maps DOFs
// to values."
//
// Vitaboy's Practice/Skill/Motion system implements this same layered
// architecture: Practices have priorities, opaque practices occlude
// lower-priority ones on the same bones, and multiple practices blend
// via weighted averaging. The vocabulary below carries Improv's spirit
// into a game engine that shipped to millions:
//
//   Skeleton  — bone hierarchy (the body's structure)
//   Bone      — translated/rotated coordinate system node
//   Skin      — a mesh attached to a bone, rendered in its coordinate system
//   Suit      — a named set of Skins (an outfit)
//   Dressing  — binding a Suit to a Skeleton (the act of wearing)
//   Skill     — a named set of Motions (a learned ability)
//   Practice  — binding a Skill to a Skeleton (doing the skill)
//   Motion    — translation/rotation keyframe stream for one bone
//
// You "dress" a Skeleton in a Suit (creating a Dressing), and a Skeleton
// "practices" a Skill (creating a Practice). The language makes the API
// self-documenting.
//
// The animation data lives in shared buffers rather than per-motion:
// "All the data of all the motions are shared and managed by the Skill,
// so they can all be read in quickly as one chunk." This reduces
// fragmentation and load time — each Motion just stores offsets into
// the Skill's flat translation and rotation arrays.
export const vec3 = (x = 0, y = 0, z = 0) => ({ x, y, z });
export const quat = (x = 0, y = 0, z = 0, w = 1) => ({ x, y, z, w });
export const vec2 = (x = 0, y = 0) => ({ x, y });
export function vec3Add(a, b) {
    return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}
export function vec3Scale(v, s) {
    return { x: v.x * s, y: v.y * s, z: v.z * s };
}
export function vec3Lerp(a, b, t) {
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t };
}
export function quatMultiply(a, b) {
    return {
        x: a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
        y: a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
        z: a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        w: a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
    };
}
export function quatRotateVec3(q, v) {
    // Rotate vector by quaternion: q * v * q_conjugate
    const qv = { x: v.x, y: v.y, z: v.z, w: 0 };
    const qc = { x: -q.x, y: -q.y, z: -q.z, w: q.w };
    const r = quatMultiply(quatMultiply(q, qv), qc);
    return { x: r.x, y: r.y, z: r.z };
}
export function quatSlerp(a, b, t) {
    let dot = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w;
    // Ensure shortest path
    let bx = b.x, by = b.y, bz = b.z, bw = b.w;
    if (dot < 0) {
        dot = -dot;
        bx = -bx;
        by = -by;
        bz = -bz;
        bw = -bw;
    }
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
export function quatNormalize(q) {
    const len = Math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
    if (len < 0.0001)
        return { x: 0, y: 0, z: 0, w: 1 };
    return { x: q.x / len, y: q.y / len, z: q.z / len, w: q.w / len };
}
//# sourceMappingURL=types.js.map