import { Vec3, MeshData } from './types.js';
export declare class Renderer {
    private static loggedMeshes;
    private gl;
    private program;
    private aPosition;
    private aNormal;
    private aTexCoord;
    private uProjection;
    private uModelView;
    private uTexture;
    private uHasTexture;
    private uLightDir;
    constructor(canvas: HTMLCanvasElement);
    clear(r?: number, g?: number, b?: number): void;
    setCamera(fov: number, aspect: number, near: number, far: number, eyeX: number, eyeY: number, eyeZ: number, targetX?: number, targetY?: number, targetZ?: number): void;
    setCulling(enable: boolean): void;
    get context(): WebGLRenderingContext;
    drawMesh(mesh: MeshData, vertices: Vec3[], normals: Vec3[], texture?: WebGLTexture | null): void;
    loadTexture(image: HTMLImageElement): WebGLTexture;
    private setBuffer;
    private createProgram;
    private compileShader;
}
