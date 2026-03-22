/// <reference types="@webgpu/types" />
import { Renderer, ObjectIdType, updateTransforms, deformMesh, loadGltfMeshes } from 'vitamoo';

type ResolvedRenderer = Awaited<ReturnType<typeof Renderer.create>> | null;
type RendererWithDebug = NonNullable<ResolvedRenderer> & { setDebugSlice(mode: 0 | 1 | 2 | 3): void };
import type { MooShowHooks } from '../hooks/types.js';
import { defaultHooks } from '../hooks/defaults.js';
import { ContentLoader } from './content-loader.js';
import type { ContentIndex, CharacterDef, SceneDef } from './content-loader.js';
import type { Body, Vec3 } from './types.js';
import { SpinController } from '../interaction/spin-controller.js';
import { tickTopPhysics, applyTopTransform, TOP_MAX_TILT } from '../interaction/top-physics.js';
import { SoundEngine } from '../audio/sound-engine.js';

let _stagePickLogCount = 0;
const DEBUG_STAGE_PICK_LOGS = 5;

export interface StageConfig {
    canvas: HTMLCanvasElement;
    hooks?: MooShowHooks;
    assetsBaseUrl?: string;
    /** If set, load this glTF URL as the plumb-bob; all meshes in the file are used. */
    plumbBobUrl?: string;
    /** Scale multiplier for the plumb-bob. Default 1. */
    plumbBobScale?: number;
}

export class MooShowStage {
    readonly canvas: HTMLCanvasElement;
    readonly hooks: MooShowHooks;
    readonly loader: ContentLoader;
    readonly spin: SpinController;
    readonly sound: SoundEngine;

    private _renderer: ResolvedRenderer | Promise<ResolvedRenderer> | null = null;
    private _running = false;
    private _rafId = 0;
    private _animTime = 0;
    private _lastFrameTime = 0;
    private _paused = false;
    private _speedScale = 1.0;
    private _keysHeld = { up: false, down: false, left: false, right: false, leftStart: 0, rightStart: 0 };

    private _bodies: Body[] = [];
    private _selectedActor = -1;
    private _activeScene: string | null = null;
    private _cameraTarget: Vec3 = { x: 0, y: 2.5, z: 0 };
    private _plumbBobUrl: string | undefined;
    private _plumbBobScale: number;
    private _plumbBobThrobStart = 0;
    private _plumbBobSelectionTime = 0;

    constructor(config: StageConfig) {
        this.canvas = config.canvas;
        this.hooks = { ...defaultHooks, ...config.hooks };
        this.loader = new ContentLoader(config.assetsBaseUrl ?? '');
        this.spin = new SpinController();
        this.sound = new SoundEngine();
        this._plumbBobUrl = config.plumbBobUrl;
        this._plumbBobScale = config.plumbBobScale ?? 1;

        this._initRenderer();
        this._bindCanvasEvents();
    }

    private _initRenderer(): void {
        this.canvas.width = this.canvas.clientWidth;
        this.canvas.height = this.canvas.clientHeight;
        const plumbBobUrl = this._plumbBobUrl;
        this._renderer = Renderer.create(this.canvas).catch((e) => {
            console.error('WebGPU init failed:', e);
            return null;
        }).then(async (r) => {
            if (r) {
                this.loader.setTextureFactory(r.getTextureFactory());
                r.setViewport(0, 0, this.canvas.width, this.canvas.height);
                if (plumbBobUrl) {
                    const url = /^https?:\/\//i.test(plumbBobUrl) ? plumbBobUrl : this.loader.baseUrl + plumbBobUrl;
                    try {
                        const meshes = await loadGltfMeshes(url);
                        r.setPlumbBobMeshes(meshes.length > 0 ? meshes : null);
                    } catch (e) {
                        console.warn('Failed to load plumb-bob glTF:', url, e);
                    }
                }
                r.setPlumbBobScale(this._plumbBobScale);
                const ds = new URLSearchParams(window.location.search).get('debugSlice');
                if (ds !== null) {
                    const m = parseInt(ds, 10);
                    if (m >= 0 && m <= 3) {
                        (r as RendererWithDebug).setDebugSlice(m as 0 | 1 | 2 | 3);
                        console.log('[stage] debugSlice from URL', m, '(0=normal 1=UV RG 2=checker 3=red)');
                    }
                }
            }
            return r;
        });
    }

