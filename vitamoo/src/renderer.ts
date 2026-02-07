// VitaMoo WebGL renderer — draws deformed meshes with textures.

import { Vec3, Vec2, Face, MeshData, Bone } from './types.js';
import { deformMesh } from './skeleton.js';

const VERTEX_SHADER = `
attribute vec3 aPosition;
attribute vec3 aNormal;
attribute vec2 aTexCoord;
uniform mat4 uProjection;
uniform mat4 uModelView;
varying vec2 vTexCoord;
varying vec3 vNormal;
void main() {
    gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);
    vTexCoord = aTexCoord;
    vNormal = aNormal;
}`;

const FRAGMENT_SHADER = `
precision mediump float;
varying vec2 vTexCoord;
varying vec3 vNormal;
uniform sampler2D uTexture;
uniform bool uHasTexture;
uniform vec3 uLightDir;
void main() {
    float light = max(dot(normalize(vNormal), normalize(uLightDir)), 0.2);
    if (uHasTexture) {
        vec4 texColor = texture2D(uTexture, vTexCoord);
        gl_FragColor = vec4(texColor.rgb * light, texColor.a);
    } else {
        gl_FragColor = vec4(vec3(0.7, 0.7, 0.8) * light, 1.0);
    }
}`;

export class Renderer {
    private gl: WebGLRenderingContext;
    private program: WebGLProgram;
    private aPosition: number;
    private aNormal: number;
    private aTexCoord: number;
    private uProjection: WebGLUniformLocation;
    private uModelView: WebGLUniformLocation;
    private uTexture: WebGLUniformLocation;
    private uHasTexture: WebGLUniformLocation;
    private uLightDir: WebGLUniformLocation;

    constructor(canvas: HTMLCanvasElement) {
        const gl = canvas.getContext('webgl', { alpha: true, antialias: true });
        if (!gl) throw new Error('WebGL not available');
        this.gl = gl;

        gl.enable(gl.DEPTH_TEST);
        gl.enable(gl.CULL_FACE);
        gl.cullFace(gl.BACK);

        this.program = this.createProgram(VERTEX_SHADER, FRAGMENT_SHADER);
        gl.useProgram(this.program);

        this.aPosition = gl.getAttribLocation(this.program, 'aPosition');
        this.aNormal = gl.getAttribLocation(this.program, 'aNormal');
        this.aTexCoord = gl.getAttribLocation(this.program, 'aTexCoord');
        this.uProjection = gl.getUniformLocation(this.program, 'uProjection')!;
        this.uModelView = gl.getUniformLocation(this.program, 'uModelView')!;
        this.uTexture = gl.getUniformLocation(this.program, 'uTexture')!;
        this.uHasTexture = gl.getUniformLocation(this.program, 'uHasTexture')!;
        this.uLightDir = gl.getUniformLocation(this.program, 'uLightDir')!;
    }

    clear(r = 0.1, g = 0.1, b = 0.15): void {
        const gl = this.gl;
        gl.clearColor(r, g, b, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    }

    setCamera(fov: number, aspect: number, near: number, far: number,
              eyeX: number, eyeY: number, eyeZ: number): void {
        const gl = this.gl;
        const proj = perspective(fov, aspect, near, far);
        const view = lookAt(eyeX, eyeY, eyeZ, 0, 0.5, 0, 0, 1, 0);
        gl.uniformMatrix4fv(this.uProjection, false, proj);
        gl.uniformMatrix4fv(this.uModelView, false, view);
        gl.uniform3f(this.uLightDir, 0.5, 1.0, 0.3);
    }

    // Draw a deformed mesh. Call after deformMesh() produces transformed vertices.
    drawMesh(mesh: MeshData, vertices: Vec3[], normals: Vec3[],
             texture: WebGLTexture | null = null): void {
        const gl = this.gl;

        // Build flat arrays for WebGL
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

        // Upload to GPU
        this.setBuffer(this.aPosition, new Float32Array(posData), 3);
        this.setBuffer(this.aNormal, new Float32Array(normData), 3);
        this.setBuffer(this.aTexCoord, new Float32Array(uvData), 2);

        if (texture) {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.uniform1i(this.uTexture, 0);
            gl.uniform1i(this.uHasTexture, 1);
        } else {
            gl.uniform1i(this.uHasTexture, 0);
        }

        const indexBuffer = gl.createBuffer()!;
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indexData), gl.STATIC_DRAW);

        gl.drawElements(gl.TRIANGLES, indexData.length, gl.UNSIGNED_SHORT, 0);
    }

    loadTexture(image: HTMLImageElement): WebGLTexture {
        const gl = this.gl;
        const tex = gl.createTexture()!;
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        return tex;
    }

    private setBuffer(attrib: number, data: Float32Array, size: number): void {
        const gl = this.gl;
        const buf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(attrib);
        gl.vertexAttribPointer(attrib, size, gl.FLOAT, false, 0, 0);
    }

    private createProgram(vsSource: string, fsSource: string): WebGLProgram {
        const gl = this.gl;
        const vs = this.compileShader(gl.VERTEX_SHADER, vsSource);
        const fs = this.compileShader(gl.FRAGMENT_SHADER, fsSource);
        const prog = gl.createProgram()!;
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
            throw new Error('Shader link error: ' + gl.getProgramInfoLog(prog));
        }
        return prog;
    }

    private compileShader(type: number, source: string): WebGLShader {
        const gl = this.gl;
        const shader = gl.createShader(type)!;
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            throw new Error('Shader compile error: ' + gl.getShaderInfoLog(shader));
        }
        return shader;
    }
}

// Simple perspective projection matrix
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

// Simple lookAt view matrix
function lookAt(ex: number, ey: number, ez: number,
                cx: number, cy: number, cz: number,
                ux: number, uy: number, uz: number): Float32Array {
    let fx = cx - ex, fy = cy - ey, fz = cz - ez;
    let fl = Math.sqrt(fx * fx + fy * fy + fz * fz);
    fx /= fl; fy /= fl; fz /= fl;
    let sx = fy * uz - fz * uy, sy = fz * ux - fx * uz, sz = fx * uy - fy * ux;
    let sl = Math.sqrt(sx * sx + sy * sy + sz * sz);
    sx /= sl; sy /= sl; sz /= sl;
    let uux = sy * fz - sz * fy, uuy = sz * fx - sx * fz, uuz = sx * fy - sy * fx;
    return new Float32Array([
        sx, uux, -fx, 0,
        sy, uuy, -fy, 0,
        sz, uuz, -fz, 0,
        -(sx * ex + sy * ey + sz * ez),
        -(uux * ex + uuy * ey + uuz * ez),
        fx * ex + fy * ey + fz * ez, 1,
    ]);
}
