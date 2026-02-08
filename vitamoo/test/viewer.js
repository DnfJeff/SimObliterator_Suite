// VitaMoo character viewer — modern reimplementation of SimShow.
//
// Original SimShow (Maxis, 1999) by Don Hopkins:
//   MFC dialog + DirectX 3.0 + VitaBoy animation system.
//   Default character: b003mafit_01 + c003ma_romancrew (Dad Fit + RomanCrew).
//   Features: distance presets, 4-corner rotation, slow/fast auto-rotate,
//   body/head/hand selection, texture filtering by sex/age/body type/skin tone,
//   animation list, and "Import Into Game" export.
//
// This version: ES modules + WebGL + the same VitaBoy data pipeline,
// running in a browser 26 years later. Same Dad. Same RomanCrew head.

import { parseCMX, parseSKN, parseCFP } from '../dist/parser.js';
import { buildSkeleton, updateTransforms, deformMesh, findBone } from '../dist/skeleton.js';
import { Renderer } from '../dist/renderer.js';
import { loadTexture } from '../dist/texture.js';
import { Practice } from '../dist/animation.js';

const $ = id => document.getElementById(id);

// All loaded content, keyed by name
const content = {
    skeletons: {},   // name -> SkeletonData
    suits: {},       // name -> SuitData
    skills: {},      // name -> SkillData
    meshes: {},      // name -> MeshData
    textures: {},    // name -> filename (base name -> actual file)
};

// Content index from content.json (defaults and people presets)
let contentIndex = null;

// Rendering state
let renderer = null;
let activeSkeleton = null;  // Bone[]
let activeMeshes = [];      // {mesh, boneMap, texture}[]
let cameraTarget = { x: 0, y: 1.5, z: 0 };

// Animation playback
let activePractice = null;    // Practice instance (current animation)
let animationTime = 0;        // accumulated ticks (ms)
let lastFrameTime = 0;        // last timestamp from requestAnimationFrame
let paused = false;
const cfpCache = new Map();   // animationFileName -> ArrayBuffer (loaded CFP data)

// Rotation momentum state: drag left/right to spin, release to keep spinning.
// SimShow had fixed NW/NE/SW/SE angles + slow/fast auto-rotate.
// We do better: physics-based momentum with smoothed velocity tracking.
let rotationVelocity = 0;     // degrees per frame
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let lastDragX = 0;
let lastDragY = 0;
let lastDragTime = 0;
let dragMoved = false;
let dragButton = 0;           // 0=left (spin+zoom), 2=right (spin+orbit)
const DRAG_THRESHOLD = 3;     // pixels before it counts as drag vs click
const FRICTION = 0.985;       // velocity decay per frame (higher = less friction)
const VELOCITY_SMOOTHING = 0.3; // low-pass filter for mouse velocity
let smoothedVelocity = 0;

// Texture cache: base name -> WebGLTexture
const textureCache = new Map();

// Filter state (SimShow's sex/age/bodyType/skinTone filtering)
const filter = {
    enabled: false,
    sex: null,       // 'M', 'F', or null (any)
    age: null,       // 'A' (adult), 'C' (child), or null
    bodyType: null,  // 'Fit', 'Fat', 'Skn', or null
    skinTone: null,  // 'drk', 'lgt', 'med', or null
};

// DOM references
const statusEl = $('status');
const canvas = $('viewport');

function initRenderer() {
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    try {
        renderer = new Renderer(canvas);
        renderer.context.viewport(0, 0, canvas.width, canvas.height);
    } catch (e) {
        statusEl.textContent = 'WebGL error: ' + e.message;
    }
}

// Populate a <select> from an array of values with optional labels
function fillSelect(sel, items, labelFn) {
    while (sel.options.length > 1) sel.remove(1);
    for (const item of items) {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = labelFn ? labelFn(item) : item.replace(/\.(cmx|skn|bmp|png)$/i, '');
        sel.appendChild(opt);
    }
}

