// VitaMoo WebGPU renderer — draws deformed meshes with textures.
/// <reference types="@webgpu/types" />

import { Vec3, MeshData } from './types.js';
import { loadTexture } from './texture.js';
import { createDiamondMesh } from './procedural/diamond.js';
import { transformMesh } from './display-list.js';

export type TextureHandle = import('./texture.js').TextureHandle;

const MESH_VERTEX_WGSL = `
struct Uniforms {
    projection: mat4x4f,
    modelView: mat4x4f,
    lightDir: vec3f,
    alpha: f32,
    fadeColor: vec3f,
    hasTexture: u32,
    ambient: f32,
    diffuseFactor: f32,
    highlight: vec4f,
    idType: u32,
    objectId: u32,
    subObjectId: u32,
    debugMode: u32,
}
@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var tex: texture_2d<f32>;
@group(0) @binding(2) var samp: sampler;

struct VertexInput {
    @location(0) position: vec3f,
    @location(1) normal: vec3f,
    @location(2) texCoord: vec2f,
}
struct VertexOutput {
    @builtin(position) position: vec4f,
    @location(0) texCoord: vec2f,
    @location(1) normal: vec3f,
}
@vertex
fn vertexMain(input: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    out.position = u.projection * u.modelView * vec4f(input.position, 1.0);
    out.texCoord = input.texCoord;
    out.normal = input.normal;
    return out;
}
struct FragmentOutput {
    @location(0) objectId: vec4u,
    @location(1) color: vec4f,
}
@fragment
fn fragmentMain(input: VertexOutput) -> FragmentOutput {
    var result: FragmentOutput;
    result.objectId = vec4u(u.idType, u.objectId, u.subObjectId, 0u);
    if (u.debugMode == 1u) {
        result.color = vec4f(input.texCoord.x, input.texCoord.y, 0.0, 1.0);
        return result;
    }
    if (u.debugMode == 2u) {
        let uv = input.texCoord * 8.0;
        let cx = i32(floor(uv.x));
        let cy = i32(floor(uv.y));
        let c = f32((cx + cy) % 2);
        result.color = vec4f(c, c, c, 1.0);
        return result;
    }
    if (u.debugMode == 3u) {
        result.color = vec4f(1.0, 0.0, 0.0, 1.0);
        return result;
    }
    if (u.fadeColor.r >= 0.0) {
        result.color = vec4f(u.fadeColor, u.alpha);
        return result;
    }
    let n = normalize(input.normal);
    let L = normalize(u.lightDir);
    let diffuse = max(dot(n, L), 0.0);
    let light = u.ambient + u.diffuseFactor * diffuse;
    if (u.hasTexture != 0u) {
        let texColor = textureSample(tex, samp, input.texCoord);
        result.color = vec4f(texColor.rgb * light, texColor.a * u.alpha);
    } else {
        result.color = vec4f(vec3f(0.7, 0.7, 0.8) * light, u.alpha);
    }
    if (u.highlight.a > 0.0) {
        result.color = vec4f(mix(result.color.rgb, u.highlight.rgb, u.highlight.a), result.color.a);
    }
    return result;
}
@fragment
fn fragmentMainColorOnly(input: VertexOutput) -> @location(0) vec4f {
    if (u.debugMode == 1u) {
        return vec4f(input.texCoord.x, input.texCoord.y, 0.0, 1.0);
    }
    if (u.debugMode == 2u) {
        let uv = input.texCoord * 8.0;
        let cx = i32(floor(uv.x));
        let cy = i32(floor(uv.y));
        let c = f32((cx + cy) % 2);
        return vec4f(c, c, c, 1.0);
    }
    if (u.debugMode == 3u) {
        return vec4f(1.0, 0.0, 0.0, 1.0);
    }
    if (u.fadeColor.r >= 0.0) {
        return vec4f(u.fadeColor, u.alpha);
    }
    let n = normalize(input.normal);
    let L = normalize(u.lightDir);
    let diffuse = max(dot(n, L), 0.0);
    let light = u.ambient + u.diffuseFactor * diffuse;
    var out: vec4f;
    if (u.hasTexture != 0u) {
        let texColor = textureSample(tex, samp, input.texCoord);
        out = vec4f(texColor.rgb * light, texColor.a * u.alpha);
    } else {
        out = vec4f(vec3f(0.7, 0.7, 0.8) * light, u.alpha);
    }
    if (u.highlight.a > 0.0) {
        out = vec4f(mix(out.rgb, u.highlight.rgb, u.highlight.a), out.a);
    }
    return out;
}
`;

