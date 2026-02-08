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
        personData: null,    // reference to content.json person entry
        x: 0, z: 0,         // world position offset
        direction: 0,        // facing angle (degrees)
        top: {               // per-body top physics (independent spin/tilt/drift)
            active: false, tilt: 0, tiltTarget: 0,
            precessionAngle: 0, nutationPhase: 0, nutationAmp: 0,
            driftX: 0, driftZ: 0, driftVX: 0, driftVZ: 0,
        },
    };
}
let bodies = [];              // Body[] — all characters in the current scene
let activeScene = null;       // current scene name or null (solo mode)
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
const FRICTION = 0.98;        // velocity decay per frame (lower = slows faster)
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

        // Auto-load first scene (Grand Chorus) or fall back to first person
        if (contentIndex.scenes?.length) {
            $('selScene').value = '0';
            await loadScene(0);
        } else if (contentIndex.people?.length) {
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

    // Scene dropdown: scenes first, Solo at the bottom
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
        const soloOpt = document.createElement('option');
        soloOpt.value = '';
        soloOpt.textContent = 'Solo';
        sceneSel.appendChild(soloOpt);
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

// Find a person entry by name (case-insensitive)
function findPersonByName(name) {
    if (!contentIndex?.people) return null;
    const lower = name.toLowerCase();
    return contentIndex.people.find(p => p.name.toLowerCase() === lower) || null;
}

// Load a multi-body scene. Each cast member gets their own Body with independent
// skeleton, meshes, animation, position, and top-physics state.
async function loadScene(sceneIndex) {
    if (!contentIndex?.scenes?.[sceneIndex]) return;
    const scene = contentIndex.scenes[sceneIndex];
    activeScene = scene.name;
    bodies = [];

    for (const cast of scene.cast) {
        const person = findPersonByName(cast.person);
        if (!person) { console.warn(`[loadScene] person not found: ${cast.person}`); continue; }

        const body = createBody();
        body.personData = person;
        body.x = cast.x || 0;
        body.z = cast.z || 0;
        body.direction = cast.direction || 0;

        // Load skeleton
        const skelName = person.skeleton || 'adult';
        const skelFile = skelName.includes('.cmx') ? skelName : skelName + '-skeleton.cmx';
        try {
            const skelResp = await fetch('data/' + skelFile);
            const skelText = await skelResp.text();
            const skelData = parseCMX(skelText);
            if (skelData.skeletons?.length) {
                body.skeleton = buildSkeleton(skelData.skeletons[0]);
                updateTransforms(body.skeleton);
            }
        } catch (e) { console.warn(`[loadScene] skeleton ${skelFile}:`, e); }

        if (!body.skeleton) continue;

        // Load meshes (body, head, hands) with textures
        const meshParts = [
            { name: person.body, tex: person.bodyTexture },
            { name: person.head, tex: person.headTexture },
            { name: person.leftHand, tex: person.handTexture },
            { name: person.rightHand, tex: person.handTexture },
        ];
        for (const part of meshParts) {
            if (!part.name) continue;
            const meshKey = part.name;
            if (!content.meshes[meshKey]) {
                // Load SKN
                const sknFile = meshKey + '.skn';
                try {
                    const resp = await fetch('data/' + sknFile);
                    const text = await resp.text();
                    content.meshes[meshKey] = parseSKN(text);
                } catch (e) { continue; }
            }
            const mesh = content.meshes[meshKey];
            if (!mesh) continue;
            const boneMap = new Map();
            for (const bone of body.skeleton) {
                if (bone.name === mesh.boneName) boneMap.set(mesh.boneName, bone);
                else boneMap.set(bone.name, bone);
            }

            // Use the same getTexture() as solo mode — returns cached WebGLTexture
            const texture = part.tex ? await getTexture(part.tex) : null;
            body.meshes.push({ mesh, boneMap, texture });
        }

        // Load animation
        const animName = cast.animation || person.animation;
        if (animName) {
            body.practice = await loadAnimationForBody(animName, body.skeleton);
        }

        bodies.push(body);
    }

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

    animationTime = 0;
    lastFrameTime = 0;
    const status = $('status');
    if (status) status.textContent = `Scene: ${scene.name} (${bodies.length} characters)`;
    renderFrame();
}

// Load an animation (Practice) for a specific body's skeleton.
// Uses the same CFP loading path as the solo loader in updateScene().
async function loadAnimationForBody(animName, skeleton) {
    // Find the skill by name in already-loaded skills
    let skill = content.skills[animName];

    if (!skill) {
        // Search by internal name field (case-insensitive)
        const lower = animName.toLowerCase();
        skill = Object.values(content.skills).find(
            s => s.name?.toLowerCase() === lower
        );
        // Substring match: "adult-dance-inplace-twistloop" matches "a2o-dance-inplace-twistloop"
        if (!skill) {
            // Strip common prefixes and try matching the tail
            const stripped = lower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
            skill = Object.values(content.skills).find(s => {
                const sLower = (s.name || '').toLowerCase();
                const sStripped = sLower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
                return sStripped === stripped || sLower.includes(stripped) || stripped.includes(sLower.replace(/^a2o-/, ''));
            });
        }
    }

    if (!skill) {
        // Try loading all animation CMXs to find the skill
        for (const cmxFile of contentIndex.animations || []) {
            if (content.skills[cmxFile.replace('.cmx', '')]) continue;
            try {
                const resp = await fetch('data/' + cmxFile);
                const text = await resp.text();
                const data = parseCMX(text);
                for (const s of data.skills || []) content.skills[s.name] = s;
            } catch (e) { }
        }
        const lower = animName.toLowerCase();
        const stripped = lower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
        skill = Object.values(content.skills).find(s => {
            const sLower = (s.name || '').toLowerCase();
            const sStripped = sLower.replace(/^(adult|ross|child|c2o|a2o)-/, '');
            return sLower === lower || sStripped === stripped;
        });
    }

    if (!skill?.motions?.length) {
        console.warn(`[loadAnimationForBody] skill not found: ${animName}`);
        return null;
    }

    // Load CFP using the same key scheme as the solo loader
    const cfpName = skill.animationFileName;
    if (cfpName && !cfpCache.has(cfpName) && (skill.numTranslations > 0 || skill.numRotations > 0)) {
        const cfpFile = cfpIndex.get(cfpName.toLowerCase());
        if (cfpFile) {
            try {
                const resp = await fetch('data/' + cfpFile);
                if (resp.ok) {
                    cfpCache.set(cfpName, await resp.arrayBuffer());
                }
            } catch (e) { }
        }
    }

    const buffer = cfpCache.get(cfpName);
    if (buffer) {
        skill.translations = [];
        skill.rotations = [];
        parseCFP(buffer, skill);
    }

    const practice = new Practice(skill, skeleton);
    if (practice.ready) {
        practice.tick(0);
        updateTransforms(skeleton);
    }
    return practice;
}

// Exit scene mode, return to solo viewing
function exitScene() {
    activeScene = null;
    bodies = [];
    const sel = $('selScene');
    if (sel) sel.value = '';
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
function tickAllBodiesTop() {
    if (bodies.length > 0) {
        for (const body of bodies) tickTopFor(body.top);
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

    // Solo mode: try per-person JSON voice first
    const peopleSelect = $('selPerson');
    if (peopleSelect && contentIndex?.people) {
        const idx = parseInt(peopleSelect.value, 10);
        const person = contentIndex.people[idx];
        if (person?.voice) {
            const v = person.voice;
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

            // Get this body's voice params from their person data
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

    for (const body of bodiesToRender) {
        const bTop = body.top || top;
        // Scene mode: rotY spins each body around its own center (added to base direction)
        // Solo mode: direction is 0 (camera does the orbiting)
        const spinDeg = sceneMode ? (body.direction || 0) + rotYDeg : 0;
        const bodyDir = spinDeg * Math.PI / 180;
        const cosD = Math.cos(bodyDir);
        const sinD = Math.sin(bodyDir);

        for (const { mesh, boneMap, texture } of body.meshes) {
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
        }
    }
}

// Animation loop: ticks Practice animation + applies rotation momentum.
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
            // Scene mode: tick every body's own practice
            for (const body of bodies) {
                if (body.practice?.ready && body.skeleton) {
                    body.practice.tick(animationTime);
                    updateTransforms(body.skeleton);
                    needsRender = true;
                }
            }
        } else if (activePractice?.ready && activeSkeleton) {
            // Solo mode
            activePractice.tick(animationTime);
            updateTransforms(activeSkeleton);
            needsRender = true;
        }
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

    // Top physics: all bodies respond to the same spin, each with independent state
    tickAllBodiesTop();
    const anyTopActive = bodies.length > 0
        ? bodies.some(b => b.top.active)
        : top.active;
    if (anyTopActive) needsRender = true;

    // Spin sound: pitch tracks velocity, fades as they slow down
    updateSpinSound();

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
        initSpinSound(); // init audio on first gesture (browser policy)
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
            let zoomVal = parseFloat(zoomSlider.value) + dy * 0.25;
            zoomVal = Math.max(15, Math.min(200, zoomVal));
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
        val = Math.max(15, Math.min(200, val));
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
        val = Math.max(15, Math.min(200, val));
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
        if (!isNaN(idx)) { exitScene(); applyPerson(idx); }
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