// Decode Sims naming convention for human-readable dropdown labels.
// Naming: B=body, C=head, H=hand, M=male, F=female, A=adult, C=child,
// Fat/Fit/Skn=body type, drk/lgt/med=skin tone.
function decodeMeshName(name) {
    const parts = [];
    const lower = name.toLowerCase();
    if (lower.includes('fafat')) parts.push('F Fat');
    else if (lower.includes('fafit')) parts.push('F Fit');
    else if (lower.includes('faskn')) parts.push('F Skinny');
    else if (lower.includes('mafat')) parts.push('M Fat');
    else if (lower.includes('mafit')) parts.push('M Fit');
    else if (lower.includes('maskn')) parts.push('M Skinny');
    else if (lower.includes('ucchd') || lower.includes('kbodynaked')) parts.push('Child');
    else if (lower.includes('fcchd')) parts.push('Girl');
    else if (lower.includes('mcchd')) parts.push('Boy');

    if (parts.length === 0) {
        const m = name.match(/[Cc]\d+[A-Za-z]{2}_(\w+)/);
        if (m) parts.push(m[1]);
        else parts.push(name.split('-').pop() || name);
    }

    // Extract suit number for disambiguation
    const numMatch = name.match(/[bc](\d+)/i);
    if (numMatch) parts.push('#' + numMatch[1]);

    return parts.join(' ');
}

function decodeTexName(name) {
    let label = name;
    // Extract the descriptive part after the code prefix
    const m = name.match(/(?:drk|lgt|med)_(\w+)/i);
    if (m) label = m[1];
    // Add skin tone indicator
    if (name.includes('drk')) label += ' (dark)';
    else if (name.includes('lgt')) label += ' (light)';
    else if (name.includes('med')) label += ' (med)';
    return label;
}

// Load a texture by base name, returning a cached WebGLTexture
async function getTexture(baseName) {
    if (!baseName || !renderer) return null;
    if (textureCache.has(baseName)) return textureCache.get(baseName);

    const fileName = content.textures[baseName];
    if (!fileName) {
        console.warn(`[getTexture] no file for "${baseName}"`);
        return null;
    }

    try {
        const tex = await loadTexture('data/' + fileName, renderer.context);
        textureCache.set(baseName, tex);
        console.log(`[getTexture] loaded "${baseName}" -> "${fileName}"`);
        return tex;
    } catch (e) {
        console.warn(`[getTexture] failed "${baseName}":`, e);
        return null;
    }
}

// Apply SimShow-style filtering to a list of names.
// The filter uses the Sims naming convention encoded in filenames.
function applyFilter(names, category) {
    if (!filter.enabled) return names;

    return names.filter(name => {
        const lower = name.toLowerCase();

        // Sex filter
        if (filter.sex === 'M' && !lower.includes('ma') && !lower.includes('mc') && !lower.includes('uc')) return false;
        if (filter.sex === 'F' && !lower.includes('fa') && !lower.includes('fc') && !lower.includes('uc')) return false;

        // Age filter
        if (filter.age === 'A' && (lower.includes('chd') || lower.includes('uc'))) return false;
        if (filter.age === 'C' && !lower.includes('chd') && !lower.includes('uc')) return false;

        // Body type filter (body meshes and textures only)
        if (filter.bodyType && (category === 'body' || category === 'bodyTex')) {
            const bt = filter.bodyType.toLowerCase();
            if (!lower.includes(bt)) return false;
        }

        // Skin tone filter (textures only)
        if (filter.skinTone && (category === 'bodyTex' || category === 'headTex' || category === 'handTex')) {
            if (!lower.includes(filter.skinTone)) return false;
        }

        return true;
    });
}

