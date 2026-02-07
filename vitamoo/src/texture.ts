// VitaMoo texture loader — reads BMP files (Sims native format),
// plus PNG and JPG when the file extension says so.
//
// BMP is the canonical format for Sims 1 skin textures. They're 8-bit
// indexed color with a 256-entry palette. We read them directly because
// that's what the game content uses and we don't want to require a
// conversion step for legacy content.
//
// If the filename (lowercased) ends with .png or .jpg, we use the
// browser's native image decoder instead. This supports modern content
// created with the Simopolis tools or AI image generation.

// Parse a BMP file from an ArrayBuffer. Returns an ImageData-compatible
// object with RGBA pixels ready for WebGL texturing.
export function parseBMP(buffer: ArrayBuffer): {
    width: number; height: number; data: Uint8ClampedArray
} {
    const view = new DataView(buffer);

    // BMP header
    const magic = String.fromCharCode(view.getUint8(0), view.getUint8(1));
    if (magic !== 'BM') throw new Error('Not a BMP file');

    const dataOffset = view.getUint32(10, true);
    const headerSize = view.getUint32(14, true);
    const width = view.getInt32(18, true);
    const rawHeight = view.getInt32(22, true);
    const height = Math.abs(rawHeight);
    const topDown = rawHeight < 0;
    const bitsPerPixel = view.getUint16(28, true);
    const compression = view.getUint32(30, true);

    // We handle 8-bit indexed (most Sims textures) and 24-bit RGB
    if (bitsPerPixel !== 8 && bitsPerPixel !== 24 && bitsPerPixel !== 32) {
        throw new Error(`Unsupported BMP bit depth: ${bitsPerPixel}`);
    }

    const rgba = new Uint8ClampedArray(width * height * 4);

    if (bitsPerPixel === 8) {
        // 8-bit indexed color — read the palette first
        const paletteOffset = 14 + headerSize;
        const numColors = view.getUint32(46, true) || 256;
        const palette = new Uint8Array(numColors * 4); // BGRA per entry
        for (let i = 0; i < numColors; i++) {
            const off = paletteOffset + i * 4;
            palette[i * 4 + 0] = view.getUint8(off + 2); // R (BMP stores BGR)
            palette[i * 4 + 1] = view.getUint8(off + 1); // G
            palette[i * 4 + 2] = view.getUint8(off + 0); // B
            palette[i * 4 + 3] = 255;                     // A
        }

        // Row stride is padded to 4-byte boundary
        const rowStride = Math.ceil(width / 4) * 4;

        if (compression === 0) {
            // BI_RGB: uncompressed indexed
            for (let y = 0; y < height; y++) {
                const srcRow = topDown ? y : (height - 1 - y);
                const srcOffset = dataOffset + srcRow * rowStride;
                for (let x = 0; x < width; x++) {
                    const idx = view.getUint8(srcOffset + x);
                    const dstOffset = (y * width + x) * 4;
                    rgba[dstOffset + 0] = palette[idx * 4 + 0];
                    rgba[dstOffset + 1] = palette[idx * 4 + 1];
                    rgba[dstOffset + 2] = palette[idx * 4 + 2];
                    rgba[dstOffset + 3] = palette[idx * 4 + 3];
                }
            }
        } else if (compression === 1) {
            // BI_RLE8: run-length encoded 8-bit
            decodeRLE8(view, dataOffset, width, height, topDown, palette, rgba);
        } else {
            throw new Error(`Unsupported BMP compression: ${compression}`);
        }
    } else if (bitsPerPixel === 24) {
        // 24-bit RGB
        const rowStride = Math.ceil(width * 3 / 4) * 4;
        for (let y = 0; y < height; y++) {
            const srcRow = topDown ? y : (height - 1 - y);
            const srcOffset = dataOffset + srcRow * rowStride;
            for (let x = 0; x < width; x++) {
                const sOff = srcOffset + x * 3;
                const dOff = (y * width + x) * 4;
                rgba[dOff + 0] = view.getUint8(sOff + 2); // R (BGR order)
                rgba[dOff + 1] = view.getUint8(sOff + 1); // G
                rgba[dOff + 2] = view.getUint8(sOff + 0); // B
                rgba[dOff + 3] = 255;
            }
        }
    } else if (bitsPerPixel === 32) {
        // 32-bit BGRA
        for (let y = 0; y < height; y++) {
            const srcRow = topDown ? y : (height - 1 - y);
            const srcOffset = dataOffset + srcRow * width * 4;
            for (let x = 0; x < width; x++) {
                const sOff = srcOffset + x * 4;
                const dOff = (y * width + x) * 4;
                rgba[dOff + 0] = view.getUint8(sOff + 2); // R
                rgba[dOff + 1] = view.getUint8(sOff + 1); // G
                rgba[dOff + 2] = view.getUint8(sOff + 0); // B
                rgba[dOff + 3] = view.getUint8(sOff + 3); // A
            }
        }
    }

    return { width, height, data: rgba };
}

