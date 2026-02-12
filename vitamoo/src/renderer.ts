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
uniform float uAlpha;
uniform vec3 uFadeColor;
void main() {
    if (uFadeColor.r >= 0.0) {
        gl_FragColor = vec4(uFadeColor, uAlpha);
        return;
    }
    vec3 n = normalize(vNormal);
    vec3 L = normalize(uLightDir);
    float diffuse = max(dot(n, L), 0.0);
    float light = 0.25 + 0.75 * diffuse;
    if (uHasTexture) {
        vec4 texColor = texture2D(uTexture, vTexCoord);
        gl_FragColor = vec4(texColor.rgb * light, texColor.a * uAlpha);
    } else {
        gl_FragColor = vec4(vec3(0.7, 0.7, 0.8) * light, uAlpha);
    }
}`;

export class Renderer {
    private static loggedMeshes = new Set<string>();
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
    private uAlpha: WebGLUniformLocation;
    private uFadeColor: WebGLUniformLocation;

    constructor(canvas: HTMLCanvasElement) {
        const gl = canvas.getContext('webgl', { alpha: false, antialias: true, preserveDrawingBuffer: true });
        if (!gl) throw new Error('WebGL not available');
        this.gl = gl;

        gl.enable(gl.DEPTH_TEST);
        // The Sims SKN text format stores CCW winding (matching OpenGL/WebGL).
        gl.frontFace(gl.CCW);
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
        this.uAlpha = gl.getUniformLocation(this.program, 'uAlpha')!;
        this.uFadeColor = gl.getUniformLocation(this.program, 'uFadeColor')!;
        gl.uniform1f(this.uAlpha, 1.0);
        gl.uniform3f(this.uFadeColor, -1, -1, -1); // sentinel: use normal lighting
    }

    clear(r = 0.1, g = 0.1, b = 0.15): void {
        const gl = this.gl;
        gl.clearColor(r, g, b, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    }

    // Motion blur: overlay a semi-transparent background-colored quad over the
    // previous frame. Alpha controls trail length (lower = longer ghostly trails).
    // Clears only the depth buffer so new geometry draws on top of the faded trails.
    fadeScreen(r = 0.1, g = 0.1, b = 0.15, alpha = 0.3): void {
        const gl = this.gl;

        const prevDepthTest = gl.isEnabled(gl.DEPTH_TEST);
        const prevCullFace = gl.isEnabled(gl.CULL_FACE);
        gl.disable(gl.DEPTH_TEST);
        gl.disable(gl.CULL_FACE);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        // Identity matrices so clip coords = NDC
        const identity = new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
        gl.uniformMatrix4fv(this.uProjection, false, identity);
        gl.uniformMatrix4fv(this.uModelView, false, identity);
        gl.uniform1f(this.uAlpha, alpha);
        gl.uniform3f(this.uFadeColor, r, g, b); // exact background color

        // Fullscreen quad in NDC
        const quadVerts = new Float32Array([
            -1,-1,0, 1,-1,0, 1,1,0, -1,-1,0, 1,1,0, -1,1,0
        ]);
        const quadNorms = new Float32Array([
            0,0,1, 0,0,1, 0,0,1, 0,0,1, 0,0,1, 0,0,1
        ]);
        const quadUVs = new Float32Array([
            0,0, 1,0, 1,1, 0,0, 1,1, 0,1
        ]);

        const pb = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, pb);
        gl.bufferData(gl.ARRAY_BUFFER, quadVerts, gl.STREAM_DRAW);
        gl.enableVertexAttribArray(this.aPosition);
        gl.vertexAttribPointer(this.aPosition, 3, gl.FLOAT, false, 0, 0);

        const nb = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, nb);
        gl.bufferData(gl.ARRAY_BUFFER, quadNorms, gl.STREAM_DRAW);
        gl.enableVertexAttribArray(this.aNormal);
        gl.vertexAttribPointer(this.aNormal, 3, gl.FLOAT, false, 0, 0);

        const ub = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, ub);
        gl.bufferData(gl.ARRAY_BUFFER, quadUVs, gl.STREAM_DRAW);
        gl.enableVertexAttribArray(this.aTexCoord);
        gl.vertexAttribPointer(this.aTexCoord, 2, gl.FLOAT, false, 0, 0);

        gl.drawArrays(gl.TRIANGLES, 0, 6);

        gl.deleteBuffer(pb);
        gl.deleteBuffer(nb);
        gl.deleteBuffer(ub);

        // Restore
        gl.uniform1f(this.uAlpha, 1.0);
        gl.uniform3f(this.uFadeColor, -1, -1, -1); // back to normal lighting
        gl.disable(gl.BLEND);
        if (prevDepthTest) gl.enable(gl.DEPTH_TEST);
        if (prevCullFace) gl.enable(gl.CULL_FACE);
        gl.clear(gl.DEPTH_BUFFER_BIT);
    }

    setCamera(fov: number, aspect: number, near: number, far: number,
              eyeX: number, eyeY: number, eyeZ: number,
              targetX = 0, targetY = 0.5, targetZ = 0): void {
        const gl = this.gl;
        const proj = perspective(fov, aspect, near, far);
        const view = lookAt(eyeX, eyeY, eyeZ, targetX, targetY, targetZ, 0, 1, 0);
        gl.uniformMatrix4fv(this.uProjection, false, proj);
        gl.uniformMatrix4fv(this.uModelView, false, view);
        // Light follows the camera: main light from eye direction + slight upward bias
        const lx = eyeX - targetX, ly = eyeY - targetY + 0.5, lz = eyeZ - targetZ;
        const ll = Math.sqrt(lx * lx + ly * ly + lz * lz) || 1;
        gl.uniform3f(this.uLightDir, lx / ll, ly / ll, lz / ll);
    }

    // Toggle backface culling. Enable once face winding is confirmed correct.
    setCulling(enable: boolean): void {
        if (enable) {
            this.gl.enable(this.gl.CULL_FACE);
            this.gl.cullFace(this.gl.BACK);
        } else {
            this.gl.disable(this.gl.CULL_FACE);
        }
    }

    // Expose GL context for external texture operations
    get context(): WebGLRenderingContext { return this.gl; }

    // Draw a deformed mesh. Call after deformMesh() produces transformed vertices.
    drawMesh(mesh: MeshData, vertices: Vec3[], normals: Vec3[],
             texture: WebGLTexture | null = null): void {
        const gl = this.gl;

        // Build flat arrays for WebGL
        const posData: number[] = [];
        const normData: number[] = [];
        const uvData: number[] = [];
        const indexData: number[] = [];

        let nullVerts = 0;
        for (let i = 0; i < vertices.length; i++) {
            const v = vertices[i];
            const n = normals[i];
            const uv = mesh.uvs[i] || { x: 0, y: 0 };
            if (v && n) {
                posData.push(v.x, v.y, v.z);
                normData.push(n.x, n.y, n.z);
                uvData.push(uv.x, uv.y);
            } else {
                nullVerts++;
                posData.push(0, 0, 0);
                normData.push(0, 1, 0);
                uvData.push(0, 0);
            }
        }

        for (const face of mesh.faces) {
            indexData.push(face.a, face.b, face.c);
        }

        // Check for out-of-range indices (only on first draw per mesh)
        if (!Renderer.loggedMeshes.has(mesh.name)) {
            Renderer.loggedMeshes.add(mesh.name);
            const maxIdx = vertices.length - 1;
            const badIndices = indexData.filter(i => i < 0 || i > maxIdx);
            console.log(`[drawMesh] "${mesh.name}" verts=${vertices.length} nullVerts=${nullVerts} tris=${mesh.faces.length} indices=${indexData.length} uvs=${mesh.uvs.length} badIndices=${badIndices.length} hasTex=${!!texture}`,
                { posRange: posData.length > 0 ? { min: Math.min(...posData), max: Math.max(...posData) } : 'empty',
                  samplePos: posData.slice(0, 9),
                  sampleIdx: indexData.slice(0, 9) });
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

    // Draw a procedural diamond (octahedron) at a world position.
    // The classic Sims plumb bob: two pyramids stacked point-to-point.
    // Sharp edges: no vertex sharing — each face has its own 3 vertices and face normal (own smoothing group).
    drawDiamond(x: number, y: number, z: number,
                size: number, rotY: number,
                r: number, g: number, b: number, alpha = 1.0): void {
        const gl = this.gl;

        // N equatorial points + top + bottom, rotated by rotY
        const N = 6; // facet count
        const s = size;
        const h = size * 2.2; // tall diamond shape

        const eq: { x: number; y: number; z: number }[] = [];
        for (let i = 0; i < N; i++) {
            const a = rotY + (i / N) * Math.PI * 2;
            eq.push({ x: s * Math.cos(a), y: 0, z: s * Math.sin(a) });
        }
        const top = { x: 0, y: h, z: 0 };
        const bot = { x: 0, y: -h, z: 0 };

        // 2*N triangles: N top + N bottom. Each tri has its own 3 verts (no sharing) = sharp edges.
        const tris: { x: number; y: number; z: number }[] = [];
        for (let i = 0; i < N; i++) {
            const next = (i + 1) % N;
            // Top pyramid: CCW from outside so normal points up/out
            tris.push(eq[i], eq[next], top);
            // Bottom pyramid: CCW from below (eq[i], eq[next], bot) so normal points down/out
            tris.push(eq[i], eq[next], bot);
        }

        const posData = new Float32Array(tris.length * 3);
        const normData = new Float32Array(tris.length * 3);
        const uvData = new Float32Array(tris.length * 2);

        for (let i = 0; i < tris.length; i += 3) {
            const a = tris[i], b2 = tris[i + 1], c = tris[i + 2];
            // Face normal
            const ux = b2.x - a.x, uy = b2.y - a.y, uz = b2.z - a.z;
            const vx = c.x - a.x, vy = c.y - a.y, vz = c.z - a.z;
            let nx = uy * vz - uz * vy;
            let ny = uz * vx - ux * vz;
            let nz = ux * vy - uy * vx;
            const nl = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
            nx /= nl; ny /= nl; nz /= nl;

            for (let j = 0; j < 3; j++) {
                const v = tris[i + j];
                const vi = (i + j) * 3;
                posData[vi] = v.x + x;
                posData[vi + 1] = v.y + y;
                posData[vi + 2] = v.z + z;
                normData[vi] = nx;
                normData[vi + 1] = ny;
                normData[vi + 2] = nz;
                uvData[(i + j) * 2] = 0;
                uvData[(i + j) * 2 + 1] = 0;
            }
        }

        // Draw with custom color via uFadeColor, no culling (both sides visible)
        const wasCulling = gl.isEnabled(gl.CULL_FACE);
        gl.disable(gl.CULL_FACE);
        gl.uniform3f(this.uFadeColor, r, g, b);
        gl.uniform1f(this.uAlpha, alpha);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        this.setBuffer(this.aPosition, posData, 3);
        this.setBuffer(this.aNormal, normData, 3);
        this.setBuffer(this.aTexCoord, uvData, 2);
        gl.uniform1i(this.uHasTexture, 0);

        gl.drawArrays(gl.TRIANGLES, 0, tris.length);

        // Restore
        gl.uniform3f(this.uFadeColor, -1, -1, -1);
        gl.uniform1f(this.uAlpha, 1.0);
        gl.disable(gl.BLEND);
        if (wasCulling) gl.enable(gl.CULL_FACE);
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