// Load content index and populate menus
async function loadContentIndex() {
    try {
        const resp = await fetch('content.json');
        contentIndex = await resp.json();

        statusEl.textContent = 'Loading CMX files...';

        // Load all CMX files (skeletons, suits, animations)
        const allCmx = [
            ...(contentIndex.skeletons || []),
            ...(contentIndex.suits || []),
            ...(contentIndex.animations || []),
        ];
        for (const name of allCmx) {
            try {
                const r = await fetch('data/' + name);
                if (!r.ok) continue;
                const cmx = parseCMX(await r.text());
                cmx.skeletons.forEach(s => content.skeletons[s.name] = s);
                cmx.suits.forEach(s => content.suits[s.name] = s);
                cmx.skills.forEach(s => content.skills[s.name] = s);
            } catch (e) { console.warn(name, e); }
        }

        statusEl.textContent = 'Loading meshes...';

        // Load all SKN meshes
        for (const name of (contentIndex.meshes || [])) {
            try {
                const r = await fetch('data/' + name);
                if (!r.ok) continue;
                const mesh = parseSKN(await r.text());
                content.meshes[mesh.name] = mesh;
            } catch (e) { console.warn(name, e); }
        }

        // Index texture filenames — prefer PNG over BMP (smaller, browser-native)
        for (const name of (contentIndex.textures_bmp || [])) {
            const base = name.replace(/\.(bmp|png)$/i, '');
            if (!content.textures[base]) content.textures[base] = name;
        }
        for (const name of (contentIndex.textures_png || [])) {
            const base = name.replace(/\.(bmp|png)$/i, '');
            content.textures[base] = name;
        }

        buildCfpIndex();
        populateMenus();

        const counts = {
            skel: Object.keys(content.skeletons).length,
            suit: Object.keys(content.suits).length,
            skill: Object.keys(content.skills).length,
            mesh: Object.keys(content.meshes).length,
            tex: Object.keys(content.textures).length,
        };
        statusEl.textContent = `Loaded: ${counts.skel} skeletons, ${counts.suit} suits, ${counts.skill} anims, ${counts.mesh} meshes, ${counts.tex} textures`;

        console.log('[loadContentIndex]', counts);

        // Auto-select first person preset (Dad Fit + RomanCrew, same since 1999)
        if (contentIndex.people?.length) {
            $('selPerson').value = '0';
            applyPerson(0);
        } else {
            applyDefaults();
        }

    } catch (e) {
        statusEl.textContent = 'Failed to load content.json: ' + e.message;
        console.error('[loadContentIndex]', e);
    }
}

function populateMenus() {
    // Skeletons
    fillSelect($('selSkeleton'), Object.keys(content.skeletons));

    // Auto-select skeleton based on age filter
    if (filter.enabled && filter.age) {
        const targetSkel = filter.age === 'C' ? 'child' : 'adult';
        setSelectValue('selSkeleton', targetSkel);
    }

    // Body meshes
    const allBodies = Object.keys(content.meshes).filter(n =>
        n.includes('BODY') || n.includes('KBODYNAKED'));
    fillSelect($('selBody'), applyFilter(allBodies, 'body'), decodeMeshName);

    // Head meshes (exclude SPECS accessories)
    const allHeads = Object.keys(content.meshes).filter(n =>
        n.includes('HEAD') && !n.includes('SPECS'));
    fillSelect($('selHead'), applyFilter(allHeads, 'head'), decodeMeshName);

    // Hand meshes
    const leftHands = Object.keys(content.meshes).filter(n => n.includes('L_HAND'));
    const rightHands = Object.keys(content.meshes).filter(n => n.includes('R_HAND'));
    fillSelect($('selLeftHand'), leftHands, decodeMeshName);
    fillSelect($('selRightHand'), rightHands, decodeMeshName);

    // Textures
    const bodyTexNames = Object.keys(content.textures).filter(n => /^B\d/.test(n));
    const headTexNames = Object.keys(content.textures).filter(n => /^C\d/.test(n));
    const handTexNames = Object.keys(content.textures).filter(n => n.startsWith('HU'));
    fillSelect($('selBodyTex'), applyFilter(bodyTexNames, 'bodyTex'), decodeTexName);
    fillSelect($('selHeadTex'), applyFilter(headTexNames, 'headTex'), decodeTexName);
    fillSelect($('selHandTex'), applyFilter(handTexNames, 'handTex'), decodeTexName);

    // Animations
    fillSelect($('selAnim'), Object.keys(content.skills));

    // People dropdown
    if (contentIndex?.people) {
        fillSelect($('selPerson'), contentIndex.people.map((_, i) => String(i)),
            i => contentIndex.people[i].name);
    }
}

