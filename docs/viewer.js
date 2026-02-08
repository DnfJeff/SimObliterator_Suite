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

import { parseCMX, parseSKN, parseCFP } from './parser.js';
import { buildSkeleton, updateTransforms, deformMesh, findBone } from './skeleton.js';
import { Renderer } from './renderer.js';
import { loadTexture } from './texture.js';
import { Practice } from './animation.js';

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
let activeSkeleton = null;  // Bone[] (primary body for solo mode)
let activeMeshes = [];      // {mesh, boneMap, texture}[] (primary body)
let cameraTarget = { x: 0, y: 2.5, z: 0 };

// Animation playback
let activePractice = null;    // Practice instance (primary body)
let animationTime = 0;        // accumulated ticks (ms)
let lastFrameTime = 0;        // last timestamp from requestAnimationFrame
let paused = false;

// Multi-body scene support. Each body is an independent character with its own
// skeleton, meshes, animation, position, top-physics state, and voice params.
// In solo mode, bodies[] has one entry. In scene mode, multiple.
function createBody() {
    return {
        skeleton: null,      // Bone[]
        meshes: [],          // {mesh, boneMap, texture}[]
        practice: null,      // Practice instance
        personData: null,    // reference to content.json character entry
        x: 0, z: 0,         // world position offset
        direction: 0,        // facing angle (degrees)
        spinOffset: 0,       // per-body spin accumulated from drag (degrees)
        spinVelocity: 0,     // per-body spin momentum (degrees per frame)
        top: {               // per-body top physics (independent spin/tilt/drift)
            active: false, tilt: 0, tiltTarget: 0,
            precessionAngle: 0, nutationPhase: 0, nutationAmp: 0,
            driftX: 0, driftZ: 0, driftVX: 0, driftVZ: 0,
        },
    };
}
let bodies = [];              // Body[] — all characters in the current scene
let activeScene = null;       // current scene name or null (solo mode)
let selectedActorIndex = -1;  // which actor in bodies[] is selected for editing (-1 = none)
const cfpCache = new Map();   // animationFileName -> ArrayBuffer (loaded CFP data)
const _skelCache = {};        // skelFile -> CMX text (preloaded skeleton data)

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
const FRICTION = 0.98;        // velocity decay per frame (lower = slows faster)
// Held key state for smooth per-frame arrow key input
const _keysHeld = { up: false, down: false, left: false, right: false, leftStart: 0, rightStart: 0 };
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
        let cmxLoaded = 0, cmxFailed = 0;
        for (const name of allCmx) {
            try {
                const r = await fetch('data/' + name);
                if (!r.ok) {
                    console.error(`[loadContentIndex] CMX fetch FAILED: ${r.status} for "${name}"`);
                    cmxFailed++;
                    continue;
                }
                const cmx = parseCMX(await r.text());
                cmx.skeletons.forEach(s => content.skeletons[s.name] = s);
                cmx.suits.forEach(s => content.suits[s.name] = s);
                cmx.skills.forEach(s => content.skills[s.name] = s);
                cmxLoaded++;
            } catch (e) {
                console.error(`[loadContentIndex] CMX parse EXCEPTION for "${name}":`, e);
                cmxFailed++;
            }
        }
        console.log(`[loadContentIndex] CMX: ${cmxLoaded} loaded, ${cmxFailed} failed out of ${allCmx.length}`);
        console.log(`[loadContentIndex] Skills loaded: [${Object.keys(content.skills).join(', ')}]`);

        statusEl.textContent = 'Loading meshes...';

        // Load all SKN meshes
        let meshLoaded = 0, meshFailed = 0;
        for (const name of (contentIndex.meshes || [])) {
            try {
                const r = await fetch('data/' + name);
                if (!r.ok) {
                    console.error(`[loadContentIndex] SKN fetch FAILED: ${r.status} for "${name}"`);
                    meshFailed++;
                    continue;
                }
                const mesh = parseSKN(await r.text());
                content.meshes[mesh.name] = mesh;
                meshLoaded++;
            } catch (e) {
                console.error(`[loadContentIndex] SKN parse EXCEPTION for "${name}":`, e);
                meshFailed++;
            }
        }
        console.log(`[loadContentIndex] Meshes: ${meshLoaded} loaded, ${meshFailed} failed out of ${(contentIndex.meshes || []).length}`);

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

        // Classic Sims loading screen messages
        const loadingMessages = [
            'Reticulating Splines...',
            'Adjusting Emotional Weights...',
            'Calibrating Personality Matrix...',
            'Compressing Sim Genomes...',
            'Calculating Snowfall Coefficients...',
            'Tokenizing Elf Language...',
            'Possessing Animate Objects...',
            'Inserting Alarm Clock...',
            'Computing Optimal Bin Packing...',
            'Preparing Neighborly Greetings...',
            'Simmifying Name Savant...',
            'Synthesizing Gravity...',
            'Collecting Bonus Diamonds...',
            'Loading Lovingly Handcrafted Sims...',
            'Applying Alarm Clock Patch...',
            'Fabricating Social Constructs...',
            'Convincing Sims They Have Free Will...',
            'Polishing Countertop Surfaces...',
            'Debugging Dream Sequences...',
            'Unbarricading Elevator...',
            'Reconfiguring Vertical Transporter...',
            'Priming Geodesic Abreaction...',
            'Lecturing Errant Unicorns...',
            'Pressurizing Fruit Punch...',
        ];
        let loadMsgIdx = 0;
        const loaderText = document.querySelector('.loader-text');
        const cycleMessage = () => {
            if (loaderText) loaderText.textContent = loadingMessages[loadMsgIdx % loadingMessages.length];
            loadMsgIdx++;
        };
        cycleMessage();
        const msgInterval = setInterval(cycleMessage, 800);

        // Preload ALL character data so scene switching is instant:
        // skeleton CMX files, all textures, and all CFP animation data.
        statusEl.textContent = 'Preloading characters...';

        // Cache skeleton CMX files (usually just "adult" and "child")
        const skelNames = new Set();
        if (contentIndex.characters) {
            for (const c of contentIndex.characters) skelNames.add(c.skeleton || 'adult');
        }
        for (const skelName of skelNames) {
            const skelFile = skelName.includes('.cmx') ? skelName : skelName + '-skeleton.cmx';
            if (!_skelCache[skelFile]) {
                try {
                    const r = await fetch('data/' + skelFile);
                    if (r.ok) _skelCache[skelFile] = await r.text();
                } catch (e) { console.error(`[preload] skeleton "${skelFile}":`, e); }
            }
        }

        // Preload all textures referenced by characters
        const texNames = new Set();
        if (contentIndex.characters) {
            for (const c of contentIndex.characters) {
                if (c.bodyTexture) texNames.add(c.bodyTexture);
                if (c.headTexture) texNames.add(c.headTexture);
                if (c.handTexture) texNames.add(c.handTexture);
            }
        }
        let texLoaded = 0;
        for (const texName of texNames) {
            if (loaderText) loaderText.textContent = `Loading textures... ${++texLoaded}/${texNames.size}`;
            await getTexture(texName);
        }

        // Preload all CFP animation data
        const cfpNames = new Set();
        for (const skill of Object.values(content.skills)) {
            const cfpName = skill.animationFileName;
            if (cfpName && !cfpCache.has(cfpName) && (skill.numTranslations > 0 || skill.numRotations > 0)) {
                cfpNames.add(cfpName);
            }
        }
        let cfpLoaded = 0;
        for (const cfpName of cfpNames) {
            if (loaderText) loaderText.textContent = `Loading animations... ${++cfpLoaded}/${cfpNames.size}`;
            const bare = cfpName.toLowerCase();
            const cfpFile = cfpIndex.get(bare) || cfpIndex.get('xskill-' + bare);
            if (cfpFile) {
                try {
                    const r = await fetch('data/' + cfpFile);
                    if (r.ok) cfpCache.set(cfpName, await r.arrayBuffer());
                } catch (e) { }
            }
        }

        console.log(`[preload] skeletons=${skelNames.size} textures=${texNames.size} cfp=${cfpNames.size}`);

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

        // Auto-load first scene or fall back to first character
        if (contentIndex.scenes?.length) {
            $('selScene').value = '0';
            await loadScene(0);
        } else if (contentIndex.characters?.length) {
            $('selCharacter').value = '0';
            applyCharacter(0);
        } else {
            applyDefaults();
        }

        // Hide loading overlay
        clearInterval(msgInterval);
        const overlay = $('loadingOverlay');
        if (overlay) {
            overlay.classList.add('done');
            setTimeout(() => overlay.remove(), 500);
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

    // Character dropdown
    if (contentIndex?.characters) {
        fillSelect($('selCharacter'), contentIndex.characters.map((_, i) => String(i)),
            i => contentIndex.characters[i].name);
    }

    // Scene dropdown
    const sceneSel = $('selScene');
    if (sceneSel) {
        while (sceneSel.options.length) sceneSel.remove(0);
        if (contentIndex?.scenes) {
            for (let i = 0; i < contentIndex.scenes.length; i++) {
                const opt = document.createElement('option');
                opt.value = String(i);
                opt.textContent = contentIndex.scenes[i].name;
                sceneSel.appendChild(opt);
            }
        }
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
// Defaults = first character preset (Dad Fit + RomanCrew, same since 1999).
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

// Apply a character preset
function applyCharacter(index) {
    if (!contentIndex?.characters?.[index]) return;
    const p = contentIndex.characters[index];
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

// Find a character entry by name (case-insensitive)
function findCharacterByName(name) {
    if (!contentIndex?.characters) return null;
    const lower = name.toLowerCase();
    return contentIndex.characters.find(c => c.name.toLowerCase() === lower) || null;
}

// Load a multi-body scene. Each cast member gets their own Body with independent
// skeleton, meshes, animation, position, and top-physics state.
async function loadScene(sceneIndex) {
    if (!contentIndex?.scenes?.[sceneIndex]) {
        console.error(`[loadScene] INVALID scene index ${sceneIndex}, scenes available: ${contentIndex?.scenes?.length ?? 0}`);
        return;
    }
    const scene = contentIndex.scenes[sceneIndex];
    console.log(`[loadScene] === LOADING SCENE "${scene.name}" with ${scene.cast.length} cast members ===`);
    activeScene = scene.name;
    // Build into a LOCAL array — don't touch the live bodies[] until ALL are loaded.
    // This prevents the animation loop from ticking partially-loaded bodies.
    const newBodies = [];

    for (let ci = 0; ci < scene.cast.length; ci++) {
        const cast = scene.cast[ci];
        const char = findCharacterByName(cast.character);
        if (!char) {
            console.error(`[loadScene] CAST[${ci}] character NOT FOUND: "${cast.character}" — skipping`);
            continue;
        }

        const body = createBody();
        body.personData = char;
        body.actorName = cast.actor || `Actor ${ci + 1}`;
        body.x = cast.x || 0;
        body.z = cast.z || 0;
        body.direction = cast.direction || 0;

        // Load skeleton (from preloaded cache or fetch)
        const skelName = char.skeleton || 'adult';
        const skelFile = skelName.includes('.cmx') ? skelName : skelName + '-skeleton.cmx';
        try {
            let skelText = _skelCache[skelFile];
            if (!skelText) {
                const skelResp = await fetch('data/' + skelFile);
                if (!skelResp.ok) {
                    console.error(`[loadScene] CAST[${ci}] "${cast.character}" skeleton fetch FAILED: ${skelResp.status} ${skelResp.statusText} for "${skelFile}"`);
                    continue;
                }
                skelText = await skelResp.text();
                _skelCache[skelFile] = skelText;
            }
            const skelData = parseCMX(skelText);
            if (skelData.skeletons?.length) {
                body.skeleton = buildSkeleton(skelData.skeletons[0]);
                updateTransforms(body.skeleton);
            } else {
                console.error(`[loadScene] CAST[${ci}] "${cast.character}" parseCMX returned 0 skeletons from "${skelFile}"`);
            }
        } catch (e) {
            console.error(`[loadScene] CAST[${ci}] "${cast.character}" skeleton EXCEPTION for "${skelFile}":`, e);
        }

        if (!body.skeleton) {
            console.error(`[loadScene] CAST[${ci}] "${cast.character}" has NO SKELETON — skipping entirely`);
            continue;
        }

        // Load meshes (body, head, hands) with textures
        const meshParts = [
            { label: 'body',      name: char.body,      tex: char.bodyTexture },
            { label: 'head',      name: char.head,      tex: char.headTexture },
            { label: 'leftHand',  name: char.leftHand,  tex: char.handTexture },
            { label: 'rightHand', name: char.rightHand, tex: char.handTexture },
        ];
        for (const part of meshParts) {
            if (!part.name) {
                console.warn(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: name is empty/null, skipping`);
                continue;
            }
            const meshKey = part.name;
            if (!content.meshes[meshKey]) {
                // Try to find by case-insensitive match before fetching
                const lowerKey = meshKey.toLowerCase();
                const ciMatch = Object.keys(content.meshes).find(k => k.toLowerCase() === lowerKey);
                if (ciMatch) {
                    console.warn(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: exact key "${meshKey}" not found but case-insensitive match "${ciMatch}" exists — using it`);
                    content.meshes[meshKey] = content.meshes[ciMatch];
                } else {
                    // Load SKN as fallback
                    const sknFile = meshKey + '.skn';
                    console.warn(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: key "${meshKey}" not in preloaded meshes (${Object.keys(content.meshes).length} loaded), trying fetch "${sknFile}"`);
                    try {
                        const resp = await fetch('data/' + sknFile);
                        if (!resp.ok) {
                            console.error(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: fetch "${sknFile}" FAILED: ${resp.status} ${resp.statusText}`);
                            continue;
                        }
                        const text = await resp.text();
                        const parsed = parseSKN(text);
                        content.meshes[meshKey] = parsed;
                        console.warn(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: dynamically loaded "${sknFile}" → internal name "${parsed.name}"`);
                    } catch (e) {
                        console.error(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: SKN load EXCEPTION for "${sknFile}":`, e);
                        continue;
                    }
                }
            }
            const mesh = content.meshes[meshKey];
            if (!mesh) {
                console.error(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: mesh STILL NULL after load attempts for "${meshKey}"`);
                continue;
            }
            const boneMap = new Map();
            for (const bone of body.skeleton) {
                boneMap.set(bone.name, bone);
            }

            // Use the same getTexture() as solo mode — returns cached WebGLTexture
            let texture = null;
            if (part.tex) {
                texture = await getTexture(part.tex);
                if (!texture) {
                    console.warn(`[loadScene] CAST[${ci}] "${cast.character}" ${part.label}: texture "${part.tex}" failed to load`);
                }
            }
            body.meshes.push({ mesh, boneMap, texture });
        }

        if (body.meshes.length === 0) {
            console.error(`[loadScene] CAST[${ci}] "${cast.character}" has ZERO meshes — body will be invisible!`);
        }

        // Load animation — DEEP COPY the skill so multiple bodies don't share/corrupt the same skill object
        const animName = cast.animation || char.animation;
        if (animName) {
            body.practice = await loadAnimationForBody(animName, body.skeleton, `CAST[${ci}] "${cast.character}"`);
            if (!body.practice) {
                console.error(`[loadScene] CAST[${ci}] "${cast.character}" animation "${animName}" returned NULL practice — body will be frozen!`);
            } else if (!body.practice.ready) {
                console.error(`[loadScene] CAST[${ci}] "${cast.character}" animation "${animName}" practice NOT READY (translations=${body.practice.skill.translations.length} rotations=${body.practice.skill.rotations.length}) — body will be frozen!`);
            }
        } else {
            console.warn(`[loadScene] CAST[${ci}] "${cast.character}" has no animation specified — body will be idle`);
        }

        newBodies.push(body);
    }

    // Scene health diagnostic
    console.log(`[loadScene] === SCENE "${scene.name}" LOADED: ${newBodies.length}/${scene.cast.length} bodies ===`);
    for (let i = 0; i < newBodies.length; i++) {
        const b = newBodies[i];
        const name = b.personData?.name || '?';
        const hasSkel = !!b.skeleton;
        const meshCount = b.meshes.length;
        const hasPractice = !!b.practice;
        const practiceReady = b.practice?.ready ?? false;
        const transLen = b.practice?.skill?.translations?.length ?? 0;
        const rotLen = b.practice?.skill?.rotations?.length ?? 0;
        const bindingCount = b.practice?.bindings?.length ?? 0;
        const status = (hasSkel && meshCount > 0 && hasPractice && practiceReady) ? 'ALIVE' : 'DEAD';
        const issues = [];
        if (!hasSkel) issues.push('NO_SKELETON');
        if (meshCount === 0) issues.push('NO_MESHES');
        if (!hasPractice) issues.push('NO_PRACTICE');
        if (hasPractice && !practiceReady) issues.push('PRACTICE_NOT_READY');
        if (hasPractice && transLen === 0 && rotLen === 0) issues.push('NO_ANIM_DATA');
        if (hasPractice && bindingCount === 0) issues.push('NO_BONE_BINDINGS');
        const issueStr = issues.length > 0 ? ` ISSUES=[${issues.join(',')}]` : '';
        if (status === 'DEAD') {
            console.error(`[loadScene] BODY[${i}] "${name}" ${status} skel=${hasSkel} meshes=${meshCount} practice=${hasPractice} ready=${practiceReady} trans=${transLen} rots=${rotLen} bindings=${bindingCount}${issueStr}`);
        } else {
            console.log(`[loadScene] BODY[${i}] "${name}" ${status} meshes=${meshCount} bindings=${bindingCount}`);
        }
    }

    // ATOMIC SWAP: animation loop only ever sees a fully-loaded scene.
    // All bodies are built, all practices are ready — now make them live.
    bodies = newBodies;

    // Populate Actor dropdown from cast.
    // 1 actor: no "All", auto-select the only actor.
    // 2+ actors: "All" at top, default to All.
    const actorSel = $('selActor');
    const actorGroup = $('actorGroup');
    if (actorSel) {
        while (actorSel.options.length) actorSel.remove(0);
        if (bodies.length > 1) {
            const allOpt = document.createElement('option');
            allOpt.value = '-1';
            allOpt.textContent = `All (${bodies.length})`;
            actorSel.appendChild(allOpt);
        }
        for (let i = 0; i < bodies.length; i++) {
            const opt = document.createElement('option');
            opt.value = String(i);
            opt.textContent = bodies[i].actorName;
            actorSel.appendChild(opt);
        }
        if (bodies.length === 1) {
            selectedActorIndex = 0;
            actorSel.value = '0';
        } else {
            selectedActorIndex = -1;
            actorSel.value = '-1';
        }
    }
    if (actorGroup) actorGroup.style.display = bodies.length > 0 ? '' : 'none';

    // Sync dropdowns to the selected actor (or neutral if All)
    if (selectedActorIndex >= 0 && bodies[selectedActorIndex]) {
        const body = bodies[selectedActorIndex];
        if (body.personData && contentIndex?.characters) {
            const charIdx = contentIndex.characters.findIndex(c => c.name === body.personData.name);
            if (charIdx >= 0) $('selCharacter').value = String(charIdx);
        }
        if (body.practice?.skill?.name) {
            setSelectValue('selAnim', body.practice.skill.name);
        }
    }
    updateActorEditingUI();

    // Set primary body refs for compatibility (camera target, status, etc.)
    if (bodies.length > 0) {
        activeSkeleton = bodies[0].skeleton;
        activeMeshes = bodies[0].meshes;
        activePractice = bodies[0].practice;
        // Camera targets center of the group
        let cx = 0, cz = 0;
        for (const b of bodies) { cx += b.x; cz += b.z; }
        cx /= bodies.length; cz /= bodies.length;
        cameraTarget = { x: cx, y: 2.5, z: cz };
    }

    // Don't reset animationTime or lastFrameTime — new Practices handle their own
    // warmup via lastTicks=0. Resetting to 0 caused a one-frame flash of rest pose
    // because tick(0) returns immediately without applying motions.
    _animDiagLogged = false;
    const statusEl2 = $('status');
    if (statusEl2) statusEl2.textContent = `Scene: ${scene.name} (${bodies.length} characters)`;
    renderFrame();
}

// Load an animation (Practice) for a specific body's skeleton.
// Uses the same CFP loading path as the solo loader in updateScene().
async function loadAnimationForBody(animName, skeleton, debugLabel = '') {
    const tag = `[loadAnimForBody] ${debugLabel}`;

    // Find the skill by name in already-loaded skills
    let skill = content.skills[animName];
    let matchMethod = skill ? 'exact' : null;

    if (!skill) {
        // Search by internal name field (case-insensitive)
        const lower = animName.toLowerCase();
        skill = Object.values(content.skills).find(
            s => s.name?.toLowerCase() === lower
        );
        if (skill) matchMethod = 'case-insensitive';
        // Substring match: "adult-dance-inplace-twistloop" matches "a2o-dance-inplace-twistloop"
        if (!skill) {
            // Strip common prefixes and try matching the tail
            const stripped = lower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
            skill = Object.values(content.skills).find(s => {
                const sLower = (s.name || '').toLowerCase();
                const sStripped = sLower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
                return sStripped === stripped || sLower.includes(stripped) || stripped.includes(sLower.replace(/^a2o-/, ''));
            });
            if (skill) matchMethod = 'stripped-prefix';
        }
    }

    if (!skill) {
        // Try loading all animation CMXs to find the skill
        console.warn(`${tag} "${animName}" not in ${Object.keys(content.skills).length} loaded skills, loading all CMXs...`);
        for (const cmxFile of contentIndex.animations || []) {
            if (content.skills[cmxFile.replace('.cmx', '')]) continue;
            try {
                const resp = await fetch('data/' + cmxFile);
                if (!resp.ok) {
                    console.error(`${tag} CMX fetch failed: ${resp.status} for "${cmxFile}"`);
                    continue;
                }
                const text = await resp.text();
                const data = parseCMX(text);
                for (const s of data.skills || []) content.skills[s.name] = s;
            } catch (e) {
                console.error(`${tag} CMX load exception for "${cmxFile}":`, e);
            }
        }
        const lower = animName.toLowerCase();
        const stripped = lower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
        skill = Object.values(content.skills).find(s => {
            const sLower = (s.name || '').toLowerCase();
            const sStripped = sLower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
            return sLower === lower || sStripped === stripped;
        });
        if (skill) matchMethod = 'full-scan';
    }

    if (!skill) {
        console.error(`${tag} SKILL NOT FOUND: "${animName}" — available skills: [${Object.keys(content.skills).join(', ')}]`);
        return null;
    }

    if (!skill.motions?.length) {
        console.error(`${tag} skill "${skill.name}" has NO MOTIONS (motions=${skill.motions?.length ?? 0})`);
        return null;
    }

    console.log(`${tag} "${animName}" → skill "${skill.name}" (match=${matchMethod}) motions=${skill.motions.length} numTrans=${skill.numTranslations} numRots=${skill.numRotations} cfpFile="${skill.animationFileName}"`);

    // DEEP COPY the skill so multiple bodies sharing the same animation
    // don't corrupt each other's translations/rotations arrays.
    // In the original C++, Skill owns its data and Practice just references it.
    // Multiple Practices can share one Skill safely because the Skill's data is
    // loaded once and never mutated. But our parseCFP mutates skill.translations
    // and skill.rotations — so we must either load CFP once and share, or deep copy.
    // We load CFP once into the shared skill, then each Practice references it.
    const cfpName = skill.animationFileName;
    if (cfpName && !cfpCache.has(cfpName) && (skill.numTranslations > 0 || skill.numRotations > 0)) {
        const bare = cfpName.toLowerCase();
        const prefixed = 'xskill-' + bare;
        const cfpFile = cfpIndex.get(bare) || cfpIndex.get(prefixed);
        if (cfpFile) {
            try {
                const resp = await fetch('data/' + cfpFile);
                if (resp.ok) {
                    cfpCache.set(cfpName, await resp.arrayBuffer());
                    console.log(`${tag} CFP loaded: "${cfpFile}" (${cfpCache.get(cfpName).byteLength} bytes)`);
                } else {
                    console.error(`${tag} CFP fetch FAILED: ${resp.status} for "${cfpFile}"`);
                }
            } catch (e) {
                console.error(`${tag} CFP fetch EXCEPTION for "${cfpFile}":`, e);
            }
        } else {
            console.error(`${tag} CFP file NOT FOUND in index for "${cfpName}" (tried bare="${bare}" prefixed="${prefixed}") — index has ${cfpIndex.size} entries`);
        }
    }

    // Parse CFP into the shared skill ONLY if not already parsed
    // (avoid re-parsing and re-allocating arrays for every body)
    const buffer = cfpCache.get(cfpName);
    if (buffer && (skill.translations.length === 0 && skill.rotations.length === 0)) {
        skill.translations = [];
        skill.rotations = [];
        parseCFP(buffer, skill);
        console.log(`${tag} CFP parsed: translations=${skill.translations.length} rotations=${skill.rotations.length}`);
    } else if (!buffer && (skill.numTranslations > 0 || skill.numRotations > 0)) {
        console.error(`${tag} NO CFP BUFFER for "${cfpName}" but skill expects ${skill.numTranslations} translations and ${skill.numRotations} rotations — animation will be BROKEN`);
    }

    if (skill.translations.length === 0 && skill.rotations.length === 0) {
        console.error(`${tag} skill "${skill.name}" has EMPTY animation data after CFP parse — practice will NOT be ready`);
    }

    const practice = new Practice(skill, skeleton);
    if (practice.ready) {
        practice.tick(0);
        updateTransforms(skeleton);
        console.log(`${tag} Practice READY: bindings=${practice.bindings.length}/${skill.motions.length} duration=${practice.duration}ms`);
    } else {
        console.error(`${tag} Practice NOT READY: bindings=${practice.bindings.length}/${skill.motions.length} trans=${skill.translations.length} rots=${skill.rotations.length}`);
    }
    return practice;
}

// Exit scene mode, return to solo viewing with first character
function exitScene() {
    activeScene = null;
    bodies = [];
    selectedActorIndex = -1;
    const actorGroup = $('actorGroup');
    if (actorGroup) actorGroup.style.display = 'none';
    updateActorEditingUI();
    // Silence any body voice chains
    if (audioCtx) {
        const now = audioCtx.currentTime;
        for (const chain of bodyVoices) chain.masterGain.gain.setTargetAtTime(0, now, 0.05);
    }
    // Select Solo in scene dropdown
    const sel = $('selScene');
    if (sel) {
        for (const opt of sel.options) {
            if (opt.value === '') { sel.value = ''; break; }
        }
    }
    // Load first character
    if (contentIndex?.characters?.length) {
        $('selCharacter').value = '0';
        applyCharacter(0);
    } else {
        applyDefaults();
    }
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

// Top physics Easter egg: spin fast enough and the character tilts,
// precesses like a gyroscope, drifts off-center, and wobbles back.
const top = {
    active: false,
    tilt: 0,            // current tilt angle (radians)
    tiltTarget: 0,      // desired tilt based on spin speed
    precessionAngle: 0, // gyroscopic precession rotation
    nutationPhase: 0,   // wobble oscillation phase
    nutationAmp: 0,     // wobble amplitude
    driftX: 0,          // off-center displacement
    driftZ: 0,
    driftVX: 0,         // drift velocity
    driftVZ: 0,
};

// CARTOON PHYSICS: Tamed Tazzie — still fun but less extreme
const TOP_SPIN_THRESHOLD = 1.0;   // needs a decent flick to trigger
const TOP_TILT_SCALE = 0.05;      // moderate tilt response (was 0.08)
const TOP_MAX_TILT = 1.0;         // ~57 degrees max lean (was 1.5 / 86 deg)
const TOP_PRECESSION_RATE = 0.04; // moderate gyroscopic orbit
const TOP_NUTATION_FREQ = 4.5;    // wobble frequency
const TOP_NUTATION_SCALE = 0.3;   // wobble amplitude (was 0.4)
const TOP_DRIFT_FORCE = 0.0008;   // moderate drift off-center (was 0.0015)
const TOP_GRAVITY = 0.003;        // stronger gravity — pulls back sooner (was 0.002)
const TOP_DRIFT_FRICTION = 0.97;  // more friction on drift (was 0.975)
const TOP_TILT_DECAY = 0.95;      // settles back a bit faster
const TOP_SETTLE_RATE = 0.10;     // still snappy into tilt

// Tick top physics for a given top-state object.
// All bodies share the same rotationVelocity input but each has independent state.
function tickTopFor(t) {
    const spinSpeed = Math.abs(rotationVelocity);

    if (spinSpeed > TOP_SPIN_THRESHOLD) {
        if (!t.active) {
            const launchAngle = Math.random() * Math.PI * 2;
            t.driftVX += Math.sin(launchAngle) * spinSpeed * 0.015;
            t.driftVZ += Math.cos(launchAngle) * spinSpeed * 0.015;
            t.nutationPhase = Math.random() * Math.PI * 2;
        }
        t.active = true;
        t.tiltTarget = Math.min(spinSpeed * TOP_TILT_SCALE, TOP_MAX_TILT);
    } else if (t.active) {
        t.tiltTarget *= TOP_TILT_DECAY;
        if (t.tiltTarget < 0.005 && Math.abs(t.driftX) < 0.01 && Math.abs(t.driftZ) < 0.01) {
            t.active = false;
            t.tilt = 0;
            t.driftX = 0; t.driftZ = 0;
            t.driftVX = 0; t.driftVZ = 0;
            t.nutationAmp = 0;
            return;
        }
    }

    if (!t.active) return;

    t.tilt += (t.tiltTarget - t.tilt) * TOP_SETTLE_RATE;
    t.precessionAngle += spinSpeed * TOP_PRECESSION_RATE;
    t.nutationPhase += TOP_NUTATION_FREQ * 0.05;
    t.nutationAmp += (t.tilt * TOP_NUTATION_SCALE - t.nutationAmp) * 0.1;

    const tiltDirX = Math.sin(t.precessionAngle);
    const tiltDirZ = Math.cos(t.precessionAngle);
    t.driftVX += tiltDirX * t.tilt * TOP_DRIFT_FORCE;
    t.driftVZ += tiltDirZ * t.tilt * TOP_DRIFT_FORCE;

    const dist = Math.sqrt(t.driftX * t.driftX + t.driftZ * t.driftZ);
    if (dist > 0.01) {
        const orbitalStrength = spinSpeed * 0.0004;
        const spinSign = rotationVelocity > 0 ? 1 : -1;
        t.driftVX += (-t.driftZ / dist) * orbitalStrength * spinSign;
        t.driftVZ += (t.driftX / dist) * orbitalStrength * spinSign;
    }

    const jitter = t.tilt * 0.0003;
    t.driftVX += (Math.random() - 0.5) * jitter;
    t.driftVZ += (Math.random() - 0.5) * jitter;

    const gravStrength = TOP_GRAVITY * (1 + dist * 0.3);
    t.driftVX -= t.driftX * gravStrength;
    t.driftVZ -= t.driftZ * gravStrength;

    t.driftVX *= TOP_DRIFT_FRICTION;
    t.driftVZ *= TOP_DRIFT_FRICTION;
    t.driftX += t.driftVX;
    t.driftZ += t.driftVZ;
}

// Solo-mode wrapper: ticks the global top state
function tickTop() { tickTopFor(top); }

// Tick all bodies' top physics (scene mode): same spin input, independent chaos
// Tick top physics. Selected bodies get full spin input.
// Unselected bodies still tick if active (so they can settle smoothly)
// but with zero spin speed so they decay to rest.
function tickAllBodiesTop() {
    if (bodies.length > 0) {
        const savedVelocity = rotationVelocity;
        for (let i = 0; i < bodies.length; i++) {
            const isSelected = (selectedActorIndex < 0 || i === selectedActorIndex);
            if (isSelected) {
                tickTopFor(bodies[i].top);
            } else if (bodies[i].top.active) {
                // Tick with zero velocity so it settles smoothly
                rotationVelocity = 0;
                tickTopFor(bodies[i].top);
                rotationVelocity = savedVelocity;
            }
        }
    } else {
        tickTopFor(top);
    }
}

// Apply top physics transform for a given top-state object
function applyTopTransformFor(v, t) {
    if (!t.active || !v) return v;

    const nutX = t.nutationAmp * Math.sin(t.nutationPhase);
    const nutZ = t.nutationAmp * Math.cos(t.nutationPhase * 0.7);
    const tiltX = t.tilt * Math.sin(t.precessionAngle) + nutX;
    const tiltZ = t.tilt * Math.cos(t.precessionAngle) + nutZ;

    const cy = cameraTarget.y;
    const relY = v.y - cy;

    const cosZ = Math.cos(tiltZ), sinZ = Math.sin(tiltZ);
    let y1 = relY * cosZ - v.x * sinZ;
    let x1 = relY * sinZ + v.x * cosZ;

    const cosX = Math.cos(tiltX), sinX = Math.sin(tiltX);
    let y2 = y1 * cosX - v.z * sinX;
    let z2 = y1 * sinX + v.z * cosX;

    return { x: x1 + t.driftX, y: y2 + cy, z: z2 + t.driftZ };
}

// Solo-mode wrapper
function applyTopTransform(v) { return applyTopTransformFor(v, top); }

// Top spin sound: procedural whirring via Web Audio oscillator.
// Pitch proportional to spin speed — you hear it wind up and slow down.
let audioCtx = null;
let spinOsc = null;
let spinGain = null;

// Simlish "weeeoooaaaaawww!" — formant synthesis with tilt-driven dipthong.
// Precession angle sweeps the vowel through ee->oo->aa->aw as the character
// leans and orbits. Tilt magnitude controls how far from neutral "ee" it goes.
// Vowel formant targets (F1, F2, F3 in Hz):
//   "ee" (wee):  270, 2300, 3000  — upright, tight
//   "oo" (ooh):  300,  870, 2240  — leaning, rounded
//   "aa" (aah):  730, 1090, 2440  — max lean, open mouth
//   "aw" (aww):  570,  840, 2410  — coming back around
let spinFormants = null; // solo mode voice chain
let bodyVoices = [];     // per-body voice chains for scene mode

// Create one complete voice chain: 2 oscillators + noise -> 3 bandpass formants -> gain -> panner -> destination
function createVoiceChain() {
    const glottal = audioCtx.createOscillator();
    glottal.type = 'sawtooth';
    glottal.frequency.value = 120;

    const glottal2 = audioCtx.createOscillator();
    glottal2.type = 'sawtooth';
    glottal2.frequency.value = 120;
    glottal2.detune.value = 5 + Math.random() * 10; // varied detune per voice

    const noise = audioCtx.createBufferSource();
    const noiseLen = audioCtx.sampleRate * 2;
    const noiseBuf = audioCtx.createBuffer(1, noiseLen, audioCtx.sampleRate);
    const noiseData = noiseBuf.getChannelData(0);
    for (let i = 0; i < noiseLen; i++) noiseData[i] = (Math.random() * 2 - 1) * 0.15;
    noise.buffer = noiseBuf;
    noise.loop = true;

    const srcGain = audioCtx.createGain();
    srcGain.gain.value = 1;
    const noiseGain = audioCtx.createGain();
    noiseGain.gain.value = 0.15;
    glottal.connect(srcGain);
    glottal2.connect(srcGain);
    noise.connect(noiseGain);
    noiseGain.connect(srcGain);

    const formantFreqs = [270, 2300, 3000];
    const formantQs = [5, 12, 8];
    const formantGains = [1.0, 0.6, 0.3];

    const filters = [];
    const masterGain = audioCtx.createGain();
    masterGain.gain.value = 0;
    const panner = audioCtx.createStereoPanner();
    panner.pan.value = 0;
    masterGain.connect(panner);
    panner.connect(audioCtx.destination);

    for (let i = 0; i < 3; i++) {
        const bp = audioCtx.createBiquadFilter();
        bp.type = 'bandpass';
        bp.frequency.value = formantFreqs[i];
        bp.Q.value = formantQs[i];
        const g = audioCtx.createGain();
        g.gain.value = formantGains[i];
        srcGain.connect(bp);
        bp.connect(g);
        g.connect(masterGain);
        filters.push(bp);
    }

    glottal.start();
    glottal2.start();
    noise.start();

    return { glottal, glottal2, filters, masterGain, noiseGain, panner };
}

function initSpinSound() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    // Create solo voice chain
    spinFormants = createVoiceChain();
    spinOsc = spinFormants.glottal;
    spinGain = spinFormants.masterGain;
}

// Create per-body voice chains for scene mode (call after audioCtx exists)
function ensureBodyVoices() {
    if (!audioCtx) return;
    // Match voice chains to bodies count
    while (bodyVoices.length < bodies.length) {
        bodyVoices.push(createVoiceChain());
    }
    // Silence extra chains
    const now = audioCtx.currentTime;
    for (let i = bodies.length; i < bodyVoices.length; i++) {
        bodyVoices[i].masterGain.gain.setTargetAtTime(0, now, 0.05);
    }
}

// Four vowel targets around the precession circle (F1, F2, F3)
const VOWELS = [
    [270, 2300, 3000],  // "ee" — 0 degrees (front, upright-ish)
    [300,  870, 2240],  // "oo" — 90 degrees (leaning right)
    [730, 1090, 2440],  // "aa" — 180 degrees (leaning back, mouth wide open)
    [570,  840, 2410],  // "aw" — 270 degrees (leaning left, rounding off)
];

function lerpVowel(angle, tiltAmount) {
    // angle: 0..2PI precession angle, tiltAmount: 0..1 normalized lean
    // At tiltAmount=0 we stay on pure "ee". At tiltAmount=1 we sweep full dipthong.
    const t = angle / (Math.PI * 2); // 0..1
    const idx = t * 4;
    const i0 = Math.floor(idx) % 4;
    const i1 = (i0 + 1) % 4;
    const frac = idx - Math.floor(idx);

    // Interpolate between adjacent vowels
    const swept = [
        VOWELS[i0][0] + (VOWELS[i1][0] - VOWELS[i0][0]) * frac,
        VOWELS[i0][1] + (VOWELS[i1][1] - VOWELS[i0][1]) * frac,
        VOWELS[i0][2] + (VOWELS[i1][2] - VOWELS[i0][2]) * frac,
    ];

    // Blend between neutral "ee" and the swept vowel based on tilt
    const ee = VOWELS[0];
    return [
        ee[0] + (swept[0] - ee[0]) * tiltAmount,
        ee[1] + (swept[1] - ee[1]) * tiltAmount,
        ee[2] + (swept[2] - ee[2]) * tiltAmount,
    ];
}

// Voice parameters for the current character.
// Voice parameters for the current character(s).
// Scene mode: blends all cast members' voices into a chord/chorus.
// Solo mode: reads the selected person's voice or auto-detects.
function getVoiceType() {
    // Scene mode: blend all bodies' voices
    if (bodies.length > 1) {
        let totalPitch = 0, totalRange = 0, totalFormant = 0, totalBreath = 0;
        let count = 0;
        for (const body of bodies) {
            const v = body.personData?.voice;
            if (v) {
                totalPitch += v.pitch || 100;
                totalRange += v.range || 50;
                totalFormant += v.formant || 1.0;
                totalBreath += v.breathiness || 0.15;
                count++;
            }
        }
        if (count > 0) {
            return {
                basePitch: totalPitch / count,
                pitchRange: totalRange / count,
                formantScale: totalFormant / count,
                breathiness: totalBreath / count,
                chorusSize: count, // used for extra detune
            };
        }
    }

    // Solo mode: try per-character JSON voice first
    const charSelect = $('selCharacter');
    if (charSelect && contentIndex?.characters) {
        const idx = parseInt(charSelect.value, 10);
        const char = contentIndex.characters[idx];
        if (char?.voice) {
            const v = char.voice;
            return {
                basePitch: v.pitch || 100,
                pitchRange: v.range || 50,
                formantScale: v.formant || 1.0,
                breathiness: v.breathiness || 0.15,
                chorusSize: 1,
            };
        }
    }

    // Auto-detect from body mesh name
    const body = ($('selBody')?.value || '').toLowerCase();
    const skel = ($('selSkeleton')?.value || '').toLowerCase();

    let isChild = skel.includes('child') || body.includes('chd') || body.includes('uc');
    let isFemale = body.includes('fa') || body.includes('fc');

    if (!body.includes('ma') && !body.includes('fa') && !body.includes('mc') && !body.includes('fc')) {
        if (filter.sex === 'F') isFemale = true;
        if (filter.age === 'C') isChild = true;
    }

    if (isChild && isFemale) return { basePitch: 240, pitchRange: 40, formantScale: 1.35, breathiness: 0.20, chorusSize: 1 };
    if (isChild)             return { basePitch: 220, pitchRange: 45, formantScale: 1.30, breathiness: 0.18, chorusSize: 1 };
    if (isFemale)            return { basePitch: 180, pitchRange: 50, formantScale: 1.15, breathiness: 0.18, chorusSize: 1 };
    return                          { basePitch: 50, pitchRange: 20, formantScale: 0.75, breathiness: 0.10, chorusSize: 1 };
}

// Drive a single voice chain from a body's voice params and top-physics state.
function updateVoiceChain(chain, voice, bTop, screenX, speed, now) {
    if (speed > 0.5) {
        const rawTilt = bTop.active ? Math.min(bTop.tilt / TOP_MAX_TILT, 1.0) : 0;
        const tiltAmount = Math.pow(rawTilt, 0.6);
        const precAngle = bTop.active ? ((bTop.precessionAngle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) : 0;

        // Pitch with per-body wobble from this body's own nutation
        const basePitch = voice.basePitch + Math.min(speed, 15) * voice.pitchRange;
        const wobbleDepth = tiltAmount * 60;
        const wobble1 = Math.sin(bTop.nutationPhase * 2.5) * wobbleDepth;
        const wobble2 = Math.sin(bTop.nutationPhase * 1.7 + 1.3) * wobbleDepth * 0.3;
        const pitch = basePitch + wobble1 + wobble2;
        chain.glottal.frequency.setTargetAtTime(pitch, now, 0.01);
        chain.glottal2.frequency.setTargetAtTime(pitch * 1.005, now, 0.01);

        // Breathiness
        if (chain.noiseGain) {
            const breathTilt = (voice.breathiness || 0.15) + tiltAmount * 0.5;
            chain.noiseGain.gain.setTargetAtTime(breathTilt, now, 0.02);
        }

        // Formants: this body's own dipthong sweep
        const speedShift = 1 + Math.min(speed, 12) * 0.02;
        const [f1, f2, f3] = lerpVowel(precAngle, tiltAmount);
        const fScale = speedShift * voice.formantScale;
        chain.filters[0].frequency.setTargetAtTime(f1 * fScale, now, 0.015);
        chain.filters[1].frequency.setTargetAtTime(f2 * fScale, now, 0.015);
        chain.filters[2].frequency.setTargetAtTime(f3 * fScale, now, 0.015);

        const qScale = 1 - tiltAmount * 0.6;
        chain.filters[0].Q.setTargetAtTime(5 * qScale, now, 0.01);
        chain.filters[1].Q.setTargetAtTime(12 * qScale, now, 0.01);
        chain.filters[2].Q.setTargetAtTime(8 * qScale, now, 0.01);

        // Volume: scale down per body so the chorus doesn't clip
        const numVoices = Math.max(bodies.length, 1);
        const perVoiceVol = Math.min(speed / 7, 0.25) / Math.sqrt(numVoices);
        const tiltBoost = 1 + tiltAmount * 1.2;
        chain.masterGain.gain.setTargetAtTime(perVoiceVol * tiltBoost, now, 0.02);

        // Stereo pan from screen X position
        if (chain.panner) {
            const pan = Math.max(-1, Math.min(1, screenX / 3));
            chain.panner.pan.setTargetAtTime(pan, now, 0.03);
        }
    } else {
        chain.masterGain.gain.setTargetAtTime(0, now, 0.1);
    }
}

function updateSpinSound() {
    if (!audioCtx) return;

    const speed = Math.abs(rotationVelocity);
    const now = audioCtx.currentTime;

    if (bodies.length > 0) {
        // Scene mode: each body gets its own voice chain
        ensureBodyVoices();
        // Silence the solo chain
        if (spinFormants) spinFormants.masterGain.gain.setTargetAtTime(0, now, 0.05);

        for (let i = 0; i < bodies.length; i++) {
            const b = bodies[i];
            const chain = bodyVoices[i];
            if (!chain) continue;

            // Only voice the selected actor (or all in All mode)
            const isActive = (selectedActorIndex < 0 || i === selectedActorIndex);
            if (!isActive) {
                chain.masterGain.gain.setTargetAtTime(0, now, 0.05);
                continue;
            }

            // Get this body's voice params from their character data
            const v = b.personData?.voice;
            const voice = v ? {
                basePitch: v.pitch || 50, pitchRange: v.range || 20,
                formantScale: v.formant || 0.85, breathiness: v.breathiness || 0.15,
            } : { basePitch: 50, pitchRange: 20, formantScale: 0.75, breathiness: 0.10 };

            // Screen X: body position projected for pan
            const driftX = b.top.active ? b.top.driftX : 0;
            const screenX = b.x + driftX;

            updateVoiceChain(chain, voice, b.top, screenX, speed, now);
        }
    } else if (spinFormants) {
        // Solo mode: single voice chain
        const voice = getVoiceType();
        const driftX = top.active ? top.driftX : 0;
        updateVoiceChain(spinFormants, voice, top, driftX, speed, now);
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
        cameraTarget = { x: 0, y: 2.5, z: 0 };
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
                const bare = cfpName.toLowerCase();
                const cfpFile = cfpIndex.get(bare) || cfpIndex.get('xskill-' + bare);
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
    const charIdx = parseInt($('selCharacter').value);
    const charName = contentIndex?.characters?.[charIdx]?.name;
    const animLabel = animName || 'idle';
    statusEl.textContent = charName
        ? `${charName} | ${animLabel}`
        : `${skelName} (${activeSkeleton.length} bones) | ${animLabel}`;
    renderFrame();
}

function renderFrame() {
    if (!renderer) return;

    // Motion blur: when spinning fast with top physics active, fade previous frame
    const spinSpeed = Math.abs(rotationVelocity);
    const anyActive = bodies.length > 0 ? bodies.some(b => b.top.active) : top.active;
    if (anyActive && spinSpeed > 1.0) {
        // Alpha = how much background to overlay. Lower = longer trails.
        // Scale with spin speed: fast spin = long trails, slow = short trails
        const trailLength = Math.max(0.08, 0.4 - spinSpeed * 0.02);
        renderer.fadeScreen(0.1, 0.1, 0.15, trailLength);
    } else {
        renderer.clear();
    }

    const zoom = parseFloat($('zoom').value) / 10;
    const rotYDeg = parseFloat($('rotY').value);
    const rotY = rotYDeg * Math.PI / 180;
    const rotX = parseFloat($('rotX').value) * Math.PI / 180;
    const dist = zoom;

    // Scene mode: camera stays fixed, each body spins in place.
    // Solo mode: camera orbits around the character (original behavior).
    const sceneMode = bodies.length > 0;
    const cosX = Math.cos(rotX);
    let eyeX, eyeY, eyeZ;
    if (sceneMode) {
        // Fixed camera looking at the group from a consistent angle
        eyeX = Math.sin(0) * cosX * dist; // no camera rotation
        eyeY = cameraTarget.y + Math.sin(rotX) * dist;
        eyeZ = Math.cos(0) * cosX * dist;
    } else {
        // Solo: camera orbits around character
        eyeX = Math.sin(rotY) * cosX * dist;
        eyeY = cameraTarget.y + Math.sin(rotX) * dist;
        eyeZ = Math.cos(rotY) * cosX * dist;
    }

    renderer.setCamera(50, canvas.width / canvas.height, 0.01, 100,
                       eyeX, eyeY, eyeZ,
                       cameraTarget.x, cameraTarget.y, cameraTarget.z);

    // Render all bodies
    const bodiesToRender = sceneMode ? bodies : [{ skeleton: activeSkeleton, meshes: activeMeshes, top, x: 0, z: 0, direction: 0 }];

    for (let bi = 0; bi < bodiesToRender.length; bi++) {
        const body = bodiesToRender[bi];
        const bTop = body.top || top;
        // Scene mode: each body has a base direction + per-body spinOffset + global rotY.
        // All mode (-1): everyone gets global rotY.
        // Selected actor: only that actor gets global rotY; others keep base + their own spinOffset.
        let spinDeg = 0;
        if (sceneMode) {
            const baseDir = (body.direction || 0) + (body.spinOffset || 0);
            if (selectedActorIndex < 0 || bi === selectedActorIndex) {
                spinDeg = baseDir + rotYDeg;
            } else {
                spinDeg = baseDir;
            }
        }
        const bodyDir = spinDeg * Math.PI / 180;
        const cosD = Math.cos(bodyDir);
        const sinD = Math.sin(bodyDir);

        if (body.meshes.length === 0 && sceneMode && !_renderWarnedBodies.has(bi)) {
            _renderWarnedBodies.add(bi);
            console.error(`[renderFrame] BODY[${bi}] "${body.personData?.name || '?'}" has 0 meshes — nothing to draw`);
        }

        for (const { mesh, boneMap, texture } of body.meshes) {
            try {
                let verts, norms;
                if (body.skeleton) {
                    const deformed = deformMesh(mesh, body.skeleton, boneMap);
                    verts = deformed.vertices;
                    norms = deformed.normals;
                } else {
                    verts = mesh.vertices;
                    norms = mesh.normals;
                }

                // Per-body top physics tilt + drift
                if (bTop.active) {
                    verts = verts.map(v => applyTopTransformFor(v, bTop));
                    norms = norms.map(v => applyTopTransformFor(v, bTop));
                }

                // World position offset + facing direction
                if (body.x !== 0 || body.z !== 0 || bodyDir !== 0) {
                    verts = verts.map(v => {
                        if (!v) return v;
                        // Rotate around Y by direction, then translate
                        const rx = v.x * cosD - v.z * sinD;
                        const rz = v.x * sinD + v.z * cosD;
                        return { x: rx + body.x, y: v.y, z: rz + body.z };
                    });
                    if (bodyDir !== 0) {
                        norms = norms.map(v => {
                            if (!v) return v;
                            return { x: v.x * cosD - v.z * sinD, y: v.y, z: v.x * sinD + v.z * cosD };
                        });
                    }
                }

                renderer.drawMesh(mesh, verts, norms, texture || null);
            } catch (e) {
                if (!_renderWarnedBodies.has(`${bi}-${mesh.name}`)) {
                    _renderWarnedBodies.add(`${bi}-${mesh.name}`);
                    console.error(`[renderFrame] BODY[${bi}] mesh "${mesh.name}" render EXCEPTION:`, e);
                }
            }
        }
    }

    // Plumb bob: floating green diamond above actors' heads.
    // All mode: plumb bob over every actor. Selected mode: just the one.
    if (sceneMode) {
        const now = performance.now();
        const plumbRot = now * 0.001 * Math.PI; // half rev per second
        const bob = Math.sin(now * 0.002) * 0.12;

        const drawPlumbBobForBody = (bi, body) => {
            if (!body.skeleton) return;
            const headBone = body.skeleton.find(b => b.name === 'HEAD');
            if (!headBone) return;

            const bTop = body.top || top;
            const baseDir = (body.direction || 0) + (body.spinOffset || 0);
            const sd = (selectedActorIndex < 0 || bi === selectedActorIndex) ? baseDir + rotYDeg : baseDir;
            const bodyDir = sd * Math.PI / 180;
            const cosD = Math.cos(bodyDir);
            const sinD = Math.sin(bodyDir);

            let hx = headBone.worldPosition.x;
            let hy = headBone.worldPosition.y;
            let hz = headBone.worldPosition.z;

            if (bTop.active) {
                const tilted = applyTopTransformFor({ x: hx, y: hy, z: hz }, bTop);
                hx = tilted.x; hy = tilted.y; hz = tilted.z;
            }

            const rx = hx * cosD - hz * sinD;
            const rz = hx * sinD + hz * cosD;
            const wx = rx + body.x;
            const wy = hy + 1.5;
            const wz = rz + body.z;

            renderer.drawDiamond(wx, wy + bob, wz, 0.18, plumbRot, 0.2, 1.0, 0.2, 0.9);
        };

        if (selectedActorIndex >= 0 && selectedActorIndex < bodiesToRender.length) {
            // One actor selected: plumb bob over just them
            drawPlumbBobForBody(selectedActorIndex, bodiesToRender[selectedActorIndex]);
        } else if (selectedActorIndex < 0) {
            // All mode: plumb bob over everyone
            for (let bi = 0; bi < bodiesToRender.length; bi++) {
                drawPlumbBobForBody(bi, bodiesToRender[bi]);
            }
        }
    }
}
const _renderWarnedBodies = new Set();

// Animation loop: ticks Practice animation + applies rotation momentum.
let _animDiagLogged = false;
function animationLoop(timestamp) {
    let needsRender = false;

    // Tick animations for all bodies (scene mode) or just the primary (solo mode)
    if (!paused) {
        if (lastFrameTime === 0) lastFrameTime = timestamp;
        const dt = timestamp - lastFrameTime;
        lastFrameTime = timestamp;
        const speedScale = parseFloat($('speed').value) / 100;
        animationTime += dt * speedScale;

        if (bodies.length > 0) {
            // One-shot diagnostic: log every body's animation state on first tick
            if (!_animDiagLogged) {
                _animDiagLogged = true;
                console.log(`[animLoop] FIRST TICK: ${bodies.length} bodies, animationTime=${animationTime.toFixed(1)}`);
                for (let i = 0; i < bodies.length; i++) {
                    const b = bodies[i];
                    const name = b.personData?.name || '?';
                    const hasPractice = !!b.practice;
                    const ready = b.practice?.ready ?? false;
                    const hasSkel = !!b.skeleton;
                    const meshCount = b.meshes.length;
                    if (!hasPractice || !ready || !hasSkel || meshCount === 0) {
                        console.error(`[animLoop] BODY[${i}] "${name}" WILL NOT ANIMATE: practice=${hasPractice} ready=${ready} skeleton=${hasSkel} meshes=${meshCount}`);
                    }
                }
            }

            // Scene mode: tick every body's own practice
            for (let i = 0; i < bodies.length; i++) {
                const body = bodies[i];
                if (body.practice?.ready && body.skeleton) {
                    try {
                        body.practice.tick(animationTime);
                        updateTransforms(body.skeleton);
                        needsRender = true;
                    } catch (e) {
                        console.error(`[animLoop] BODY[${i}] "${body.personData?.name}" tick EXCEPTION:`, e);
                    }
                }
            }
        } else if (activePractice?.ready && activeSkeleton) {
            // Solo mode
            try {
                activePractice.tick(animationTime);
                updateTransforms(activeSkeleton);
                needsRender = true;
            } catch (e) {
                console.error(`[animLoop] solo tick EXCEPTION:`, e);
            }
        }
    }

    // Spin momentum: when a specific actor is selected, spin only them.
    // When All is selected, spin the global rotY slider (spins everyone).
    if (!isDragging && Math.abs(rotationVelocity) > 0.001) {
        if (bodies.length > 0 && selectedActorIndex >= 0 && selectedActorIndex < bodies.length) {
            // Per-actor spin
            bodies[selectedActorIndex].spinOffset += rotationVelocity;
        } else {
            // Global spin (All mode or solo)
            const rotSlider = $('rotY');
            let val = parseFloat(rotSlider.value) + rotationVelocity;
            if (val > 360) val -= 360;
            if (val < 0) val += 360;
            rotSlider.value = val;
        }
        rotationVelocity *= FRICTION;
        needsRender = true;
    }

    // Per-body independent spin momentum (from space-while-spinning)
    for (const b of bodies) {
        if (Math.abs(b.spinVelocity) > 0.001) {
            b.spinOffset += b.spinVelocity;
            b.spinVelocity *= FRICTION;
            needsRender = true;
        }
    }

    // Top physics: all bodies respond to the same spin, each with independent state
    tickAllBodiesTop();
    const anyTopActive = bodies.length > 0
        ? bodies.some(b => b.top.active)
        : top.active;
    if (anyTopActive) needsRender = true;

    // Arrow keys: smooth zoom (up/down) and ramp spin (left/right)
    if (_keysHeld.up || _keysHeld.down) {
        const zoomSlider = $('zoom');
        const zoomDelta = (_keysHeld.down ? 1.5 : -1.5); // per frame
        let val = parseFloat(zoomSlider.value) + zoomDelta;
        val = Math.max(15, Math.min(400, val));
        zoomSlider.value = val;
        needsRender = true;
    }
    if (_keysHeld.left || _keysHeld.right) {
        // Ramp up spin speed the longer the key is held (gentle acceleration)
        const now = performance.now();
        const dir = _keysHeld.left ? 1 : -1;
        const holdTime = _keysHeld.left
            ? (now - _keysHeld.leftStart) / 1000
            : (now - _keysHeld.rightStart) / 1000;
        // Ramp: starts at 0.5 deg/frame, maxes at ~16 deg/frame after 3 seconds
        const speed = 0.5 + Math.min(holdTime * 5.0, 16.0);
        rotationVelocity = dir * speed;
        needsRender = true;
    }

    // Spin sound: pitch tracks velocity, fades as they slow down
    updateSpinSound();

    if (needsRender) renderFrame();

    requestAnimationFrame(animationLoop);
}

// Pick actor by screen position: project each body's head position to screen,
// find the nearest one within a threshold radius.
function pickActorAtScreen(screenX, screenY) {
    if (bodies.length === 0 || !renderer) return -1;

    const rect = canvas.getBoundingClientRect();
    const mx = screenX - rect.left;
    const my = screenY - rect.top;

    const zoom = parseFloat($('zoom').value) / 10;
    const rotYDeg = parseFloat($('rotY').value);
    const rotY = rotYDeg * Math.PI / 180;
    const rotX = parseFloat($('rotX').value) * Math.PI / 180;
    const dist = zoom;
    const fov = 50;
    const aspect = canvas.width / canvas.height;

    const sceneMode = bodies.length > 0;
    const cosX = Math.cos(rotX);
    let eyeX, eyeY, eyeZ;
    if (sceneMode) {
        eyeX = 0;
        eyeY = cameraTarget.y + Math.sin(rotX) * dist;
        eyeZ = cosX * dist;
    } else {
        eyeX = Math.sin(rotY) * cosX * dist;
        eyeY = cameraTarget.y + Math.sin(rotX) * dist;
        eyeZ = Math.cos(rotY) * cosX * dist;
    }

    // Build view + projection matrices (same as renderer.setCamera)
    const proj = perspectiveMatrix(fov, aspect, 0.01, 100);
    const view = lookAtMatrix(eyeX, eyeY, eyeZ, cameraTarget.x, cameraTarget.y, cameraTarget.z, 0, 1, 0);

    let bestIdx = -1;
    let bestDist = 60; // max screen-pixel distance threshold

    for (let i = 0; i < bodies.length; i++) {
        const b = bodies[i];
        if (!b.skeleton) continue;

        // Get approximate center: body world position at waist height
        // Match render logic: base + spinOffset + global rotY (if selected or All)
        const baseDir = (b.direction || 0) + (b.spinOffset || 0);
        const spinDeg = (selectedActorIndex < 0 || i === selectedActorIndex) ? baseDir + rotYDeg : baseDir;
        const bodyDir = spinDeg * Math.PI / 180;

        // Use SPINE1 bone if available, else just body position
        const spine = b.skeleton.find(bn => bn.name === 'SPINE1') || b.skeleton.find(bn => bn.name === 'PELVIS');
        let wx = b.x, wy = 2.5, wz = b.z;
        if (spine) {
            const cosD = Math.cos(bodyDir);
            const sinD = Math.sin(bodyDir);
            const sx = spine.worldPosition.x;
            const sz = spine.worldPosition.z;
            wx = sx * cosD - sz * sinD + b.x;
            wy = spine.worldPosition.y;
            wz = sx * sinD + sz * cosD + b.z;
        }

        // Project world point to screen
        const sp = projectToScreen(wx, wy, wz, view, proj, canvas.width, canvas.height);
        if (!sp) continue;

        const dx = sp.x - mx;
        const dy = sp.y - my;
        const screenDist = Math.sqrt(dx * dx + dy * dy);

        if (screenDist < bestDist) {
            bestDist = screenDist;
            bestIdx = i;
        }
    }

    return bestIdx;
}

// Project a world point to screen pixel coordinates
function projectToScreen(wx, wy, wz, view, proj, width, height) {
    // view * point
    const vx = view[0]*wx + view[4]*wy + view[8]*wz + view[12];
    const vy = view[1]*wx + view[5]*wy + view[9]*wz + view[13];
    const vz = view[2]*wx + view[6]*wy + view[10]*wz + view[14];
    const vw = view[3]*wx + view[7]*wy + view[11]*wz + view[15];
    // proj * view_point
    const px = proj[0]*vx + proj[4]*vy + proj[8]*vz + proj[12]*vw;
    const py = proj[1]*vx + proj[5]*vy + proj[9]*vz + proj[13]*vw;
    const pw = proj[3]*vx + proj[7]*vy + proj[11]*vz + proj[15]*vw;
    if (Math.abs(pw) < 0.001) return null; // behind camera
    // NDC
    const ndcX = px / pw;
    const ndcY = py / pw;
    // Screen
    return {
        x: (ndcX * 0.5 + 0.5) * width,
        y: (1.0 - (ndcY * 0.5 + 0.5)) * height,
    };
}

// Minimal perspective matrix (matches renderer.ts)
function perspectiveMatrix(fov, aspect, near, far) {
    const f = 1.0 / Math.tan(fov * Math.PI / 360);
    const nf = 1 / (near - far);
    return new Float32Array([
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) * nf, -1,
        0, 0, 2 * far * near * nf, 0,
    ]);
}

// Minimal lookAt matrix (matches renderer.ts)
function lookAtMatrix(ex, ey, ez, cx, cy, cz, ux, uy, uz) {
    let fx = cx - ex, fy = cy - ey, fz = cz - ez;
    let fl = Math.sqrt(fx*fx + fy*fy + fz*fz);
    fx /= fl; fy /= fl; fz /= fl;
    let sx = fy*uz - fz*uy, sy = fz*ux - fx*uz, sz = fx*uy - fy*ux;
    let sl = Math.sqrt(sx*sx + sy*sy + sz*sz);
    sx /= sl; sy /= sl; sz /= sl;
    let uux = sy*fz - sz*fy, uuy = sz*fx - sx*fz, uuz = sx*fy - sy*fx;
    return new Float32Array([
        sx, uux, -fx, 0,
        sy, uuy, -fy, 0,
        sz, uuz, -fz, 0,
        -(sx*ex + sy*ey + sz*ez),
        -(uux*ex + uuy*ey + uuz*ez),
        fx*ex + fy*ey + fz*ez, 1,
    ]);
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
        initSpinSound(); // init audio on first gesture (browser policy)

        // Click-to-pick: immediately select actor on mousedown (left button only)
        if (e.button === 0 && bodies.length > 0) {
            const picked = pickActorAtScreen(e.clientX, e.clientY);
            if (picked >= 0) {
                selectActor(picked);
            } else if (bodies.length > 1) {
                selectActor(-1); // click background = All
            }
        }

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
            if (bodies.length > 0 && selectedActorIndex >= 0 && selectedActorIndex < bodies.length) {
                // Per-actor spin
                bodies[selectedActorIndex].spinOffset -= dx * 0.5;
            } else {
                // Global spin
                const rotSlider = $('rotY');
                let rotVal = parseFloat(rotSlider.value) - dx * 0.5;
                if (rotVal > 360) rotVal -= 360;
                if (rotVal < 0) rotVal += 360;
                rotSlider.value = rotVal;
            }

            const zoomSlider = $('zoom');
            let zoomVal = parseFloat(zoomSlider.value) + dy * 0.25;
            zoomVal = Math.max(15, Math.min(400, zoomVal));
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
        const instantVelocity = dragButton === 0 ? (-dx * 0.3) / (dt / 16.67) : 0;
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
        }
        // Click without drag: don't kill rotationVelocity — let it decay naturally.
        // Pick already happened on mousedown.
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
        val = Math.max(15, Math.min(400, val));
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
        val = Math.max(15, Math.min(400, val));
        zoomSlider.value = val;
        renderFrame();
    });

    canvas.style.cursor = 'grab';
}

// Select an actor by index. -1 = All.
function selectActor(idx) {
    if (idx < -1 || idx >= bodies.length) return;
    const prevIdx = selectedActorIndex;
    selectedActorIndex = idx;
    const actorSel = $('selActor');
    if (actorSel) actorSel.value = String(idx);

    // Deselected bodies: set tiltTarget to 0 so they settle smoothly
    // (tickTopFor will decay them naturally via TOP_TILT_DECAY)
    if (prevIdx !== idx) {
        for (let i = 0; i < bodies.length; i++) {
            const shouldBeActive = (idx < 0 || i === idx);
            if (!shouldBeActive && bodies[i].top.active) {
                bodies[i].top.tiltTarget = 0;
            }
        }
    }
    if (idx >= 0) {
        const body = bodies[idx];
        // Sync Character dropdown to this actor's character
        if (body?.personData && contentIndex?.characters) {
            const charIdx = contentIndex.characters.findIndex(c => c.name === body.personData.name);
            if (charIdx >= 0) $('selCharacter').value = String(charIdx);
        }
        // Sync Animation dropdown to this actor's current skill
        if (body?.practice?.skill?.name) {
            setSelectValue('selAnim', body.practice.skill.name);
        }
    }
    updateActorEditingUI();
}

// Enable/disable actor editing controls based on whether a specific actor is selected.
// When disabled (All mode), show neutral placeholder text in dropdowns.
function updateActorEditingUI() {
    const inScene = !!activeScene;
    const hasActor = inScene && selectedActorIndex >= 0;
    const disabled = !hasActor && inScene;

    // Character controls
    const charSel = $('selCharacter');
    const charPrev = $('btnCharacterPrev');
    const charNext = $('btnCharacterNext');
    if (charSel) {
        charSel.disabled = disabled;
        if (disabled) charSel.value = '';
    }
    if (charPrev) charPrev.disabled = disabled;
    if (charNext) charNext.disabled = disabled;

    // Animation controls
    const animSel = $('selAnim');
    const animPrev = $('btnAnimPrev');
    const animNext = $('btnAnimNext');
    if (animSel) {
        animSel.disabled = disabled;
        if (disabled) animSel.value = '';
    }
    if (animPrev) animPrev.disabled = disabled;
    if (animNext) animNext.disabled = disabled;
}

// Step through character presets
function stepCharacter(direction) {
    if (!contentIndex?.characters?.length) return;
    const sel = $('selCharacter');
    let idx = parseInt(sel.value);
    if (isNaN(idx)) idx = direction > 0 ? 0 : contentIndex.characters.length - 1;
    else idx += direction;
    if (idx < 0) idx = contentIndex.characters.length - 1;
    if (idx >= contentIndex.characters.length) idx = 0;
    sel.value = String(idx);
    if (activeScene && selectedActorIndex >= 0) {
        applyCharacterToActor(idx, selectedActorIndex);
    } else {
        exitScene();
        applyCharacter(idx);
    }
}

// Apply a character preset to a specific actor in the current scene.
// Rebuilds that actor's body (skeleton, meshes, textures, animation) in place.
async function applyCharacterToActor(charIndex, actorIndex) {
    if (!contentIndex?.characters?.[charIndex]) return;
    if (actorIndex < 0 || actorIndex >= bodies.length) return;
    const char = contentIndex.characters[charIndex];
    const body = bodies[actorIndex];

    // Build everything into temporaries — don't touch the live body until ready.
    // This prevents the animation loop from rendering a half-built rest-pose frame.
    let newSkeleton = null;
    const skelName = char.skeleton || 'adult';
    const skelFile = skelName.includes('.cmx') ? skelName : skelName + '-skeleton.cmx';
    try {
        let skelText = _skelCache[skelFile];
        if (!skelText) {
            const skelResp = await fetch('data/' + skelFile);
            if (skelResp.ok) skelText = await skelResp.text();
        }
        if (skelText) {
            const skelData = parseCMX(skelText);
            if (skelData.skeletons?.length) {
                newSkeleton = buildSkeleton(skelData.skeletons[0]);
                updateTransforms(newSkeleton);
            }
        }
    } catch (e) { console.error(`[applyCharacterToActor] skeleton error:`, e); }
    if (!newSkeleton) return;

    const newMeshes = [];
    const meshParts = [
        { name: char.body,      tex: char.bodyTexture },
        { name: char.head,      tex: char.headTexture },
        { name: char.leftHand,  tex: char.handTexture },
        { name: char.rightHand, tex: char.handTexture },
    ];
    for (const part of meshParts) {
        if (!part.name) continue;
        const meshKey = part.name;
        if (!content.meshes[meshKey]) {
            const lowerKey = meshKey.toLowerCase();
            const ciMatch = Object.keys(content.meshes).find(k => k.toLowerCase() === lowerKey);
            if (ciMatch) content.meshes[meshKey] = content.meshes[ciMatch];
        }
        const mesh = content.meshes[meshKey];
        if (!mesh) continue;
        const boneMap = new Map();
        for (const bone of newSkeleton) boneMap.set(bone.name, bone);
        const texture = part.tex ? await getTexture(part.tex) : null;
        newMeshes.push({ mesh, boneMap, texture });
    }

    let newPractice = null;
    const animName = char.animation;
    if (animName) {
        newPractice = await loadAnimationForBody(animName, newSkeleton, `actor "${body.actorName}"`);
    }

    // Apply first animation frame before making visible
    if (newPractice?.ready) {
        newPractice.tick(animationTime > 0 ? animationTime : 1);
        updateTransforms(newSkeleton);
    }

    // Atomic swap: animation loop only ever sees a fully-posed character
    body.personData = char;
    body.skeleton = newSkeleton;
    body.meshes = newMeshes;
    body.practice = newPractice;

    renderFrame();
}

let _savedSpeed = 100; // speed before pause, for 0 key toggle

function togglePause() {
    if (paused) {
        paused = false;
        $('speed').value = _savedSpeed;
        lastFrameTime = 0;
    } else {
        _savedSpeed = parseFloat($('speed').value);
        paused = true;
    }
    const btn = $('btnPause');
    if (btn) {
        btn.textContent = paused ? 'Play' : 'Pause';
        btn.classList.toggle('active', paused);
    }
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
    if (activeScene && selectedActorIndex >= 0) {
        applyAnimationToActor(sel.value, selectedActorIndex);
    } else {
        updateScene();
    }
}

// Change a specific actor's animation in the current scene
async function applyAnimationToActor(animName, actorIndex) {
    if (actorIndex < 0 || actorIndex >= bodies.length) return;
    if (!animName) return;
    const body = bodies[actorIndex];
    if (!body.skeleton) return;
    // Build practice into temporary, tick first frame, then swap
    const newPractice = await loadAnimationForBody(animName, body.skeleton, `actor "${body.actorName}"`);
    if (newPractice?.ready) {
        newPractice.tick(animationTime > 0 ? animationTime : 1);
        updateTransforms(body.skeleton);
    }
    body.practice = newPractice;
    renderFrame();
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
    // Selection changes trigger scene rebuild (solo mode details)
    for (const id of ['selSkeleton', 'selBody', 'selHead', 'selLeftHand', 'selRightHand',
                       'selBodyTex', 'selHeadTex', 'selHandTex']) {
        $(id).addEventListener('change', updateScene);
    }
    // Animation dropdown: in scene mode with selected actor, change that actor's anim
    $('selAnim').addEventListener('change', () => {
        if (activeScene && selectedActorIndex >= 0) {
            applyAnimationToActor($('selAnim').value, selectedActorIndex);
        } else {
            updateScene();
        }
    });

    // Camera controls trigger immediate re-render
    for (const id of ['rotY', 'rotX', 'zoom', 'speed']) {
        $(id).addEventListener('input', renderFrame);
    }

    // Distance preset buttons
    document.querySelectorAll('.dist-btn').forEach(btn => {
        btn.addEventListener('click', () => setDistance(btn.dataset.dist));
    });

    // Character prev/next buttons and dropdown
    const btnCharacterPrev = $('btnCharacterPrev');
    const btnCharacterNext = $('btnCharacterNext');
    if (btnCharacterPrev) btnCharacterPrev.addEventListener('click', () => stepCharacter(-1));
    if (btnCharacterNext) btnCharacterNext.addEventListener('click', () => stepCharacter(1));
    $('selCharacter').addEventListener('change', () => {
        const idx = parseInt($('selCharacter').value);
        if (isNaN(idx)) return;
        if (activeScene && selectedActorIndex >= 0) {
            applyCharacterToActor(idx, selectedActorIndex);
        } else {
            exitScene();
            applyCharacter(idx);
        }
    });

    // Actor prev/next buttons and dropdown (scene mode only)
    function stepActor(dir) {
        if (bodies.length === 0) return;
        // Range: -1 (All) through bodies.length-1
        // But if only 1 body, skip All entirely
        const minIdx = bodies.length > 1 ? -1 : 0;
        let idx = selectedActorIndex + dir;
        if (idx < minIdx) idx = bodies.length - 1;
        if (idx >= bodies.length) idx = minIdx;
        selectActor(idx);
    }
    // selectActor is module-level (defined above setupEventListeners)
    const btnActorPrev = $('btnActorPrev');
    const btnActorNext = $('btnActorNext');
    if (btnActorPrev) btnActorPrev.addEventListener('click', () => stepActor(-1));
    if (btnActorNext) btnActorNext.addEventListener('click', () => stepActor(1));
    const selActor = $('selActor');
    if (selActor) selActor.addEventListener('change', () => {
        const idx = parseInt(selActor.value);
        if (!isNaN(idx)) selectActor(idx);
    });

    // Scene prev/next/select
    function stepScene(dir) {
        const sel = $('selScene');
        if (!sel || sel.options.length <= 1) return;
        // Navigate through all options (scenes + Solo at end)
        let selIdx = sel.selectedIndex + dir;
        if (selIdx < 0) selIdx = sel.options.length - 1;
        if (selIdx >= sel.options.length) selIdx = 0;
        sel.selectedIndex = selIdx;
        const val = sel.value;
        if (val === '') { exitScene(); return; }
        loadScene(parseInt(val));
    }
    const btnScenePrev = $('btnScenePrev');
    const btnSceneNext = $('btnSceneNext');
    if (btnScenePrev) btnScenePrev.addEventListener('click', () => stepScene(-1));
    if (btnSceneNext) btnSceneNext.addEventListener('click', () => stepScene(1));
    const selScene = $('selScene');
    if (selScene) selScene.addEventListener('change', () => {
        const idx = parseInt(selScene.value);
        if (isNaN(idx) || selScene.value === '') { exitScene(); return; }
        loadScene(idx);
    });

    // Animation prev/next buttons
    const btnPrev = $('btnAnimPrev');
    const btnNext = $('btnAnimNext');
    if (btnPrev) btnPrev.addEventListener('click', () => stepAnimation(-1));
    if (btnNext) btnNext.addEventListener('click', () => stepAnimation(1));

    // Pause/resume button
    const btnPause = $('btnPause');
    if (btnPause) btnPause.addEventListener('click', togglePause);

    // Keyboard controls:
    // Space = cycle between All and last selected actor
    // 0 = pause, 1/2/3/4 = speed (normal/fast/faster/fastest)
    // Up/Down = smooth zoom, Left/Right = ramp spin velocity
    // Keyboard events on window so they work regardless of focus.
    // Skip when a <select> or <input> has focus (user is picking from dropdown).
    const _isInputFocused = () => {
        const tag = document.activeElement?.tagName;
        return tag === 'SELECT' || tag === 'INPUT' || tag === 'TEXTAREA';
    };

    // Auto-focus canvas on mouse enter so wheel zoom works immediately
    canvas.addEventListener('mouseenter', () => canvas.focus());
    canvas.tabIndex = 0;

    window.addEventListener('keydown', e => {
        if (_isInputFocused()) return;
        if (e.key === ' ') {
            // Space: next actor (same as Next button).
            // If spinning, transfer momentum to per-body spin velocity.
            if (bodies.length > 0) {
                if (Math.abs(rotationVelocity) > 0.01 && selectedActorIndex >= 0 && selectedActorIndex < bodies.length) {
                    bodies[selectedActorIndex].spinVelocity = rotationVelocity;
                    rotationVelocity = 0;
                }
                const minIdx = bodies.length > 1 ? -1 : 0;
                let idx = selectedActorIndex + 1;
                if (idx >= bodies.length) idx = minIdx;
                selectActor(idx);
            }
            e.preventDefault();
        }
        // 0 = toggle pause (remembers previous speed)
        // 1-9 = speed: 1=slowest(10%), 5=normal(100%), 9=fastest(500%)
        if (e.key === '0') {
            if (paused) {
                paused = false;
                $('speed').value = _savedSpeed;
                lastFrameTime = 0;
                $('btnPause').textContent = 'Pause';
                $('btnPause').classList.remove('active');
            } else {
                _savedSpeed = parseFloat($('speed').value);
                paused = true;
                $('btnPause').textContent = 'Play';
                $('btnPause').classList.add('active');
            }
            e.preventDefault();
        }
        const speedKeys = { '1': 10, '2': 25, '3': 50, '4': 75, '5': 100, '6': 150, '7': 250, '8': 375, '9': 500 };
        if (speedKeys[e.key]) {
            paused = false;
            $('speed').value = speedKeys[e.key];
            _savedSpeed = speedKeys[e.key];
            lastFrameTime = 0;
            $('btnPause').textContent = 'Pause';
            $('btnPause').classList.remove('active');
            e.preventDefault();
        }

        // Track held arrow keys for smooth per-frame input
        if (e.key === 'ArrowUp') { _keysHeld.up = true; e.preventDefault(); }
        if (e.key === 'ArrowDown') { _keysHeld.down = true; e.preventDefault(); }
        if (e.key === 'ArrowLeft') { _keysHeld.left = true; _keysHeld.leftStart = _keysHeld.leftStart || performance.now(); e.preventDefault(); }
        if (e.key === 'ArrowRight') { _keysHeld.right = true; _keysHeld.rightStart = _keysHeld.rightStart || performance.now(); e.preventDefault(); }
    });
    window.addEventListener('keyup', e => {
        if (e.key === 'ArrowUp') { _keysHeld.up = false; e.preventDefault(); }
        if (e.key === 'ArrowDown') { _keysHeld.down = false; e.preventDefault(); }
        if (e.key === 'ArrowLeft') { _keysHeld.left = false; _keysHeld.leftStart = 0; e.preventDefault(); }
        if (e.key === 'ArrowRight') { _keysHeld.right = false; _keysHeld.rightStart = 0; e.preventDefault(); }
    });

    // Mouse drag interaction on canvas
    setupMouseInteraction();

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
// Start animation loop via rAF so timestamp is always valid (never undefined).
// Calling animationLoop() directly would pass undefined as timestamp, poisoning
// animationTime with NaN — which permanently kills any Practice that gets ticked.
requestAnimationFrame(animationLoop);
// Focus canvas for keyboard input
canvas.focus();