    private async _getRenderer(): Promise<ResolvedRenderer | null> {
        if (this._renderer === null) return null;
        if (this._renderer instanceof Promise) {
            this._renderer = await this._renderer;
            if (this._renderer) {
                this.loader.setTextureFactory(this._renderer.getTextureFactory());
                this._renderer.setViewport(0, 0, this.canvas.width, this.canvas.height);
                const ds = new URLSearchParams(window.location.search).get('debugSlice');
                if (ds !== null) {
                    const m = parseInt(ds, 10);
                    if (m >= 0 && m <= 3) (this._renderer as RendererWithDebug).setDebugSlice(m as 0 | 1 | 2 | 3);
                }
            }
        }
        return this._renderer;
    }

    get contentIndex(): ContentIndex | null { return this.loader.index; }
    get bodies(): Body[] { return this._bodies; }
    get selectedActor(): number { return this._selectedActor; }

    /** Set plumb-bob scale at runtime (default 1). */
    async setPlumbBobScale(scale: number): Promise<void> {
        this._plumbBobScale = scale;
        const r = await this._getRenderer();
        if (r) r.setPlumbBobScale(scale);
    }
    get activeScene(): string | null { return this._activeScene; }
    get paused(): boolean { return this._paused; }
    get running(): boolean { return this._running; }

    get scenes(): SceneDef[] { return this.loader.index?.scenes || []; }
    get characters(): CharacterDef[] { return this.loader.index?.characters || []; }
    get skillNames(): string[] { return Object.keys(this.loader.store.skills); }

    async loadContentIndex(url: string, onProgress?: (msg: string) => void): Promise<ContentIndex> {
        const idx = await this.loader.loadIndex(url);
        await this.loader.loadAllContent(onProgress);
        return idx;
    }

    async setScene(sceneIndex: number): Promise<void> {
        const scenes = this.loader.index?.scenes;
        if (!scenes?.[sceneIndex]) return;

        const newBodies = await this.loader.loadScene(sceneIndex);
        this._bodies = newBodies;
        this._activeScene = scenes[sceneIndex].name;
        this._selectedActor = newBodies.length === 1 ? 0 : -1;

        if (newBodies.length > 0) {
            let cx = 0, cz = 0;
            for (const b of newBodies) { cx += b.x; cz += b.z; }
            cx /= newBodies.length; cz /= newBodies.length;
            this._cameraTarget = { x: cx, y: 2.5, z: cz };
        }

        this.hooks.onSceneChange?.(this._activeScene);
        this.hooks.onSelectionChange?.(this._selectedActor);
        this._renderFrame();
    }

    async setCharacterSolo(charIndex: number): Promise<void> {
        const chars = this.loader.index?.characters;
        if (!chars?.[charIndex]) return;
        this._activeScene = null;
        const body = await this.loader.loadCharacterBody(chars[charIndex]);
        this._bodies = body ? [body] : [];
        this._selectedActor = this._bodies.length === 1 ? 0 : -1;
        if (body) {
            this._computeCameraTarget(body.skeleton);
            this.sound.simlishGreet(0, this._bodies);
        }
        this.hooks.onSceneChange?.(null);
        this.hooks.onSelectionChange?.(this._selectedActor);
        this._renderFrame();
    }

    selectActor(idx: number): void {
        if (idx < -1 || idx >= this._bodies.length) return;
        const prev = this._selectedActor;
        if (prev === idx) {
            this.sound.simlishGreet(idx, this._bodies);
            return;
        }

        const rotYDeg = this.spin.rotY;
        if (prev >= 0 && prev < this._bodies.length) {
            this._bodies[prev].spinOffset += rotYDeg;
        } else if (prev < 0) {
            for (const b of this._bodies) b.spinOffset += rotYDeg;
        }
        if (idx >= 0 && idx < this._bodies.length) {
            this._bodies[idx].spinOffset -= rotYDeg;
        } else if (idx < 0) {
            for (const b of this._bodies) b.spinOffset -= rotYDeg;
        }

        for (let i = 0; i < this._bodies.length; i++) {
            const shouldBeActive = (idx < 0 || i === idx);
            if (!shouldBeActive && this._bodies[i].top.active) {
                this._bodies[i].top.tiltTarget = 0;
            }
        }

        const now = performance.now();
        this._plumbBobThrobStart = now;
        if (idx >= 0) this._plumbBobSelectionTime = now;
        this._selectedActor = idx;
        this.hooks.onSelectionChange?.(idx);
        this.sound.simlishGreet(idx, this._bodies);
    }