const QUAD_VERTEX_WGSL = `
struct Uniforms {
    alpha: f32,
    fadeColor: vec3f,
}
@group(0) @binding(0) var<uniform> u: Uniforms;
struct VertexOutput {
    @builtin(position) position: vec4f,
}
@vertex
fn vertexMain(@location(0) position: vec3f) -> VertexOutput {
    var out: VertexOutput;
    out.position = vec4f(position, 1.0);
    return out;
}
@fragment
fn fragmentMain() -> @location(0) vec4f {
    return vec4f(u.fadeColor, u.alpha);
}
`;

const QUAD_DUAL_WGSL = `
struct Uniforms {
    alpha: f32,
    fadeColor: vec3f,
}
@group(0) @binding(0) var<uniform> u: Uniforms;
struct QuadDualOutput {
    @location(0) objectId: vec4u,
    @location(1) color: vec4f,
}
@vertex
fn vertexMain(@location(0) position: vec3f) -> @builtin(position) vec4f {
    return vec4f(position, 1.0);
}
@fragment
fn fragmentMain() -> QuadDualOutput {
    var out: QuadDualOutput;
    out.objectId = vec4u(0u, 0u, 0u, 0u);
    out.color = vec4f(u.fadeColor, u.alpha);
    return out;
}
`;

function perspective(fov: number, aspect: number, near: number, far: number): Float32Array {
    const f = 1.0 / Math.tan(fov * Math.PI / 360);
    const nf = 1 / (near - far);
    return new Float32Array([
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) * nf, -1,
        0, 0, 2 * far * near * nf, 0,
    ]);
}

function lookAt(
    ex: number, ey: number, ez: number,
    cx: number, cy: number, cz: number,
    ux: number, uy: number, uz: number,
): Float32Array {
    let fx = cx - ex, fy = cy - ey, fz = cz - ez;
    let fl = Math.sqrt(fx * fx + fy * fy + fz * fz);
    fx /= fl; fy /= fl; fz /= fl;
    let sx = fy * uz - fz * uy, sy = fz * ux - fx * uz, sz = fx * uy - fy * ux;
    let sl = Math.sqrt(sx * sx + sy * sy + sz * sz);
    sx /= sl; sy /= sl; sz /= sl;
    const uux = sy * fz - sz * fy, uuy = sz * fx - sx * fz, uuz = sx * fy - sy * fx;
    return new Float32Array([
        sx, uux, -fx, 0,
        sy, uuy, -fy, 0,
        sz, uuz, -fz, 0,
        -(sx * ex + sy * ey + sz * ez),
        -(uux * ex + uuy * ey + uuz * ez),
        fx * ex + fy * ey + fz * ez, 1,
    ]);
}

const FADE_SENTINEL = -1;
const UNIFORM_SIZE = 256;
const QUAD_UNIFORM_SIZE = 32;
export const ObjectIdType = {
    NONE: 0,
    CHARACTER: 1,
    OBJECT: 2,
    WALL: 3,
    FLOOR: 4,
    TERRAIN: 5,
    /** Plumb-bob diamond above a character; objectId is the character it refers to. */
    PLUMB_BOB: 6,
} as const;
export type ObjectIdType = (typeof ObjectIdType)[keyof typeof ObjectIdType];

/** Sub-object slot for characters: body, head, hands, accessories (0–255). */
export const SubObjectId = {
    BODY: 0,
    HEAD: 1,
    LEFT_HAND: 2,
    RIGHT_HAND: 3,
    /** Accessory slots 4–255; use 4 + index for each accessory. */
    ACCESSORY_0: 4,
} as const;
export type SubObjectId = (typeof SubObjectId)[keyof typeof SubObjectId];

const DEBUG_PASS_LOGS = 2;
const DEBUG_UNIFORM_LOGS = 8;

export class Renderer {
    private static loggedMeshes = new Set<string>();
    private static diamondMesh: MeshData | null = null;
    private static _passLogCount = 0;
    private static _uniformLogCount = 0;
    private static _loggedDebugSlice = false;

    private static getCachedDiamondMesh(): MeshData {
        if (!Renderer.diamondMesh) Renderer.diamondMesh = createDiamondMesh(1, 6);
        return Renderer.diamondMesh;
    }

