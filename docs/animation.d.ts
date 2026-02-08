import { Bone, SkillData, MotionData } from './types.js';
export declare const RepeatMode: {
    readonly Hold: 0;
    readonly Loop: 1;
    readonly PingPong: 2;
    readonly Fade: 3;
};
export type RepeatModeType = typeof RepeatMode[keyof typeof RepeatMode];
interface PracticeBinding {
    motion: MotionData;
    bone: Bone;
}
export declare class Practice {
    skill: SkillData;
    bindings: PracticeBinding[];
    elapsed: number;
    scale: number;
    duration: number;
    repeatMode: RepeatModeType;
    lastTicks: number;
    ready: boolean;
    constructor(skill: SkillData, bones: Bone[]);
    tick(ticks: number): void;
    private applyMotions;
}
export {};