    async setAnimation(animName: string, actorIndex?: number): Promise<void> {
        const targets = (actorIndex !== undefined && actorIndex >= 0)
            ? [actorIndex]
            : this._bodies.map((_, i) => i);
        for (const i of targets) {
            const body = this._bodies[i];
            if (!body?.skeleton) continue;
            const practice = await this.loader._loadAnimation(animName, body.skeleton);
            if ((practice as any)?.ready) {
                (practice as any).tick(this._animTime > 0 ? this._animTime : 1);
                updateTransforms(body.skeleton);
            }
            body.practice = practice;
        }
        this._renderFrame();
    }

    async pick(screenX: number, screenY: number): Promise<number> {
        const renderer = await this._getRenderer();
        if (!renderer || this._bodies.length === 0) return -1;
        const rect = this.canvas.getBoundingClientRect();
        const localX = screenX - rect.left;
        const localY = screenY - rect.top;
        const scaleX = this.canvas.width / (rect.width || 1);
        const scaleY = this.canvas.height / (rect.height || 1);
        const bufferX = localX * scaleX;
        const bufferY = localY * scaleY;
        const { type, objectId } = await renderer.readObjectIdAt(bufferX, bufferY);
        if (type === ObjectIdType.CHARACTER || type === ObjectIdType.PLUMB_BOB) return objectId;
        return -1;
    }

    set speedScale(v: number) { this._speedScale = v; }
    get speedScale(): number { return this._speedScale; }

    togglePause(): void {
        this._paused = !this._paused;
        if (!this._paused) this._lastFrameTime = 0;
    }

    start(): void {
        if (this._running) return;
        this._running = true;
        this._lastFrameTime = 0;
        this._rafId = requestAnimationFrame(this._loop);
    }

    stop(): void {
        this._running = false;
        if (this._rafId) cancelAnimationFrame(this._rafId);
        this._rafId = 0;
    }

    render(): void {
        this._renderFrame();
    }

    destroy(): void {
        this.stop();
    }