// After filter changes, revalidate all dropdowns: if the current selection
// is no longer in the list, select the first available option.
function revalidateDropdowns() {
    for (const id of ['selSkeleton', 'selBody', 'selHead', 'selLeftHand', 'selRightHand',
                       'selBodyTex', 'selHeadTex', 'selHandTex']) {
        const sel = $(id);
        const current = sel.value;
        // Check if current value still exists in options
        let found = false;
        for (const opt of sel.options) {
            if (opt.value === current && opt.value) { found = true; break; }
        }
        if (!found && sel.options.length > 1) {
            sel.selectedIndex = 1; // select first real option (skip placeholder)
        }
    }
}


// Apply default selections (SimShow's gCharacterTable).
// Defaults = first person preset (Dad Fit + RomanCrew, same since 1999).
function applyDefaults() {
    if (!contentIndex?.defaults) return;
    const d = contentIndex.defaults;
    setSelectValue('selSkeleton', d.skeleton);
    setSelectValue('selBody', d.body);
    setSelectValue('selHead', d.head);
    setSelectValue('selLeftHand', d.leftHand);
    setSelectValue('selRightHand', d.rightHand);
    setSelectValue('selBodyTex', d.bodyTexture);
    setSelectValue('selHeadTex', d.headTexture);
    setSelectValue('selHandTex', d.handTexture);
    if (d.animation) setSelectValue('selAnim', d.animation);

    updateScene();
}

// Apply a person preset
function applyPerson(index) {
    if (!contentIndex?.people?.[index]) return;
    const p = contentIndex.people[index];
    setSelectValue('selSkeleton', p.skeleton);
    setSelectValue('selBody', p.body);
    setSelectValue('selHead', p.head);
    setSelectValue('selLeftHand', p.leftHand);
    setSelectValue('selRightHand', p.rightHand);
    setSelectValue('selBodyTex', p.bodyTexture);
    setSelectValue('selHeadTex', p.headTexture);
    setSelectValue('selHandTex', p.handTexture);
    if (p.animation) setSelectValue('selAnim', p.animation);
    updateScene();
}

// Set a <select> value — try exact match, then case-insensitive partial.
// The original SimShow matched suits by name with FindSuit() which was
// case-insensitive. We do the same here for content.json defaults.
function setSelectValue(selId, value) {
    if (!value) return;
    const sel = $(selId);
    // Exact match
    for (const opt of sel.options) {
        if (opt.value === value) { sel.value = value; return; }
    }
    // Case-insensitive exact match
    const lower = value.toLowerCase();
    for (const opt of sel.options) {
        if (opt.value && opt.value.toLowerCase() === lower) {
            sel.value = opt.value;
            return;
        }
    }
    // Partial substring match (skip empty placeholder options)
    for (const opt of sel.options) {
        if (!opt.value) continue;
        const optLower = opt.value.toLowerCase();
        if (optLower.includes(lower) || lower.includes(optLower)) {
            sel.value = opt.value;
            return;
        }
    }
}

// CFP file index: maps lowercase animationFileName -> actual filename on disk
const cfpIndex = new Map();

function buildCfpIndex() {
    if (!contentIndex?.cfp_files) return;
    for (const filename of contentIndex.cfp_files) {
        // Strip .cfp extension to get the animationFileName
        const key = filename.replace(/\.cfp$/i, '').toLowerCase();
        cfpIndex.set(key, filename);
    }
    console.log(`[buildCfpIndex] ${cfpIndex.size} CFP files indexed`);
}

// Compute camera target from skeleton bone positions
function computeCameraTarget() {
    if (!activeSkeleton || activeSkeleton.length === 0) {
        cameraTarget = { x: 0, y: 1.5, z: 0 };
        return;
    }
    let minY = Infinity, maxY = -Infinity;
    for (const bone of activeSkeleton) {
        const y = bone.worldPosition.y;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
    }
    cameraTarget = { x: 0, y: (minY + maxY) / 2, z: 0 };
    console.log(`[camera] target y=${cameraTarget.y.toFixed(2)} (bones y=${minY.toFixed(2)}..${maxY.toFixed(2)})`);
}