// Decode BI_RLE8 compressed pixel data
function decodeRLE8(
    view: DataView, offset: number,
    width: number, height: number, topDown: boolean,
    palette: Uint8Array, rgba: Uint8ClampedArray,
): void {
    let x = 0;
    let y = topDown ? 0 : height - 1;
    let pos = offset;

    while (pos < view.byteLength) {
        const count = view.getUint8(pos++);
        const value = view.getUint8(pos++);

        if (count > 0) {
            // Encoded run: repeat `value` for `count` pixels
            for (let i = 0; i < count && x < width; i++) {
                const dOff = (y * width + x) * 4;
                rgba[dOff + 0] = palette[value * 4 + 0];
                rgba[dOff + 1] = palette[value * 4 + 1];
                rgba[dOff + 2] = palette[value * 4 + 2];
                rgba[dOff + 3] = palette[value * 4 + 3];
                x++;
            }
        } else {
            // Escape codes
            if (value === 0) {
                // End of line
                x = 0;
                y += topDown ? 1 : -1;
            } else if (value === 1) {
                // End of bitmap
                break;
            } else if (value === 2) {
                // Delta: move cursor
                x += view.getUint8(pos++);
                y += (topDown ? 1 : -1) * view.getUint8(pos++);
            } else {
                // Absolute run: `value` literal pixels
                for (let i = 0; i < value && x < width; i++) {
                    const idx = view.getUint8(pos++);
                    const dOff = (y * width + x) * 4;
                    rgba[dOff + 0] = palette[idx * 4 + 0];
                    rgba[dOff + 1] = palette[idx * 4 + 1];
                    rgba[dOff + 2] = palette[idx * 4 + 2];
                    rgba[dOff + 3] = palette[idx * 4 + 3];
                    x++;
                }
                // Absolute runs are padded to 16-bit boundary
                if (value % 2 !== 0) pos++;
            }
        }
    }
}

// Load a texture from a file. Detects format by extension.
// BMP: parsed directly (handles indexed 8-bit + RLE).
// PNG/JPG: decoded by the browser's native image loader.
export async function loadTexture(
    url: string,
    gl: WebGLRenderingContext,
): Promise<WebGLTexture> {
    const ext = url.split('.').pop()?.toLowerCase() ?? '';

    if (ext === 'bmp') {
        // BMP: fetch as binary, parse ourselves
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        const { width, height, data } = parseBMP(buffer);

        const tex = gl.createTexture()!;
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0,
                      gl.RGBA, gl.UNSIGNED_BYTE, data);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        return tex;
    } else {
        // PNG, JPG, or anything else: let the browser decode it
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                const tex = gl.createTexture()!;
                gl.bindTexture(gl.TEXTURE_2D, tex);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
                resolve(tex);
            };
            img.onerror = () => reject(new Error(`Failed to load image: ${url}`));
            img.src = url;
        });
    }
}