    private _loop = (timestamp: number): void => {
        if (!this._running) return;
        let needsRender = false;

        if (!this._paused) {
            if (this._lastFrameTime === 0) this._lastFrameTime = timestamp;
            const dt = timestamp - this._lastFrameTime;
            this._lastFrameTime = timestamp;
            this._animTime += dt * this._speedScale;

            for (const body of this._bodies) {
                if ((body.practice as any)?.ready && body.skeleton) {
                    (body.practice as any).tick(this._animTime);
                    updateTransforms(body.skeleton);
                    needsRender = true;
                }
            }
        }

        if (this.spin.tickMomentum()) {
            if (this._bodies.length > 0) {
                if (this._selectedActor >= 0 && this._selectedActor < this._bodies.length) {
                    this._bodies[this._selectedActor].spinOffset += this.spin.rotationVelocity;
                } else {
                    for (const b of this._bodies) b.spinOffset += this.spin.rotationVelocity;
                }
            } else {
                this.spin.rotY += this.spin.rotationVelocity;
                if (this.spin.rotY > 360) this.spin.rotY -= 360;
                if (this.spin.rotY < 0) this.spin.rotY += 360;
            }
            needsRender = true;
        }

        for (const b of this._bodies) {
            if (Math.abs(b.spinVelocity) > 0.001) {
                b.spinOffset += b.spinVelocity;
                b.spinVelocity *= 0.993;
                needsRender = true;
            }
        }

        const rv = this.spin.rotationVelocity;
        const saved = this.spin.rotationVelocity;
        for (let i = 0; i < this._bodies.length; i++) {
            const isSelected = (this._selectedActor < 0 || i === this._selectedActor);
            if (isSelected) {
                tickTopPhysics(this._bodies[i].top, rv);
            } else if (this._bodies[i].top.active) {
                tickTopPhysics(this._bodies[i].top, 0);
            }
        }
        this.spin.rotationVelocity = saved;

        const anyTopActive = this._bodies.some(b => b.top.active);
        if (anyTopActive) needsRender = true;

        if (this._keysHeld.up || this._keysHeld.down) {
            const zoomDelta = this._keysHeld.down ? 1.5 : -1.5;
            this.spin.zoom = Math.max(15, Math.min(400, this.spin.zoom + zoomDelta));
            needsRender = true;
        }
        if (this._keysHeld.left || this._keysHeld.right) {
            const now = performance.now();
            const dir = this._keysHeld.left ? 1 : -1;
            const holdTime = this._keysHeld.left
                ? (now - this._keysHeld.leftStart) / 1000
                : (now - this._keysHeld.rightStart) / 1000;
            const speed = 0.5 + Math.min(holdTime * 5.0, 16.0);
            this.spin.rotationVelocity = dir * speed;
            needsRender = true;
        }

        this.sound.updateSpinSound(this.spin.rotationVelocity, this._bodies, this._selectedActor);

        this.hooks.onAnimationTick?.(this._animTime);
        if (needsRender) this._renderFrame();

        this._rafId = requestAnimationFrame(this._loop);
    };

    private _debugSliceFromUrl(): 0 | 1 | 2 | 3 | null {
        const ds = new URLSearchParams(window.location.search).get('debugSlice');
        if (ds === null) return null;
        const m = parseInt(ds, 10);
        return (m >= 0 && m <= 3) ? (m as 0 | 1 | 2 | 3) : null;
    }