// Rebuild the scene when selections change
async function updateScene() {
    const skelName = $('selSkeleton').value;

    if (!skelName || !content.skeletons[skelName]) {
        activeSkeleton = null;
        activeMeshes = [];
        activePractice = null;
        renderFrame();
        return;
    }

    // Build everything into temporary variables first, so the animation
    // loop never sees a half-built state (rest pose flicker).
    const newSkeleton = buildSkeleton(content.skeletons[skelName]);
    updateTransforms(newSkeleton);
    const boneMap = new Map();
    newSkeleton.forEach(b => boneMap.set(b.name, b));

    const newMeshes = [];

    async function addMesh(meshName, texBaseName) {
        if (!meshName || !content.meshes[meshName]) return;
        const mesh = content.meshes[meshName];
        const texture = texBaseName ? await getTexture(texBaseName) : null;
        newMeshes.push({ mesh, boneMap, texture });
    }

    await addMesh($('selBody').value, $('selBodyTex').value);
    await addMesh($('selHead').value, $('selHeadTex').value);
    const handTex = $('selHandTex').value;
    await addMesh($('selLeftHand').value, handTex);
    await addMesh($('selRightHand').value, handTex);

    // Load animation for the selected skill
    const animName = $('selAnim').value;
    let newPractice = null;
    if (animName) {
        const skill = content.skills[animName];
        if (skill) {
            const cfpName = skill.animationFileName;
            if (!cfpCache.has(cfpName) && (skill.numTranslations > 0 || skill.numRotations > 0)) {
                const cfpFile = cfpIndex.get(cfpName.toLowerCase());
                if (cfpFile) {
                    try {
                        const r = await fetch('data/' + cfpFile);
                        if (r.ok) {
                            cfpCache.set(cfpName, await r.arrayBuffer());
                        }
                    } catch { /* skip */ }
                }
            }
            const buffer = cfpCache.get(cfpName);
            if (buffer) {
                skill.translations = [];
                skill.rotations = [];
                parseCFP(buffer, skill);
            }
            newPractice = new Practice(skill, newSkeleton);
        }
    }

    // Apply first animation frame before making anything visible
    if (newPractice?.ready) {
        newPractice.tick(1);
        updateTransforms(newSkeleton);
    }

    // Atomic swap: animation loop only ever sees a fully-posed character
    activeSkeleton = newSkeleton;
    activeMeshes = newMeshes;
    activePractice = newPractice;
    animationTime = 0;
    lastFrameTime = 0;
    computeCameraTarget();

    // Status
    const personIdx = parseInt($('selPerson').value);
    const personName = contentIndex?.people?.[personIdx]?.name;
    const animLabel = animName || 'idle';
    statusEl.textContent = personName
        ? `${personName} | ${animLabel}`
        : `${skelName} (${activeSkeleton.length} bones) | ${animLabel}`;
    renderFrame();
}

function renderFrame() {
    if (!renderer) return;
    renderer.clear();

    const zoom = parseFloat($('zoom').value) / 10;
    const rotY = parseFloat($('rotY').value) * Math.PI / 180;
    const rotX = parseFloat($('rotX').value) * Math.PI / 180;
    const dist = zoom;
    // Spherical coordinates: rotX tilts up/down, rotY spins around
    const cosX = Math.cos(rotX);
    const eyeX = Math.sin(rotY) * cosX * dist;
    const eyeY = cameraTarget.y + Math.sin(rotX) * dist;
    const eyeZ = Math.cos(rotY) * cosX * dist;

    renderer.setCamera(50, canvas.width / canvas.height, 0.01, 100,
                       eyeX, eyeY, eyeZ,
                       cameraTarget.x, cameraTarget.y, cameraTarget.z);

    for (const { mesh, boneMap, texture } of activeMeshes) {
        if (activeSkeleton) {
            const { vertices, normals } = deformMesh(mesh, activeSkeleton, boneMap);
            renderer.drawMesh(mesh, vertices, normals, texture || null);
        } else {
            renderer.drawMesh(mesh, mesh.vertices, mesh.normals, texture || null);
        }
    }
}