    private device!: GPUDevice;
    private queue!: GPUQueue;
    private context!: GPUCanvasContext;
    private format!: GPUTextureFormat;
    private viewport = { x: 0, y: 0, w: 0, h: 0 };
    private depthTexture: GPUTexture | null = null;
    private meshPipeline!: GPURenderPipeline;
    private meshPipelineNoCull!: GPURenderPipeline;
    private meshPipelineSingle!: GPURenderPipeline;
    private meshPipelineNoCullSingle!: GPURenderPipeline;
    private quadPipeline!: GPURenderPipeline;
    private quadPipelineDual!: GPURenderPipeline;
    private meshBindGroupLayout!: GPUBindGroupLayout;
    private quadBindGroupLayout!: GPUBindGroupLayout;
    private uniformBuffer!: GPUBuffer;
    private quadUniformBuffer!: GPUBuffer;
    private defaultSampler!: GPUSampler;
    private dummyTexture!: GPUTexture;
    private proj = new Float32Array(16);
    private modelView = new Float32Array(16);
    private lightDir = new Float32Array([0, 1, 0]);
    private alpha = 1.0;
    private fadeColor = new Float32Array([FADE_SENTINEL, FADE_SENTINEL, FADE_SENTINEL]);
    private ambient = 0.25;
    private diffuseFactor = 0.75;
    private highlight = new Float32Array([0, 0, 0, 0]);
    private cullingEnabled = true;

    private objectIdTexture: GPUTexture | null = null;
    /** 0=normal, 1=UV as RG, 2=UV checker, 3=solid red. Test slices to isolate texture/UV path. */
    private debugSliceMode = 0;
    /** When set, drawDiamond draws these meshes (plug-in plumb-bob); all use the same transform. */
    private plumbBobMeshes: MeshData[] | null = null;
    /** Scale multiplier for plumb-bob (applied to size in drawDiamond). Default 1. */
    private plumbBobScale = 1;

    private currentEncoder: GPUCommandEncoder | null = null;
    private currentPass: GPURenderPassEncoder | null = null;
    private currentTexture: GPUTexture | null = null;
    private buffersToDestroy: GPUBuffer[] = [];

    private constructor(private canvas: HTMLCanvasElement) {}

    static async create(canvas: HTMLCanvasElement): Promise<Renderer> {
        const r = new Renderer(canvas);
        await r._init();
        return r;
    }

    private async _init(): Promise<void> {
        const adapter = await navigator.gpu?.requestAdapter();
        if (!adapter) throw new Error('WebGPU not available');
        this.device = await adapter.requestDevice();
        this.queue = this.device.queue;

        const ctx = this.canvas.getContext('webgpu');
        if (!ctx) throw new Error('WebGPU canvas context not available');
        this.context = ctx;
        this.format = navigator.gpu.getPreferredCanvasFormat?.() ?? 'bgra8unorm';
        this.context.configure({
            device: this.device,
            format: this.format,
            alphaMode: 'opaque',
        });

        this.uniformBuffer = this.device.createBuffer({
            size: UNIFORM_SIZE,
            usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
        });
        this.quadUniformBuffer = this.device.createBuffer({
            size: QUAD_UNIFORM_SIZE,
            usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
        });
        this.defaultSampler = this.device.createSampler({
            minFilter: 'linear',
            magFilter: 'linear',
            addressModeU: 'clamp-to-edge',
            addressModeV: 'clamp-to-edge',
        });
        this.dummyTexture = this.device.createTexture({
            size: [1, 1, 1],
            format: 'rgba8unorm',
            usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST,
        });
        this.queue.writeTexture(
            { texture: this.dummyTexture },
            new Uint8Array([255, 255, 255, 255]),
            { bytesPerRow: 4, rowsPerImage: 1 },
            [1, 1, 1],
        );

        this.meshBindGroupLayout = this.device.createBindGroupLayout({
            entries: [
                { binding: 0, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: 'uniform' } },
                { binding: 1, visibility: GPUShaderStage.FRAGMENT, texture: { sampleType: 'float' } },
                { binding: 2, visibility: GPUShaderStage.FRAGMENT, sampler: { type: 'filtering' } },
            ],
        });
        this.quadBindGroupLayout = this.device.createBindGroupLayout({
            entries: [
                { binding: 0, visibility: GPUShaderStage.FRAGMENT, buffer: { type: 'uniform' } },
            ],
        });

        const meshModule = this.device.createShaderModule({ code: MESH_VERTEX_WGSL });
        const quadModule = this.device.createShaderModule({ code: QUAD_VERTEX_WGSL });