    private async _renderFrame(): Promise<void> {
        const renderer = await this._getRenderer();
        if (!renderer) return;

        const debugSlice = this._debugSliceFromUrl();
        if (debugSlice !== null) {
            (renderer as RendererWithDebug).setDebugSlice(debugSlice);
        }

        const spinSpeed = Math.abs(this.spin.rotationVelocity);
        const anyActive = this._bodies.some(b => b.top.active);
        const useFadeTrail = anyActive && spinSpeed > 1.0 && debugSlice === null;

        if (useFadeTrail) {
            const trailLength = Math.max(0.08, 0.4 - spinSpeed * 0.02);
            renderer.fadeScreen(0.1, 0.1, 0.15, trailLength);
        } else {
            renderer.clear();
        }

        const zoom = this.spin.zoom / 10;
        const rotYRad = this.spin.rotY * Math.PI / 180;
        const rotXRad = this.spin.rotX * Math.PI / 180;
        const cosX = Math.cos(rotXRad);

        const eyeX = Math.sin(rotYRad) * cosX * zoom;
        const eyeY = this._cameraTarget.y + Math.sin(rotXRad) * zoom;
        const eyeZ = Math.cos(rotYRad) * cosX * zoom;

        renderer.setCamera(50, this.canvas.width / this.canvas.height, 0.01, 100,
            eyeX, eyeY, eyeZ,
            this._cameraTarget.x, this._cameraTarget.y, this._cameraTarget.z);

        for (let bi = 0; bi < this._bodies.length; bi++) {
            const body = this._bodies[bi];
            const bTop = body.top;
            const spinDeg = (body.direction || 0) + (body.spinOffset || 0);
            const bodyDir = spinDeg * Math.PI / 180;
            const cosD = Math.cos(bodyDir);
            const sinD = Math.sin(bodyDir);
            let meshIndex = 0;
            for (const { mesh, boneMap, texture } of body.meshes) {
                try {
                    let verts: any[], norms: any[];
                    if (body.skeleton) {
                        const deformed = deformMesh(mesh, body.skeleton, boneMap);
                        verts = deformed.vertices;
                        norms = deformed.normals;
                    } else {
                        verts = mesh.vertices;
                        norms = mesh.normals;
                    }

                    if (bTop.active) {
                        verts = verts.map((v: any) => applyTopTransform(v, bTop, this._cameraTarget.y));
                        norms = norms.map((v: any) => applyTopTransform(v, bTop, this._cameraTarget.y));
                    }

                    if (body.x !== 0 || body.z !== 0 || bodyDir !== 0) {
                        verts = verts.map((v: any) => {
                            if (!v) return v;
                            const rx = v.x * cosD - v.z * sinD;
                            const rz = v.x * sinD + v.z * cosD;
                            return { x: rx + body.x, y: v.y, z: rz + body.z };
                        });
                        if (bodyDir !== 0) {
                            norms = norms.map((v: any) => {
                                if (!v) return v;
                                return { x: v.x * cosD - v.z * sinD, y: v.y, z: v.x * sinD + v.z * cosD };
                            });
                        }
                    }

                    renderer.drawMesh(mesh, verts, norms, texture || null, {
                        type: ObjectIdType.CHARACTER,
                        objectId: bi,
                        subObjectId: meshIndex,
                    });
                } catch { /* skip bad mesh */ }
                meshIndex++;
            }
        }

        if (this._bodies.length > 0) {
            const now = performance.now();
            const plumbRot = now * 0.001 * Math.PI;
            const bob = Math.sin(now * 0.002) * 0.12;
            const RISE_MS = 120;
            const THROB_MS = 220;
            const THROB_AMP = 0.18;
            const riseT = this._plumbBobSelectionTime
                ? Math.min(1, (now - this._plumbBobSelectionTime) / RISE_MS)
                : 1;
            const riseFactor = 1 - (1 - riseT) * (1 - riseT);
            const throbElapsed = now - this._plumbBobThrobStart;
            const throbScale = throbElapsed < THROB_MS
                ? 1 + THROB_AMP * Math.sin((throbElapsed / THROB_MS) * Math.PI)
                : 1;
            const basePlumbSize = 0.18;
            const indicesToDraw = (this._selectedActor >= 0 && this._selectedActor < this._bodies.length)
                ? [this._selectedActor]
                : this._bodies.map((_, i) => i);

            const drawPlumbBob = (bi: number, body: Body) => {
                if (!body.skeleton) return;
                const headBone = body.skeleton.find((b: any) => b.name === 'HEAD');
                if (!headBone) return;
                const bTop = body.top;
                const sd = (body.direction || 0) + (body.spinOffset || 0);
                const dir = sd * Math.PI / 180;
                const cosD = Math.cos(dir), sinD = Math.sin(dir);
                let hx = headBone.worldPosition.x, hy = headBone.worldPosition.y, hz = headBone.worldPosition.z;
                if (bTop.active) {
                    const t = applyTopTransform({ x: hx, y: hy, z: hz }, bTop, this._cameraTarget.y);
                    hx = t.x; hy = t.y; hz = t.z;
                }
                const rx = hx * cosD - hz * sinD;
                const rz = hx * sinD + hz * cosD;
                const isSelected = bi === this._selectedActor;
                const yOffset = (1.5 + bob) * (isSelected ? riseFactor : 1);
                const size = basePlumbSize * (isSelected ? throbScale : 1);
                renderer.drawDiamond(
                    rx + body.x, hy + yOffset, rz + body.z, size, plumbRot, 0.2, 1.0, 0.2, 0.9,
                    { type: ObjectIdType.PLUMB_BOB, objectId: bi },
                );
                this.hooks.onPlumbBobChange?.(bi, true);
            };

            for (const bi of indicesToDraw) {
                drawPlumbBob(bi, this._bodies[bi]);
            }
        }

        renderer.endFrame();
    }

    private _computeCameraTarget(skeleton: any[] | null): void {
        if (!skeleton || skeleton.length === 0) {
            this._cameraTarget = { x: 0, y: 2.5, z: 0 };
            return;
        }
        let minY = Infinity, maxY = -Infinity;
        for (const bone of skeleton) {
            const y = bone.worldPosition.y;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }
        this._cameraTarget = { x: 0, y: (minY + maxY) / 2, z: 0 };
    }