// Animation loop: ticks Practice animation + applies rotation momentum.
function animationLoop(timestamp) {
    let needsRender = false;

    // Tick animation Practice if active and not paused
    if (activePractice?.ready && activeSkeleton && !paused) {
        if (lastFrameTime === 0) lastFrameTime = timestamp;
        const dt = timestamp - lastFrameTime;
        lastFrameTime = timestamp;

        // Accumulate time in ms (Speed slider = 0-200, 100 = normal)
        const speedScale = parseFloat($('speed').value) / 100;
        animationTime += dt * speedScale;

        // Tick the practice (applies keyframes to bone positions/rotations)
        activePractice.tick(animationTime);

        // Propagate bone transforms through hierarchy
        updateTransforms(activeSkeleton);

        needsRender = true;
    }

    // Spin momentum
    if (!isDragging && Math.abs(rotationVelocity) > 0.001) {
        const rotSlider = $('rotY');
        let val = parseFloat(rotSlider.value) + rotationVelocity;
        if (val > 360) val -= 360;
        if (val < 0) val += 360;
        rotSlider.value = val;
        rotationVelocity *= FRICTION;
        needsRender = true;
    }

    if (needsRender) renderFrame();

    requestAnimationFrame(animationLoop);
}

// Mouse/touch interaction: drag left/right = spin, drag up/down = zoom
function setupMouseInteraction() {
    canvas.addEventListener('contextmenu', e => e.preventDefault());

    canvas.addEventListener('mousedown', e => {
        isDragging = true;
        dragMoved = false;
        // Shift+left click = orbit (same as right button)
        dragButton = (e.button === 0 && e.shiftKey) ? 2 : e.button;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        lastDragX = e.clientX;
        lastDragY = e.clientY;
        lastDragTime = performance.now();
        smoothedVelocity = 0;
        canvas.style.cursor = 'grabbing';
        canvas.focus();
        e.preventDefault();
    });

    window.addEventListener('mousemove', e => {
        if (!isDragging) return;

        const dx = e.clientX - lastDragX;
        const dy = e.clientY - lastDragY;
        const now = performance.now();
        const dt = Math.max(now - lastDragTime, 1);

        // Check if mouse moved enough to count as drag
        const totalDx = e.clientX - dragStartX;
        const totalDy = e.clientY - dragStartY;
        if (Math.abs(totalDx) > DRAG_THRESHOLD || Math.abs(totalDy) > DRAG_THRESHOLD) {
            dragMoved = true;
        }

        if (dragButton === 0) {
            // Left button: horizontal = spin, vertical = zoom
            const rotSlider = $('rotY');
            let rotVal = parseFloat(rotSlider.value) - dx * 0.5;
            if (rotVal > 360) rotVal -= 360;
            if (rotVal < 0) rotVal += 360;
            rotSlider.value = rotVal;

            const zoomSlider = $('zoom');
            let zoomVal = parseFloat(zoomSlider.value) + dy * 0.4;
            zoomVal = Math.max(1, Math.min(200, zoomVal));
            zoomSlider.value = zoomVal;
        }

        if (dragButton === 2) {
            // Right button: direct orbit only — horizontal = rotate, vertical = tilt
            // No zoom, no inertia, just direct camera control
            const rotSlider = $('rotY');
            let rotVal = parseFloat(rotSlider.value) - dx * 0.5;
            if (rotVal > 360) rotVal -= 360;
            if (rotVal < 0) rotVal += 360;
            rotSlider.value = rotVal;

            const tiltSlider = $('rotX');
            let tiltVal = parseFloat(tiltSlider.value) + dy * 0.3;
            tiltVal = Math.max(-89, Math.min(89, tiltVal));
            tiltSlider.value = tiltVal;
        }

        // Track instantaneous velocity with smoothing (left button only)
        const instantVelocity = dragButton === 0 ? (-dx * 0.5) / (dt / 16.67) : 0;
        smoothedVelocity = smoothedVelocity * (1 - VELOCITY_SMOOTHING) +
                           instantVelocity * VELOCITY_SMOOTHING;

        lastDragX = e.clientX;
        lastDragY = e.clientY;
        lastDragTime = now;

        renderFrame();
    });

    window.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        canvas.style.cursor = 'grab';

        if (dragButton === 0 && dragMoved) {
            // Left button release with momentum — carry the smoothed velocity
            rotationVelocity = smoothedVelocity;
        } else if (dragButton === 0) {
            // Left click without drag — stop spinning
            rotationVelocity = 0;
        }
        // Right button: no momentum, just stops
    });

    // Mouse wheel / trackpad scroll / pinch-to-zoom
    canvas.addEventListener('wheel', e => {
        e.preventDefault();
        const zoomSlider = $('zoom');
        let delta;
        if (e.ctrlKey) {
            // Pinch-to-zoom in Chrome: ctrlKey + small deltaY
            delta = e.deltaY * 0.3;
        } else if (e.deltaMode === 1) {
            // Line-based scroll (mouse wheel): deltaY is ~3
            delta = e.deltaY * 3;
        } else {
            // Pixel-based scroll (trackpad): deltaY is ~1-10 per tick
            delta = e.deltaY * 0.15;
        }
        let val = parseFloat(zoomSlider.value) + delta;
        val = Math.max(1, Math.min(200, val));
        zoomSlider.value = val;
        renderFrame();
    }, { passive: false });

    // Safari gesturechange (native pinch events)
    canvas.addEventListener('gesturestart', e => e.preventDefault());
    canvas.addEventListener('gesturechange', e => {
        e.preventDefault();
        const zoomSlider = $('zoom');
        // e.scale: >1 = zoom in, <1 = zoom out
        let val = parseFloat(zoomSlider.value) / e.scale;
        val = Math.max(1, Math.min(200, val));
        zoomSlider.value = val;
        renderFrame();
    });

    canvas.style.cursor = 'grab';
}