        const meshPipelineLayout = this.device.createPipelineLayout({
            bindGroupLayouts: [this.meshBindGroupLayout],
        });
        const meshVertexState: GPUVertexState = {
            module: meshModule,
            entryPoint: 'vertexMain',
            buffers: [
                {
                    arrayStride: 32,
                    attributes: [
                        { shaderLocation: 0, offset: 0, format: 'float32x3' },
                        { shaderLocation: 1, offset: 12, format: 'float32x3' },
                        { shaderLocation: 2, offset: 24, format: 'float32x2' },
                    ],
                },
            ],
        };
        const meshFragmentState: GPUFragmentState = {
            module: meshModule,
            entryPoint: 'fragmentMain',
            targets: [
                { format: 'rgba32uint' },
                { format: this.format },
            ],
        };
        console.log('[renderer] mesh pipeline targets: [0]=rgba32uint(objectId) [1]=', this.format, '(color)');
        const meshDepthStencil: GPUDepthStencilState = {
            format: 'depth24plus',
            depthWriteEnabled: true,
            depthCompare: 'less-equal',
        };
        this.meshPipeline = this.device.createRenderPipeline({
            layout: meshPipelineLayout,
            vertex: meshVertexState,
            fragment: meshFragmentState,
            primitive: { topology: 'triangle-list', cullMode: 'back', frontFace: 'ccw' },
            depthStencil: meshDepthStencil,
        });
        this.meshPipelineNoCull = this.device.createRenderPipeline({
            layout: meshPipelineLayout,
            vertex: meshVertexState,
            fragment: meshFragmentState,
            primitive: { topology: 'triangle-list', cullMode: 'none', frontFace: 'ccw' },
            depthStencil: meshDepthStencil,
        });

        const meshFragmentStateSingle: GPUFragmentState = {
            module: meshModule,
            entryPoint: 'fragmentMainColorOnly',
            targets: [{ format: this.format }],
        };
        this.meshPipelineSingle = this.device.createRenderPipeline({
            layout: meshPipelineLayout,
            vertex: meshVertexState,
            fragment: meshFragmentStateSingle,
            primitive: { topology: 'triangle-list', cullMode: 'back', frontFace: 'ccw' },
            depthStencil: meshDepthStencil,
        });
        this.meshPipelineNoCullSingle = this.device.createRenderPipeline({
            layout: meshPipelineLayout,
            vertex: meshVertexState,
            fragment: meshFragmentStateSingle,
            primitive: { topology: 'triangle-list', cullMode: 'none', frontFace: 'ccw' },
            depthStencil: meshDepthStencil,
        });