    private _bindCanvasEvents(): void {
        const c = this.canvas;
        c.addEventListener('contextmenu', e => e.preventDefault());
        c.style.cursor = 'grab';

        c.addEventListener('mousedown', async (e: MouseEvent) => {
            this.sound.ensureAudio();
            this.spin.startDrag(e.clientX, e.clientY, e.button, e.shiftKey);
            c.style.cursor = 'grabbing';

            if (e.button === 0 && this._bodies.length > 0) {
                const renderer = await this._getRenderer();
                if (renderer) {
                    const rect = this.canvas.getBoundingClientRect();
                    const localX = e.clientX - rect.left;
                    const localY = e.clientY - rect.top;
                    const scaleX = this.canvas.width / (rect.width || 1);
                    const scaleY = this.canvas.height / (rect.height || 1);
                    const bufferX = localX * scaleX;
                    const bufferY = localY * scaleY;
                    const { type, objectId, subObjectId } = await renderer.readObjectIdAt(bufferX, bufferY);
                    if (_stagePickLogCount < DEBUG_STAGE_PICK_LOGS) {
                        _stagePickLogCount++;
                        console.log('[stage] mousedown pick', {
                            rectW: rect.width, rectH: rect.height,
                            canvasW: this.canvas.width, canvasH: this.canvas.height,
                            localX, localY, scaleX, scaleY, bufferX, bufferY,
                            type, objectId, subObjectId,
                        });
                    }
                    const picked = (type === ObjectIdType.CHARACTER || type === ObjectIdType.PLUMB_BOB) ? objectId : -1;
                    if (picked >= 0) {
                        this.selectActor(picked);
                        this.hooks.onPick?.(picked, e.clientX, e.clientY);
                    } else if (this._bodies.length > 1) {
                        this.selectActor(-1);
                    }
                } else if (this._bodies.length > 1) {
                    this.selectActor(-1);
                }
            }
            e.preventDefault();
        });

        window.addEventListener('mousemove', (e: MouseEvent) => {
            if (!this.spin.isDragging) return;
            const { spinDelta, zoomDelta, tiltDelta, isOrbit } = this.spin.drag(e.clientX, e.clientY);

            if (this._bodies.length > 0 && !isOrbit) {
                if (this._selectedActor >= 0 && this._selectedActor < this._bodies.length) {
                    this._bodies[this._selectedActor].spinOffset += spinDelta;
                } else {
                    for (const b of this._bodies) b.spinOffset += spinDelta;
                }
            } else {
                this.spin.rotY += spinDelta;
                if (this.spin.rotY > 360) this.spin.rotY -= 360;
                if (this.spin.rotY < 0) this.spin.rotY += 360;
            }

            this.spin.zoom = Math.max(15, Math.min(400, this.spin.zoom + zoomDelta));
            this.spin.rotX = Math.max(-89, Math.min(89, this.spin.rotX + tiltDelta));
            this._renderFrame();
        });

        window.addEventListener('mouseup', () => {
            this.spin.endDrag();
            c.style.cursor = 'grab';
        });

        c.addEventListener('wheel', (e: WheelEvent) => {
            e.preventDefault();
            this.spin.applyWheel(e.deltaY, e.deltaMode, e.ctrlKey);
            this._renderFrame();
        }, { passive: false });

        window.addEventListener('resize', () => {
            c.width = c.clientWidth;
            c.height = c.clientHeight;
            if (this._renderer && !(this._renderer instanceof Promise)) {
                this._renderer.setViewport(0, 0, c.width, c.height);
            }
            this._renderFrame();
        });

        c.tabIndex = 0;
        c.addEventListener('mouseenter', () => c.focus());

        const isInputFocused = () => {
            const tag = document.activeElement?.tagName;
            return tag === 'SELECT' || tag === 'INPUT' || tag === 'TEXTAREA';
        };

        window.addEventListener('keydown', (e: KeyboardEvent) => {
            if (isInputFocused()) return;

            if (e.key === ' ') {
                this.sound.ensureAudio();
                if (this._bodies.length > 0) {
                    if (Math.abs(this.spin.rotationVelocity) > 0.01 &&
                        this._selectedActor >= 0 && this._selectedActor < this._bodies.length) {
                        this._bodies[this._selectedActor].spinVelocity = this.spin.rotationVelocity;
                        this.spin.rotationVelocity = 0;
                    }
                    const minIdx = this._bodies.length > 1 ? -1 : 0;
                    const dir = e.shiftKey ? -1 : 1;
                    let idx = this._selectedActor + dir;
                    if (idx >= this._bodies.length) idx = minIdx;
                    if (idx < minIdx) idx = this._bodies.length - 1;
                    this.selectActor(idx);
                }
                e.preventDefault();
            }

            if (e.ctrlKey && ['0', '1', '2', '3'].includes(e.key)) {
                const m = e.key === '0' ? 0 : parseInt(e.key, 10);
                this._getRenderer().then((r) => {
                    if (r) {
                        (r as RendererWithDebug).setDebugSlice(m as 0 | 1 | 2 | 3);
                        console.log('[stage] debugSlice', m, '0=normal 1=UV RG 2=checker 3=red');
                    }
                });
                e.preventDefault();
                return;
            }

            if (e.key === '0' && !e.ctrlKey) {
                this.togglePause();
                this.hooks.onKeyAction?.('togglePause');
                e.preventDefault();
            }

            const speedKeys: Record<string, number> = { '1': 25, '2': 50, '3': 100, '4': 150, '5': 200, '6': 300, '7': 500, '8': 750, '9': 1000 };
            if (speedKeys[e.key] && !e.ctrlKey) {
                this._paused = false;
                this._speedScale = speedKeys[e.key] / 100;
                this._lastFrameTime = 0;
                this.hooks.onKeyAction?.('setSpeed', speedKeys[e.key]);
                e.preventDefault();
            }

            if (e.key === '?' || e.key === 'h') { this.hooks.onKeyAction?.('toggleHelp'); e.preventDefault(); }
            if (e.key === 'Escape') { this.hooks.onKeyAction?.('toggleHelp'); e.preventDefault(); }

            if (e.key === 'n') { this.hooks.onKeyAction?.('stepSceneNext'); e.preventDefault(); }
            if (e.key === 'p') { this.hooks.onKeyAction?.('stepScenePrev'); e.preventDefault(); }
            if (e.key === 'a') { this.hooks.onKeyAction?.('stepActorPrev'); e.preventDefault(); }
            if (e.key === 'd') { this.hooks.onKeyAction?.('stepActorNext'); e.preventDefault(); }
            if (e.key === 'w') { this.hooks.onKeyAction?.('stepCharacterPrev'); e.preventDefault(); }
            if (e.key === 's') { this.hooks.onKeyAction?.('stepCharacterNext'); e.preventDefault(); }
            if (e.key === 'q') { this.hooks.onKeyAction?.('stepAnimationPrev'); e.preventDefault(); }
            if (e.key === 'e') { this.hooks.onKeyAction?.('stepAnimationNext'); e.preventDefault(); }

            if (e.key === 'ArrowUp') { this._keysHeld.up = true; e.preventDefault(); }
            if (e.key === 'ArrowDown') { this._keysHeld.down = true; e.preventDefault(); }
            if (e.key === 'ArrowLeft') { this._keysHeld.left = true; this._keysHeld.leftStart = this._keysHeld.leftStart || performance.now(); e.preventDefault(); }
            if (e.key === 'ArrowRight') { this._keysHeld.right = true; this._keysHeld.rightStart = this._keysHeld.rightStart || performance.now(); e.preventDefault(); }
        });

        window.addEventListener('keyup', (e: KeyboardEvent) => {
            if (e.key === 'ArrowUp') { this._keysHeld.up = false; e.preventDefault(); }
            if (e.key === 'ArrowDown') { this._keysHeld.down = false; e.preventDefault(); }
            if (e.key === 'ArrowLeft') { this._keysHeld.left = false; this._keysHeld.leftStart = 0; e.preventDefault(); }
            if (e.key === 'ArrowRight') { this._keysHeld.right = false; this._keysHeld.rightStart = 0; e.preventDefault(); }
        });
    }
}

export function createMooShowStage(config: StageConfig): MooShowStage {
    return new MooShowStage(config);
}