// Step through people presets
function stepPerson(direction) {
    if (!contentIndex?.people?.length) return;
    const sel = $('selPerson');
    let idx = parseInt(sel.value);
    if (isNaN(idx)) idx = direction > 0 ? 0 : contentIndex.people.length - 1;
    else idx += direction;
    if (idx < 0) idx = contentIndex.people.length - 1;
    if (idx >= contentIndex.people.length) idx = 0;
    sel.value = String(idx);
    applyPerson(idx);
}

function togglePause() {
    paused = !paused;
    const btn = $('btnPause');
    if (btn) {
        btn.textContent = paused ? 'Play' : 'Pause';
        btn.classList.toggle('active', paused);
    }
    if (!paused) lastFrameTime = 0; // reset dt so no time jump on resume
}

// Step animation dropdown forward or backward
function stepAnimation(direction) {
    const sel = $('selAnim');
    if (sel.options.length <= 1) return;
    let idx = sel.selectedIndex + direction;
    // Wrap around (skip the first "-- idle --" placeholder)
    if (idx < 1) idx = sel.options.length - 1;
    if (idx >= sel.options.length) idx = 1;
    sel.selectedIndex = idx;
    updateScene();
}

// SimShow distance presets: Far, Medium, Near
function setDistance(preset) {
    const zoomSlider = $('zoom');
    switch (preset) {
        case 'far':    zoomSlider.value = 180; break;
        case 'medium': zoomSlider.value = 100; break;
        case 'near':   zoomSlider.value = 50; break;
    }
    document.querySelectorAll('.dist-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.dist-btn[data-dist="${preset}"]`);
    if (btn) btn.classList.add('active');
    renderFrame();
}

// Filter button toggle handler
function setupFilters() {
    document.querySelectorAll('.filter-btn[data-filter]').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.dataset.filter;
            const val = btn.dataset.value;

            // Toggle: if already active, deactivate
            if (filter[key] === val) {
                filter[key] = null;
                btn.classList.remove('active');
            } else {
                // Deactivate siblings in same filter group
                document.querySelectorAll(`.filter-btn[data-filter="${key}"]`)
                    .forEach(b => b.classList.remove('active'));
                filter[key] = val;
                btn.classList.add('active');
            }

            // Remember current selections before repopulating
            const sel = {
                skeleton: $('selSkeleton').value,
                body: $('selBody').value,
                head: $('selHead').value,
                bodyTex: $('selBodyTex').value,
                headTex: $('selHeadTex').value,
                handTex: $('selHandTex').value,
            };

            populateMenus();

            // Restore selections if still available
            setSelectValue('selSkeleton', sel.skeleton);
            setSelectValue('selBody', sel.body);
            setSelectValue('selHead', sel.head);
            setSelectValue('selBodyTex', sel.bodyTex);
            setSelectValue('selHeadTex', sel.headTex);
            setSelectValue('selHandTex', sel.handTex);

            // If any selection is no longer valid, pick first available
            revalidateDropdowns();
            updateScene();
        });
    });

    // Filter enable/disable
    const filterToggle = $('filterToggle');
    if (filterToggle) {
        filterToggle.addEventListener('change', () => {
            filter.enabled = filterToggle.checked;
            populateMenus();
            revalidateDropdowns();
            updateScene();
        });
    }
}

