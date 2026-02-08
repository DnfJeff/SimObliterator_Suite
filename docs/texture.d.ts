export declare function parseBMP(buffer: ArrayBuffer): {
    width: number;
    height: number;
    data: Uint8ClampedArray;
};
export declare function loadTexture(url: string, gl: WebGLRenderingContext): Promise<WebGLTexture>;
