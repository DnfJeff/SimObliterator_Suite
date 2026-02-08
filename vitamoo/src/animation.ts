// VitaMoo animation — Practice/Skill playback system.
//
// Implements the Practice system from the original vitaboy (Don Hopkins, Maxis, 1997)
// and the Unity C# VitaBoy reimplementation.
//
// "The Skill class represents a named set of Motions that can be applied
// to the Bones of a Skeleton by creating a Practice."
//
// A Practice binds a Skill to a Skeleton and manages playback:
//   - Tracks elapsed time (0.0 to 1.0 normalized)
//   - Computes frame indices from elapsed time
//   - Interpolates between keyframes (lerp for translations, slerp for rotations)
//   - Handles repeat modes (hold, loop, ping-pong)
//   - Each Motion in the Skill maps to a Bone by name
//   - Translations/rotations read from shared flat arrays at motion offsets

import {
    Vec3, Quat, Bone, SkillData, MotionData,
    vec3, quat, vec3Lerp, quatSlerp,
} from './types.js';

export const RepeatMode = {
    Hold: 0,
    Loop: 1,
    PingPong: 2,
    Fade: 3,
} as const;

export type RepeatModeType = typeof RepeatMode[keyof typeof RepeatMode];

interface PracticeBinding {
    motion: MotionData;
    bone: Bone;
}

export class Practice {
    skill: SkillData;
    bindings: PracticeBinding[];
    elapsed: number = 0;
    scale: number = 1;
    duration: number;
    repeatMode: RepeatModeType = RepeatMode.Loop;
    lastTicks: number = 0;
    ready: boolean = false;

    constructor(skill: SkillData, bones: Bone[]) {
        this.skill = skill;
        this.duration = skill.duration || 1999;

        const boneMap = new Map<string, Bone>();
        for (const bone of bones) boneMap.set(bone.name, bone);

        this.bindings = [];
        for (const motion of skill.motions) {
            const bone = boneMap.get(motion.boneName);
            if (bone) {
                this.bindings.push({ motion, bone });
            }
        }

        // Ready once CFP data is loaded
        this.ready = skill.translations.length > 0 || skill.rotations.length > 0;

        console.log(`[Practice] "${skill.name}" bindings=${this.bindings.length}/${skill.motions.length} duration=${this.duration}ms trans=${skill.translations.length} rots=${skill.rotations.length} ready=${this.ready}`);
    }

    tick(ticks: number): void {
        if (!this.ready) return;

        if (this.lastTicks === 0) {
            this.lastTicks = ticks;
            return;
        }

        const ticksDelta = ticks - this.lastTicks;
        this.lastTicks = ticks;

        if (this.duration <= 0 || this.scale === 0) return;

        const elapsedDelta = (ticksDelta / this.duration) * this.scale;
        this.elapsed += elapsedDelta;

        // Handle repeat modes when elapsed goes out of [0, 1]
        if (this.elapsed >= 1.0 || this.elapsed < 0) {
            switch (this.repeatMode) {
                case RepeatMode.Hold:
                    this.elapsed = Math.max(0, Math.min(1, this.elapsed));
                    this.scale = 0;
                    break;
                case RepeatMode.Loop:
                    this.elapsed = this.elapsed - Math.floor(this.elapsed);
                    if (this.elapsed < 0) this.elapsed += 1;
                    break;
                case RepeatMode.PingPong:
                    this.scale = -this.scale;
                    this.elapsed = this.elapsed - Math.floor(this.elapsed);
                    if (this.elapsed < 0) this.elapsed = 1 + this.elapsed;
                    break;
                case RepeatMode.Fade:
                    this.elapsed = Math.max(0, Math.min(1, this.elapsed));
                    this.scale = 0;
                    break;
            }
        }

        this.applyMotions();
    }

    private applyMotions(): void {
        const skill = this.skill;

        for (const { motion, bone } of this.bindings) {
            const frames = motion.frames;
            if (frames <= 0) continue;

            // Compute frame position: elapsed [0,1] maps to [0, frames]
            const frameReal = Math.max(0, Math.min(frames - 0.001, frames * this.elapsed));
            const frame = Math.floor(frameReal);
            const tween = frameReal - frame;

            // Next frame for interpolation (wrap for looping)
            let nextFrame = frame + 1;
            if (nextFrame >= frames) {
                nextFrame = this.repeatMode === RepeatMode.Loop ? 0 : frame;
            }

            // Apply translation: lerp between frame and nextFrame.
            // Skip root bone translation for non-moving skills to keep feet planted.
            // In the original game, the pathfinder compensated for root movement;
            // in the viewer we suppress it to prevent sliding.
            const isRoot = !bone.parent;
            const suppressRootTranslation = isRoot && !skill.isMoving;
            if (motion.hasTranslation && skill.translations.length > 0 && !suppressRootTranslation) {
                const i0 = motion.translationsOffset + frame;
                const i1 = motion.translationsOffset + nextFrame;
                if (i0 < skill.translations.length) {
                    const t0 = skill.translations[i0];
                    const t1 = i1 < skill.translations.length ? skill.translations[i1] : t0;
                    bone.position = tween > 0.001 ? vec3Lerp(t0, t1, tween) : t0;
                }
            }

            // Apply rotation: slerp between frame and nextFrame
            if (motion.hasRotation && skill.rotations.length > 0) {
                const i0 = motion.rotationsOffset + frame;
                const i1 = motion.rotationsOffset + nextFrame;
                if (i0 < skill.rotations.length) {
                    const r0 = skill.rotations[i0];
                    const r1 = i1 < skill.rotations.length ? skill.rotations[i1] : r0;
                    bone.rotation = tween > 0.001 ? quatSlerp(r0, r1, tween) : r0;
                }
            }
        }
    }
}