// Wire up all event listeners
function setupEventListeners() {
    // Selection changes trigger scene rebuild
    for (const id of ['selSkeleton', 'selBody', 'selHead', 'selLeftHand', 'selRightHand',
                       'selBodyTex', 'selHeadTex', 'selHandTex', 'selAnim']) {
        $(id).addEventListener('change', updateScene);
    }

    // Camera controls trigger immediate re-render
    for (const id of ['rotY', 'rotX', 'zoom', 'speed']) {
        $(id).addEventListener('input', renderFrame);
    }

    // Distance preset buttons
    document.querySelectorAll('.dist-btn').forEach(btn => {
        btn.addEventListener('click', () => setDistance(btn.dataset.dist));
    });

    // People prev/next buttons and dropdown
    const btnPersonPrev = $('btnPersonPrev');
    const btnPersonNext = $('btnPersonNext');
    if (btnPersonPrev) btnPersonPrev.addEventListener('click', () => stepPerson(-1));
    if (btnPersonNext) btnPersonNext.addEventListener('click', () => stepPerson(1));
    $('selPerson').addEventListener('change', () => {
        const idx = parseInt($('selPerson').value);
        if (!isNaN(idx)) applyPerson(idx);
    });

    // Animation prev/next buttons
    const btnPrev = $('btnAnimPrev');
    const btnNext = $('btnAnimNext');
    if (btnPrev) btnPrev.addEventListener('click', () => stepAnimation(-1));
    if (btnNext) btnNext.addEventListener('click', () => stepAnimation(1));

    // Pause/resume button
    const btnPause = $('btnPause');
    if (btnPause) btnPause.addEventListener('click', togglePause);

    // Keyboard: left/right arrows step animation, space = pause
    canvas.tabIndex = 0;
    canvas.addEventListener('keydown', e => {
        if (e.key === 'ArrowLeft') { stepAnimation(-1); e.preventDefault(); }
        if (e.key === 'ArrowRight') { stepAnimation(1); e.preventDefault(); }
        if (e.key === ' ') { togglePause(); e.preventDefault(); }
    });

    // Mouse drag interaction on canvas
    setupMouseInteraction();

    // Drag and drop files
    const dropZone = $('dropZone');
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('over'));
    dropZone.addEventListener('drop', async e => {
        e.preventDefault();
        dropZone.classList.remove('over');
        for (const file of e.dataTransfer.files) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext === 'cmx') {
                const cmx = parseCMX(await file.text());
                cmx.skeletons.forEach(s => { content.skeletons[s.name] = s; });
                cmx.suits.forEach(s => { content.suits[s.name] = s; });
                cmx.skills.forEach(s => { content.skills[s.name] = s; });
                statusEl.textContent = `Loaded ${file.name}`;
            } else if (ext === 'skn') {
                const mesh = parseSKN(await file.text());
                content.meshes[mesh.name] = mesh;
                statusEl.textContent = `Loaded ${file.name}: ${mesh.vertices.length} verts`;
            }
        }
        populateMenus();
    });

    // Window resize — update canvas size and GL viewport
    window.addEventListener('resize', () => {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        if (renderer) renderer.context.viewport(0, 0, canvas.width, canvas.height);
        renderFrame();
    });

    // Filters
    setupFilters();
}

// Boot
initRenderer();
setupEventListeners();
loadContentIndex();
animationLoop();
// Focus canvas for keyboard input
canvas.focus();