        const quadPipelineLayout = this.device.createPipelineLayout({
            bindGroupLayouts: [this.quadBindGroupLayout],
        });
        this.quadPipeline = this.device.createRenderPipeline({
            layout: quadPipelineLayout,
            vertex: {
                module: quadModule,
                entryPoint: 'vertexMain',
                buffers: [
                    { arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x3' }] },
                ],
            },
            fragment: {
                module: quadModule,
                entryPoint: 'fragmentMain',
                targets: [{ format: this.format }],
            },
            primitive: { topology: 'triangle-list' },
            depthStencil: {
                format: 'depth24plus',
                depthWriteEnabled: false,
                depthCompare: 'always',
            },
        });

        const quadDualModule = this.device.createShaderModule({ code: QUAD_DUAL_WGSL });
        this.quadPipelineDual = this.device.createRenderPipeline({
            layout: quadPipelineLayout,
            vertex: {
                module: quadDualModule,
                entryPoint: 'vertexMain',
                buffers: [
                    { arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x3' }] },
                ],
            },
            fragment: {
                module: quadDualModule,
                entryPoint: 'fragmentMain',
                targets: [
                    { format: 'rgba32uint' },
                    { format: this.format },
                ],
            },
            primitive: { topology: 'triangle-list' },
            depthStencil: {
                format: 'depth24plus',
                depthWriteEnabled: false,
                depthCompare: 'always',
            },
        });
    }

    setViewport(x: number, y: number, w: number, h: number): void {
        this.viewport = { x, y, w, h };
        if (this.depthTexture) this.depthTexture.destroy();
        if (this.objectIdTexture) this.objectIdTexture.destroy();
        if (w > 0 && h > 0) {
            this.depthTexture = this.device.createTexture({
                size: [w, h, 1],
                format: 'depth24plus',
                usage: GPUTextureUsage.RENDER_ATTACHMENT,
            });
            this.objectIdTexture = this.device.createTexture({
                size: [w, h, 1],
                format: 'rgba32uint',
                usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC,
            });
        } else {
            this.depthTexture = null;
            this.objectIdTexture = null;
        }
    }

    getTextureFactory(): { createTextureFromUrl(url: string): Promise<TextureHandle> } {
        return {
            createTextureFromUrl: (url: string) => loadTexture(this.device, this.queue, url),
        };
    }

    /** Test slices: 0=normal, 1=UV as RG, 2=UV checker 8x8, 3=solid red. Use to isolate texture vs UV vs pipeline. */
    setDebugSlice(mode: 0 | 1 | 2 | 3): void {
        this.debugSliceMode = mode;
    }

    private _endFrame(): void {
        if (this.currentPass) {
            this.currentPass.end();
            this.currentPass = null;
        }
        if (this.currentEncoder && this.currentTexture) {
            this.queue.submit([this.currentEncoder.finish()]);
            this.currentEncoder = null;
            this.currentTexture = null;
            for (const b of this.buffersToDestroy) b.destroy();
            this.buffersToDestroy.length = 0;
        }
    }

    private _beginPass(clearColor: GPUColor | null): void {
        this._endFrame();
        const tex = this.context.getCurrentTexture();
        this.currentTexture = tex;
        this.currentEncoder = this.device.createCommandEncoder();
        const view = tex.createView();
        if (!this.depthTexture && tex.width > 0 && tex.height > 0) {
            this.setViewport(0, 0, tex.width, tex.height);
        }
        const clearVal: GPUColor = clearColor ?? { r: 0.1, g: 0.1, b: 0.15, a: 1 };
        const colorAttachments: GPURenderPassColorAttachment[] = [];
        if (this.objectIdTexture) {
            colorAttachments.push({
                view: this.objectIdTexture.createView(),
                clearValue: { r: 0, g: 0, b: 0, a: 0 },
                loadOp: 'clear',
                storeOp: 'store',
            });
            colorAttachments.push({
                view,
                clearValue: clearVal,
                loadOp: clearColor ? 'clear' : 'load',
                storeOp: 'store',
            });
        } else {
            colorAttachments.push({
                view,
                clearValue: clearVal,
                loadOp: clearColor ? 'clear' : 'load',
                storeOp: 'store',
            });
        }
        const passDesc: GPURenderPassDescriptor = {
            colorAttachments,
            depthStencilAttachment: this.depthTexture ? {
                view: this.depthTexture.createView(),
                depthClearValue: 1,
                depthLoadOp: 'clear',
                depthStoreOp: 'store',
            } : undefined,
        };
        if (Renderer._passLogCount < DEBUG_PASS_LOGS) {
            Renderer._passLogCount++;
            const n = colorAttachments.length;
            const objSize = this.objectIdTexture
                ? `${this.objectIdTexture.width}x${this.objectIdTexture.height}`
                : 'none';
            console.log('[renderer] _beginPass', {
                passLog: Renderer._passLogCount,
                numAttachments: n,
                attachmentOrder: n === 2 ? 'att0=objectId(rgba32uint) att1=swapChain(color)' : 'att0=swapChain',
                viewport: { ...this.viewport },
                swapChainSize: tex.width + 'x' + tex.height,
                objectIdTextureSize: objSize,
            });
        }
        this.currentPass = this.currentEncoder.beginRenderPass(passDesc);
        this.currentPass.setViewport(
            this.viewport.x, this.viewport.y, this.viewport.w, this.viewport.h,
            0, 1,
        );
    }

    clear(r = 0.1, g = 0.1, b = 0.15): void {
        this._beginPass({ r, g, b, a: 1 });
    }

    fadeScreen(r = 0.1, g = 0.1, b = 0.15, alpha = 0.3): void {
        this._beginPass(null);
        const useDual = this.objectIdTexture != null;
        this.currentPass!.setPipeline(useDual ? this.quadPipelineDual : this.quadPipeline);
        const quadVerts = new Float32Array([
            -1, -1, 0, 1, -1, 0, 1, 1, 0, -1, -1, 0, 1, 1, 0, -1, 1, 0,
        ]);
        const quadBuffer = this.device.createBuffer({
            size: quadVerts.byteLength,
            usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
        });
        this.queue.writeBuffer(quadBuffer, 0, quadVerts);
        const quadUniformData = new ArrayBuffer(QUAD_UNIFORM_SIZE);
        const quadView = new DataView(quadUniformData);
        quadView.setFloat32(0, alpha, true);
        quadView.setFloat32(4, r, true);
        quadView.setFloat32(8, g, true);
        quadView.setFloat32(12, b, true);
        this.queue.writeBuffer(this.quadUniformBuffer, 0, quadUniformData);
        const quadBindGroup = this.device.createBindGroup({
            layout: this.quadBindGroupLayout,
            entries: [{ binding: 0, resource: { buffer: this.quadUniformBuffer } }],
        });
        this.currentPass!.setBindGroup(0, quadBindGroup);
        this.currentPass!.setVertexBuffer(0, quadBuffer);
        this.currentPass!.draw(6);
        this.buffersToDestroy.push(quadBuffer);
    }

    setCamera(
        fov: number, aspect: number, near: number, far: number,
        eyeX: number, eyeY: number, eyeZ: number,
        targetX = 0, targetY = 0.5, targetZ = 0,
    ): void {
        const proj = perspective(fov, aspect, near, far);
        const view = lookAt(eyeX, eyeY, eyeZ, targetX, targetY, targetZ, 0, 1, 0);
        this.proj.set(proj);
        this.modelView.set(view);
        const lx = eyeX - targetX, ly = eyeY - targetY + 0.5, lz = eyeZ - targetZ;
        const ll = Math.sqrt(lx * lx + ly * ly + lz * lz) || 1;
        this.lightDir[0] = lx / ll;
        this.lightDir[1] = ly / ll;
        this.lightDir[2] = lz / ll;
    }

    setCulling(enable: boolean): void {
        this.cullingEnabled = enable;
    }

    /**
     * Use custom meshes as the plumb-bob (e.g. all meshes from loadGltfMeshes). Pass null or [] to use the default procedural diamond.
     */
    setPlumbBobMeshes(meshes: MeshData[] | null): void {
        this.plumbBobMeshes = meshes?.length ? meshes : null;
    }

    /** Scale multiplier for the plumb-bob (runtime parameter). Default 1. */
    setPlumbBobScale(scale: number): void {
        this.plumbBobScale = scale;
    }

    endFrame(): void {
        this._endFrame();
    }

    drawMesh(
        mesh: MeshData,
        vertices: Vec3[],
        normals: Vec3[],
        texture: TextureHandle | null = null,
        objectId?: { type: ObjectIdType; objectId: number; subObjectId?: number },
    ): void {
        if (!this.currentPass) this._beginPass(null);

        const posData: number[] = [];
        const normData: number[] = [];
        const uvData: number[] = [];
        const indexData: number[] = [];

        for (let i = 0; i < vertices.length; i++) {
            const v = vertices[i];
            const n = normals[i];
            const uv = mesh.uvs[i] || { x: 0, y: 0 };
            if (v && n) {
                posData.push(v.x, v.y, v.z);
                normData.push(n.x, n.y, n.z);
                uvData.push(uv.x, uv.y);
            } else {
                posData.push(0, 0, 0);
                normData.push(0, 1, 0);
                uvData.push(0, 0);
            }
        }
        for (const face of mesh.faces) {
            indexData.push(face.a, face.b, face.c);
        }

        const textureValid = texture != null && typeof (texture as GPUTexture).createView === 'function';
        if (!textureValid && texture != null) {
            console.warn('[drawMesh] invalid texture handle (missing createView), using dummy', { mesh: mesh.name });
        }
        const texToBind = textureValid ? texture! : null;

        if (!Renderer.loggedMeshes.has(mesh.name)) {
            Renderer.loggedMeshes.add(mesh.name);
            const maxIdx = vertices.length - 1;
            const badIndices = indexData.filter((i) => i < 0 || i > maxIdx);
            const uvCount = mesh.uvs?.length ?? 0;
            const allZeroUv = uvCount > 0 && uvData.every((v, i) => v === 0);
            const uvHint = uvCount === 0 ? 'no uvs' : allZeroUv ? 'uvs all zero' : 'uvs ok';
            console.log(
                `[drawMesh] "${mesh.name}" verts=${vertices.length} tris=${mesh.faces.length} hasTex=${!!texToBind} ${uvHint} badIndices=${badIndices.length}`,
            );
        }

        const vertexCount = posData.length / 3;
        const interleaved = new Float32Array(vertexCount * 8);
        for (let i = 0; i < vertexCount; i++) {
            interleaved[i * 8 + 0] = posData[i * 3];
            interleaved[i * 8 + 1] = posData[i * 3 + 1];
            interleaved[i * 8 + 2] = posData[i * 3 + 2];
            interleaved[i * 8 + 3] = normData[i * 3];
            interleaved[i * 8 + 4] = normData[i * 3 + 1];
            interleaved[i * 8 + 5] = normData[i * 3 + 2];
            interleaved[i * 8 + 6] = uvData[i * 2];
            interleaved[i * 8 + 7] = uvData[i * 2 + 1];
        }
        const uniformData = new ArrayBuffer(UNIFORM_SIZE);
        const view = new DataView(uniformData);
        for (let i = 0; i < 16; i++) view.setFloat32(i * 4, this.proj[i], true);
        for (let i = 0; i < 16; i++) view.setFloat32(64 + i * 4, this.modelView[i], true);
        view.setFloat32(128, this.lightDir[0], true);
        view.setFloat32(132, this.lightDir[1], true);
        view.setFloat32(136, this.lightDir[2], true);
        view.setFloat32(140, this.alpha, true);
        const useFade = texToBind == null && this.fadeColor[0] >= 0;
        const fadeR = useFade ? this.fadeColor[0] : FADE_SENTINEL;
        const fadeG = useFade ? this.fadeColor[1] : FADE_SENTINEL;
        const fadeB = useFade ? this.fadeColor[2] : FADE_SENTINEL;
        const hasTexU32 = texToBind ? 1 : 0;
        if (Renderer._uniformLogCount < DEBUG_UNIFORM_LOGS && texToBind != null) {
            Renderer._uniformLogCount++;
            const useDualForLog = this.objectIdTexture != null;
            console.log('[renderer] drawMesh uniform (textured)', {
                mesh: mesh.name,
                uniformLog: Renderer._uniformLogCount,
                fadeR, fadeG, fadeB,
                expectFadeSentinel: fadeR === FADE_SENTINEL && fadeG === FADE_SENTINEL && fadeB === FADE_SENTINEL,
                hasTexture: hasTexU32,
                useFade,
                useDualPipeline: useDualForLog,
            });
        }
        view.setFloat32(144, fadeR, true);
        view.setFloat32(148, fadeG, true);
        view.setFloat32(152, fadeB, true);
        view.setUint32(156, hasTexU32, true);
        view.setFloat32(160, this.ambient, true);
        view.setFloat32(164, this.diffuseFactor, true);
        // WGSL: vec4f highlight aligns to 16; diffuseFactor ends at 168 → pad 168–175, highlight @176.
        view.setFloat32(176, this.highlight[0], true);
        view.setFloat32(180, this.highlight[1], true);
        view.setFloat32(184, this.highlight[2], true);
        view.setFloat32(188, this.highlight[3], true);
        view.setUint32(192, (objectId?.type ?? 0) & 0xff, true);
        view.setUint32(196, (objectId?.objectId ?? 0) >>> 0, true);
        view.setUint32(200, ((objectId?.subObjectId ?? 0) & 0xff) >>> 0, true);
        const debugModeU32 = (this.debugSliceMode ?? 0) >>> 0;
        view.setUint32(204, debugModeU32, true);
        if (debugModeU32 !== 0 && !Renderer._loggedDebugSlice) {
            Renderer._loggedDebugSlice = true;
            console.log('[renderer] debugSlice active', { mode: debugModeU32, '0=normal 1=UV 2=checker 3=red': true });
        }
        if (Renderer._uniformLogCount <= 1 && texToBind != null) {
            const u8 = new Uint8Array(uniformData);
            const fadeHex = Array.from(u8.slice(144, 160)).map(b => b.toString(16).padStart(2, '0')).join(' ');
            console.log('[renderer] uniform bytes fadeColor+hasTexture @144', { mesh: mesh.name, fadeHex, reRead: [view.getFloat32(144, true), view.getFloat32(148, true), view.getFloat32(152, true)], hasTex: view.getUint32(156, true) });
        }
        this.queue.writeBuffer(this.uniformBuffer, 0, uniformData);

        const texToUse = texToBind ?? this.dummyTexture;
        if (texToBind != null && Renderer._uniformLogCount <= DEBUG_UNIFORM_LOGS) {
            const label = (texToUse as GPUTexture).label ?? 'unknown';
            console.log('[renderer] drawMesh bindGroup', { mesh: mesh.name, textureLabel: label });
        }
        const meshBindGroup = this.device.createBindGroup({
            layout: this.meshBindGroupLayout,
            entries: [
                { binding: 0, resource: { buffer: this.uniformBuffer } },
                { binding: 1, resource: texToUse.createView() },
                { binding: 2, resource: this.defaultSampler },
            ],
        });

        const useDual = this.objectIdTexture != null;
        const meshPipe = useDual
            ? (this.cullingEnabled ? this.meshPipeline : this.meshPipelineNoCull)
            : (this.cullingEnabled ? this.meshPipelineSingle : this.meshPipelineNoCullSingle);

        const vb = this.device.createBuffer({
            size: interleaved.byteLength,
            usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
        });
        this.queue.writeBuffer(vb, 0, interleaved);
        const ib = this.device.createBuffer({
            size: indexData.length * 2,
            usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST,
        });
        this.queue.writeBuffer(ib, 0, new Uint16Array(indexData));

        this.currentPass!.setPipeline(meshPipe);
        this.currentPass!.setBindGroup(0, meshBindGroup);
        this.currentPass!.setVertexBuffer(0, vb);
        this.currentPass!.setIndexBuffer(ib, 'uint16');
        this.currentPass!.drawIndexed(indexData.length);
        this.buffersToDestroy.push(vb, ib);
    }

    drawDiamond(
        x: number, y: number, z: number,
        size: number, rotY: number,
        r: number, g: number, b: number, alpha = 1.0,
        objectId?: { type: ObjectIdType; objectId: number; subObjectId?: number },
    ): void {
        const effectiveSize = size * this.plumbBobScale;
        const meshes = this.plumbBobMeshes?.length
            ? this.plumbBobMeshes
            : [Renderer.getCachedDiamondMesh()];
        const savedAlpha = this.alpha;
        const savedFade = new Float32Array(this.fadeColor);
        this.alpha = alpha;
        this.fadeColor[0] = r;
        this.fadeColor[1] = g;
        this.fadeColor[2] = b;
        for (const mesh of meshes) {
            const { vertices, normals } = transformMesh(mesh, x, y, z, rotY, effectiveSize);
            this.drawMesh(mesh, vertices, normals, null, objectId);
        }
        this.alpha = savedAlpha;
        this.fadeColor.set(savedFade);
    }

    private static _readObjectIdLogCount = 0;
    private static readonly DEBUG_READ_OBJECT_ID_LOGS = 5;

    async readObjectIdAt(screenX: number, screenY: number): Promise<{ type: number; objectId: number; subObjectId: number }> {
        if (!this.objectIdTexture) return { type: ObjectIdType.NONE, objectId: 0, subObjectId: 0 };
        const w = this.viewport.w;
        const h = this.viewport.h;
        const x = Math.max(0, Math.min(w - 1, Math.floor(screenX) - this.viewport.x));
        const y = Math.max(0, Math.min(h - 1, Math.floor(screenY) - this.viewport.y));

        const bytesPerRow = 256;
        const buffer = this.device.createBuffer({
            size: bytesPerRow,
            usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
        });
        const encoder = this.device.createCommandEncoder();
        encoder.copyTextureToBuffer(
            { texture: this.objectIdTexture, origin: [x, y, 0] },
            { buffer, bytesPerRow, rowsPerImage: 1 },
            [1, 1, 1],
        );
        this.queue.submit([encoder.finish()]);
        await buffer.mapAsync(GPUMapMode.READ);
        const mapped = buffer.getMappedRange();
        const dv = new DataView(mapped);
        const type = dv.getUint32(0, true) & 0xff;
        const objectId = dv.getUint32(4, true);
        const subObjectId = dv.getUint32(8, true) & 0xff;
        if (Renderer._readObjectIdLogCount < Renderer.DEBUG_READ_OBJECT_ID_LOGS) {
            Renderer._readObjectIdLogCount++;
            const raw = new Uint8Array(mapped);
            const hex = Array.from(raw.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' ');
            console.log('[renderer] readObjectIdAt', {
                readLog: Renderer._readObjectIdLogCount,
                screenX, screenY,
                viewport: { ...this.viewport },
                samplePixel: { x, y },
                rawFirst16Hex: hex,
                result: { type, objectId, subObjectId },
            });
        }
        buffer.unmap();
        buffer.destroy();
        return { type, objectId, subObjectId };
    }
}
