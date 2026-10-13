function escapeForJs(str) {
  if (!str) return "";
  return String(str)
    .replace(/\\/g, "\\\\")
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

let currentSceneData = null;
let currentAudio = null;
let currentAudioButton = null;
let currentVisualStyle = "realistic"; // 'realistic' ou 'stylized'
let selectedPdfFile = null;
let currentChapterData = null;
let currentReaderLang = "pt"; // 'pt' ou 'orig'

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  await loadProjectsList();
  await loadProjectConfig();
  await loadScenesList();
  await loadVisualBible();
  await loadBookText();
  await loadBookChapters();
  setupEventListeners();
}

// ==========================================
// NAVEGAÇÃO DE ABAS
// ==========================================
function switchMainTab(tabName) {
  // Atualiza botões
  document.querySelectorAll(".tab-nav-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById(`tab-btn-${tabName}`).classList.add("active");

  // Atualiza painéis
  document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.remove("active"));
  document.getElementById(`tab-content-${tabName}`).classList.add("active");

  // Esconde/mostra seletor de cenas dependendo da aba
  const scenesSection = document.getElementById("sidebar-scenes-section");
  if (tabName === "shots") {
    scenesSection.style.display = "block";
  } else {
    scenesSection.style.display = "none";
  }
}

// ==========================================
// DIREÇÃO DE ARTE / ESTILO VISUAL GLOBAL
// ==========================================
async function loadProjectConfig() {
  try {
    const res = await fetch("/api/project/config");
    if (res.ok) {
      const data = await res.json();
      if (data.visual_style) {
        currentVisualStyle = data.visual_style;
        updateStyleButtonsUI(currentVisualStyle);
      }
    }
  } catch (err) {
    console.warn("Aviso ao carregar config do projeto:", err);
  }
}

function updateStyleButtonsUI(style) {
  const btnRealistic = document.getElementById("btn-style-realistic");
  const btnStylized = document.getElementById("btn-style-stylized");
  if (btnRealistic && btnStylized) {
    if (style === "stylized") {
      btnStylized.classList.add("active");
      btnRealistic.classList.remove("active");
    } else {
      btnRealistic.classList.add("active");
      btnStylized.classList.remove("active");
    }
  }
}

async function setVisualStyle(style) {
  currentVisualStyle = style;
  updateStyleButtonsUI(style);

  const styleLabel = style === "stylized" ? "🎨 Animação 3D (Pixar/DreamWorks)" : "🎥 Realista (35mm Cinematográfico)";
  showToast(`Direção de Arte alterada para: ${styleLabel}`);

  // Persiste no backend
  try {
    await fetch("/api/project/style", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visual_style: style })
    });
  } catch (err) {
    console.warn("Aviso ao salvar estilo no projeto:", err);
  }

  // Atualiza Bíblia Visual imediatamente com os novos prompts e badges
  await loadVisualBible();

  // Atualiza Caderno de Planos se houver cena carregada
  if (currentSceneData && currentSceneData.scene_id) {
    await loadSceneDetails(currentSceneData.scene_id);
  }
}

// ==========================================
// ABA 1: PLANOS & CADERNO DE 6s
// ==========================================
async function loadScenesList() {
  try {
    const res = await fetch("/api/scenes");
    const data = await res.json();
    const container = document.getElementById("scenes-list");
    container.innerHTML = "";

    if (!data.scenes || data.scenes.length === 0) {
      container.innerHTML = `<div class="scene-loading">Nenhuma cena encontrada.</div>`;
      return;
    }

    data.scenes.forEach((scene, index) => {
      const btn = document.createElement("button");
      // Seleciona SC_01 por padrão se existir
      const isDefault = scene.id === "SC_01" || (index === 0 && !data.scenes.some(s => s.id === "SC_01"));
      btn.className = `scene-nav-item ${isDefault ? "active" : ""}`;
      btn.innerHTML = `
        <span>🎬 ${scene.id}</span>
        <span style="font-size:10px; color:var(--text-muted);">${scene.total_shots || 3} planos</span>
      `;
      btn.onclick = () => selectScene(scene.id, btn);
      container.appendChild(btn);

      if (isDefault) {
        loadSceneDetails(scene.id);
      }
    });
  } catch (err) {
    console.error("Erro ao carregar lista de cenas:", err);
  }
}

function selectScene(sceneId, buttonEl) {
  document.querySelectorAll(".scene-nav-item").forEach(el => el.classList.remove("active"));
  buttonEl.classList.add("active");
  loadSceneDetails(sceneId);
}

async function loadSceneDetails(sceneId) {
  try {
    const res = await fetch(`/api/scene/${sceneId}`);
    const scene = await res.json();
    currentSceneData = scene;
    renderScene(scene);
  } catch (err) {
    console.error(`Erro ao carregar cena ${sceneId}:`, err);
  }
}

function renderScene(scene) {
  document.getElementById("scene-id-badge").textContent = scene.scene_id || "SC_01";
  document.getElementById("scene-location-text").textContent = scene.location || "Ambiente";
  document.getElementById("scene-title-text").textContent = scene.title || "Cena Sem Título";

  // Chip de Locação Principal com cópia 1-clique
  const locChip = document.getElementById("scene-location-chip");
  const locTag = scene.location_tag || (scene.locations && scene.locations[0]) || "@sala_30_andar";
  if (locChip) {
    locChip.dataset.tag = locTag;
    locChip.innerHTML = `🏛️ ${escapeHtml(locTag)} <span class="tag-copy-icon">📋</span>`;
    locChip.onclick = () => copyTag(locTag);
  }

  // Chips de Personagens com cópia 1-clique
  const charRow = document.getElementById("scene-characters-list");
  if (charRow) {
    charRow.innerHTML = "";
    (scene.characters || []).forEach(char => {
      const chip = document.createElement("button");
      chip.className = "asset-tag-pill char-pill";
      chip.title = `Clique para copiar ${char}`;
      chip.innerHTML = `👤 ${escapeHtml(char)} <span class="tag-copy-icon">📋</span>`;
      chip.onclick = () => copyTag(char);
      charRow.appendChild(chip);
    });
  }

  // Chips de Props e Objetos com cópia 1-clique
  const propsRow = document.getElementById("scene-props-list");
  if (propsRow) {
    propsRow.innerHTML = "";
    (scene.props || []).forEach(prop => {
      const chip = document.createElement("button");
      chip.className = "asset-tag-pill prop-pill";
      chip.title = `Clique para copiar ${prop}`;
      chip.innerHTML = `📦 ${escapeHtml(prop)} <span class="tag-copy-icon">📋</span>`;
      chip.onclick = () => copyTag(prop);
      propsRow.appendChild(chip);
    });
  }

  const beats = scene.beats || [];
  let totalDur = 0;
  beats.forEach(b => {
    totalDur += b.duration_s || 6.0;
  });
  document.getElementById("stat-total-duration").textContent = `${totalDur.toFixed(1)}s`;
  document.getElementById("stat-total-shots").textContent = beats.length;

  const grid = document.getElementById("shots-grid");
  grid.innerHTML = "";

  beats.forEach((beat, index) => {
    const card = createShotCard(beat, index + 1);
    grid.appendChild(card);
  });

  renderTimeline(beats, totalDur);
  updateSceneCockpit(scene);
}

function createShotCard(beat, planNumber) {
  const card = document.createElement("div");
  card.className = "shot-card";
  card.id = `card-${beat.shot_id}`;

  const hasAudio = Boolean(beat.audio_file || beat.audio_duration_s);
  const hasImage = Boolean(beat.generated_image || (beat.actor_image && !beat.actor_image.includes("placeholder")));
  const hasVideo = Boolean(beat.video_url);

  let shotStatus = "need_image";
  if (hasVideo) {
    shotStatus = "completed";
  } else if (hasImage) {
    shotStatus = "ready_video";
  } else {
    shotStatus = "need_image";
  }
  card.dataset.status = shotStatus;

  const isLastFrame = (beat.start_frame_instruction || "").includes("ÚLTIMO FRAME");

  // Formatando sliders do Kling
  const sliders = beat.kling_camera_controls || {};
  let slidersHtml = "";
  for (const [key, val] of Object.entries(sliders)) {
    if (val !== 0) {
      slidersHtml += `
        <div class="slider-pill active">
          <span>${capitalize(key)}:</span>
          <strong>${val > 0 ? "+" + val : val}</strong>
        </div>
      `;
    }
  }
  if (!slidersHtml) {
    slidersHtml = `<div class="slider-pill"><span>Câmera:</span><strong>Estática</strong></div>`;
  }

  const slidersText = Object.entries(sliders)
    .filter(([_, v]) => v !== 0)
    .map(([k, v]) => `${capitalize(k)}: ${v > 0 ? '+' + v : v}`)
    .join(', ') || 'Câmera Estática';

  // 1. Tags Rápidas de Ativos (Clique para Copiar)
  const locTag = beat.location_tag || currentSceneData?.location_tag || "@sala_30_andar";
  const locName = beat.location_name || currentSceneData?.location || "Sala do 30º Andar (Wayside School)";
  const sceneEnv = beat.scene_environment || "Sala de aula do 30º andar da Escola Wayside, janelas altas de guilhotina com vista para as nuvens, luz fria de fim de tarde.";
  const charsPresent = beat.characters_present || [];
  const propsPresent = beat.props_present || [];
  const propsInShot = beat.props_in_shot || [];

  const quickTagsHtml = `
    <div class="shot-quick-tags-bar">
      <span class="shot-quick-tags-title">TAGS DO PLANO (COPIAR):</span>
      <button class="tag-btn tag-btn-location" onclick="copyTag('${escapeForJs(locTag)}')" title="Copiar tag de cenário">
        🏛️ ${escapeHtml(locTag)} 📋
      </button>
      ${charsPresent.map(cp => `
        <button class="tag-btn tag-btn-char" onclick="copyTag('${escapeForJs(cp.tag || '')}')" title="Copiar tag do personagem">
          👤 ${escapeHtml(cp.tag || '')} 📋
        </button>
      `).join('')}
      ${(propsPresent.length ? propsPresent.map(p => p.tag) : propsInShot).map(pTag => `
        <button class="tag-btn tag-btn-prop" onclick="copyTag('${escapeForJs(pTag)}')" title="Copiar tag do objeto">
          📦 ${escapeHtml(pTag)} 📋
        </button>
      `).join('')}
    </div>
  `;

  // 2. Card Detalhado do Cenário & Locação
  const locationBoxHtml = `
    <div class="element-detail-card location-detail-card">
      <div class="element-detail-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <button class="tag-btn tag-btn-location" onclick="copyTag('${escapeForJs(locTag)}')" style="margin:0;">
            🏛️ ${escapeHtml(locTag)} 📋
          </button>
          <strong style="color:#f8fafc; font-size:13.5px;">${escapeHtml(locName)}</strong>
        </div>
        <button class="btn-copy-mini" onclick="copyTag('${escapeForJs(locTag)}')">Copiar @cenário</button>
      </div>
      <div class="element-detail-desc">${escapeHtml(sceneEnv)}</div>
    </div>
  `;

  // 3. Cards Detalhados dos Personagens em Cena
  let charsHtml = "";
  if (charsPresent.length > 0) {
    charsHtml = charsPresent.map(cp => `
      <div class="element-detail-card char-detail-card">
        <div class="element-detail-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="tag-btn tag-btn-char" onclick="copyTag('${escapeForJs(cp.tag || '')}')" style="margin:0;">
              👤 ${escapeHtml(cp.tag || '@personagem')} 📋
            </button>
            <strong style="color:#f8fafc; font-size:13.5px;">${escapeHtml(cp.name || '')}</strong>
          </div>
          <button class="btn-copy-mini" onclick="copyTag('${escapeForJs(cp.tag || '')}')">Copiar @tag</button>
        </div>
        <div class="element-detail-desc">${escapeHtml(cp.physical_description || 'Descrição física não informada.')}</div>
      </div>
    `).join("");
  } else {
    charsHtml = `<div class="element-empty-msg">Plano focado em detalhes de cenário e objetos (sem personagens principais em destaque).</div>`;
  }

  // 4. Cards Detalhados dos Objetos e Props
  let propsHtml = "";
  if (propsPresent.length > 0) {
    propsHtml = propsPresent.map(p => `
      <div class="element-detail-card prop-detail-card">
        <div class="element-detail-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="tag-btn tag-btn-prop" onclick="copyTag('${escapeForJs(p.tag || '')}')" style="margin:0;">
              📦 ${escapeHtml(p.tag || '')} 📋
            </button>
            <strong style="color:#f8fafc; font-size:13.5px;">${escapeHtml(p.name || '')}</strong>
          </div>
          <button class="btn-copy-mini" onclick="copyTag('${escapeForJs(p.tag || '')}')">Copiar @objeto</button>
        </div>
        <div class="element-detail-desc">${escapeHtml(p.description || 'Objeto físico essencial do plano.')}</div>
      </div>
    `).join("");
  } else if (propsInShot.length > 0) {
    propsHtml = propsInShot.map(pTag => `
      <div class="element-detail-card prop-detail-card">
        <div class="element-detail-header">
          <button class="tag-btn tag-btn-prop" onclick="copyTag('${escapeForJs(pTag)}')">
            📦 ${escapeHtml(pTag)} 📋
          </button>
          <button class="btn-copy-mini" onclick="copyTag('${escapeForJs(pTag)}')">Copiar @objeto</button>
        </div>
      </div>
    `).join("");
  } else {
    propsHtml = `<div class="element-empty-msg">Nenhum adereço secundário neste plano.</div>`;
  }

  // Imagem Hero 16:9 Cinematográfica do Plano
  const heroImgUrl = beat.generated_image || beat.actor_image || '';
  let heroBannerHtml = '';

  // Prompts Hiper-Detalhados: Separação de Start-Frame (Imagem) e Movimento (Vídeo)
  const imagePrompt = beat.image_prompt_en || beat.prompt_en || "";
  const videoPrompt = beat.video_prompt_en || beat.prompt_en || "";
  const negativePrompt = beat.negative_prompt || "cartoon, 3d render, CGI, smooth plastic skin, deformed hands, extra fingers, morphing face, temporal flicker, low bitrate, modern technology, oversaturated, watermark, blurry background";

  const videoUrl = beat.video_url || '';

  if (videoUrl) {
    heroBannerHtml = `
      <div class="shot-cinematic-hero" id="hero-box-${beat.shot_id}">
        <div class="shot-hero-media-wrapper" style="position:relative; background:#000;">
          <video src="${videoUrl}" controls class="shot-hero-img" style="object-fit:cover; width:100%; height:100%; border-radius:8px;" loop></video>
          <div class="shot-hero-overlay" style="pointer-events:none;">
            <div class="shot-hero-badges">
              <span class="badge-source" style="background:#10b981; color:#fff;">🎬 Vídeo IA Pronto</span>
              <span class="badge-aspect">16:9 MP4</span>
              ${beat.last_frame_url ? `<span class="badge-source" style="background:#4f46e5; color:#fff;">🔗 Chaining Ativo</span>` : ''}
            </div>
          </div>
          <div class="shot-hero-actions" style="position:absolute; bottom:12px; right:12px; display:flex; gap:8px;">
            <button class="btn-hero-zoom" style="background:linear-gradient(135deg, #6366f1, #4f46e5); font-weight:700;" onclick="event.stopPropagation(); generateShotVideo('${escapeForJs(beat.shot_id)}', this)">🔄 Regerar Vídeo IA</button>
          </div>
        </div>
      </div>
    `;
  } else if (heroImgUrl) {
    const isStylized = currentVisualStyle === "stylized";
    heroBannerHtml = `
      <div class="shot-cinematic-hero" id="hero-box-${beat.shot_id}">
        <div class="shot-hero-media-wrapper" onclick="openImageModal('${heroImgUrl}', 'Plano ${String(planNumber).padStart(2, "0")} — ${beat.shot_id}')">
          <img src="${heroImgUrl}" alt="Quadro 16:9 ${beat.shot_id}" class="shot-hero-img" id="hero-img-${beat.shot_id}">
          <div class="shot-hero-overlay">
            <div class="shot-hero-badges">
              <span class="badge-film-lens">${isStylized ? '🎨 3D Animação' : '🎥 35mm'} • ${beat.lens_mm || 50}mm</span>
              <span class="badge-aspect">16:9 Cinema</span>
              <span class="badge-source">${isStylized ? '✨ Estilo Pixar/3D' : '✨ Fotorrealista (35mm)'}</span>
            </div>
            <div class="shot-hero-actions">
              <button class="btn-hero-zoom" onclick="event.stopPropagation(); openImageModal('${heroImgUrl}', 'Plano ${String(planNumber).padStart(2, "0")} — ${beat.shot_id}')">🔍 Expandir 16:9</button>
              <button class="btn-hero-zoom" style="background:linear-gradient(135deg, #6366f1, #4f46e5); border-color:#6366f1; font-weight:700;" onclick="event.stopPropagation(); generateShotVideo('${escapeForJs(beat.shot_id)}', this)">🎬 Gerar Vídeo IA (I2V)</button>
              <button class="btn-hero-zoom" style="background:linear-gradient(135deg, #10b981, #059669); border-color:#059669; font-weight:700;" onclick="event.stopPropagation(); generateShotImage('${escapeForJs(beat.shot_id)}', '${escapeForJs(imagePrompt)}', this)">🎨 Regenerar com FLUX</button>
              <button class="btn-hero-zoom" style="background:rgba(255,255,255,0.12); border-color:rgba(255,255,255,0.3); font-weight:600;" onclick="event.stopPropagation(); triggerShotUpload('${escapeForJs(beat.shot_id)}')">📁 Upload Imagem</button>
            </div>
          </div>
        </div>
      </div>
    `;
  } else {
    const isStylized = currentVisualStyle === "stylized";
    heroBannerHtml = `
      <div class="shot-cinematic-hero shot-hero-placeholder" id="hero-box-${beat.shot_id}">
        <div class="shot-placeholder-content">
          <div class="shot-placeholder-icon">${isStylized ? '🎨' : '🎬'}</div>
          <div class="shot-placeholder-text">
            <strong>Quadro Inicial 16:9 (${isStylized ? 'Animação 3D' : 'Realista 35mm'})</strong>
            <span>Pronto para renderização com fal.ai (FLUX.3) ou upload externo (Midjourney)</span>
          </div>
          <div style="display:flex; gap:10px; margin-top:8px; flex-wrap:wrap; justify-content:center;">
            <button class="btn btn-primary btn-sm" style="background:linear-gradient(135deg, #10b981, #059669); font-weight:700;" onclick="generateShotImage('${escapeForJs(beat.shot_id)}', '${escapeForJs(imagePrompt)}', this)">
              🎨 Gerar com FLUX
            </button>
            <button class="btn btn-secondary btn-sm" style="border-color:rgba(245, 158, 11, 0.6); font-weight:700; color:var(--gold-primary);" onclick="triggerShotUpload('${escapeForJs(beat.shot_id)}')">
              📁 Upload Imagem Externa (Midjourney)
            </button>
          </div>
        </div>
      </div>
    `;
  }

  const locThumb = beat.location_image ? `
    <div class="shot-assets-preview-row">
      <div class="asset-thumb-box">
        <img src="${beat.location_image}" alt="Cenário" class="asset-thumb-img">
        <div class="asset-thumb-info">
          <span class="asset-thumb-label">Referência de Cenário</span>
          <span class="asset-thumb-title">Sala do 30º Andar (Wayside)</span>
        </div>
      </div>
      <div class="asset-thumb-box" style="margin-left:auto;">
        <span class="asset-thumb-label" style="color:var(--gold-primary);">Lente</span>
        <span class="asset-thumb-title">${beat.lens_mm || 50}mm Anamórfica</span>
      </div>
    </div>
  ` : '';

  const stepperHtml = `
    <div class="shot-stepper">
      <span class="step-chip ${hasAudio ? 'step-done' : 'step-pending'}">
        ${hasAudio ? '✓' : '1.'} 🎙️ Áudio ${hasAudio ? 'Pronto' : 'Pendente'}
      </span>
      <span class="step-divider">➔</span>
      <span class="step-chip ${hasImage ? 'step-done' : 'step-pending'}">
        ${hasImage ? '✓' : '2.'} 🖼️ Imagem ${hasImage ? 'Pronta' : 'Pendente'}
      </span>
      <span class="step-divider">➔</span>
      <span class="step-chip ${hasVideo ? 'step-done' : (hasImage ? 'step-active' : 'step-pending')}">
        ${hasVideo ? '✓' : '3.'} 🎬 Vídeo 6s ${hasVideo ? 'Pronto' : 'Pendente'}
      </span>
      <span class="step-divider">➔</span>
      <span class="step-chip step-done">
        ✓ 4. ✂️ Linha do Tempo
      </span>
      <button class="btn-edit-shot" onclick="openEditShotModal('${escapeForJs(beat.shot_id)}')">
        ✏️ Editar Plano
      </button>
    </div>
  `;

  // Botão Inteligente de Próxima Ação
  let nextActionHtml = '';
  if (!hasImage) {
    nextActionHtml = `
      <button class="btn-next-action action-image" onclick="generateShotImage('${escapeForJs(beat.shot_id)}', '${escapeForJs(imagePrompt)}', this)">
        <span>🎨</span> <strong>Próximo Passo:</strong> Gerar Start Frame com FLUX.1
      </button>
    `;
  } else if (!hasVideo) {
    nextActionHtml = `
      <button class="btn-next-action action-video" onclick="generateShotVideo('${escapeForJs(beat.shot_id)}', this)">
        <span>🎬</span> <strong>Próximo Passo:</strong> Animar Vídeo de 6s no Kling AI / Runway
      </button>
    `;
  } else {
    nextActionHtml = `
      <button class="btn-next-action action-done" onclick="openScenePreviewModal()">
        <span>✓</span> <strong>Plano Concluído:</strong> Vídeo 16:9 Pronto (Assistir na Prévia)
      </button>
    `;
  }

  card.innerHTML = `
    <div class="shot-top-bar">
      <div class="shot-title-group">
        <span class="shot-index">PLANO ${String(planNumber).padStart(2, "0")} — ${beat.shot_id}</span>
        <span class="shot-type-badge">${beat.shot_type || "Medium Shot"}</span>
        <span class="shot-lens">${beat.lens_mm || 50}mm</span>
        ${beat.camera_movement ? `<span class="shot-lens" style="background:rgba(255,255,255,0.06); color:#94a3b8;">🎥 ${beat.camera_movement}</span>` : ''}
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <button class="btn-edit-shot" style="margin:0;" onclick="openEditShotModal('${escapeForJs(beat.shot_id)}')">✏️ Editar</button>
        <div class="shot-duration-badge">⏱️ ${beat.duration_s || 6.0}s</div>
      </div>
    </div>

    <!-- Barra de Tags Rápidas do Plano (Clique para Copiar) -->
    ${quickTagsHtml}

    <!-- Stepper Visual de 4 Passos -->
    ${stepperHtml}

    <!-- Botão Guiado de Próxima Ação -->
    ${nextActionHtml}

    <!-- Banner Cinematográfico 16:9 do Plano -->
    ${heroBannerHtml}

    ${locThumb}

    <!-- Regras Cinematográficas de 6s: Papel Dramático e Eyeline Match -->
    <div style="display:flex; gap:10px; margin-bottom:12px; align-items:center; flex-wrap:wrap;">
      ${getRoleBadge(beat.role)}
      ${getEyelineBadge(beat.eyeline_match)}
    </div>

    <!-- Banner de Start Frame e Continuidade -->
    <div class="start-frame-banner ${isLastFrame ? 'warn' : ''}">
      <span>${isLastFrame ? '⚠️' : '🖼️'}</span>
      <div>
        <strong>Continuidade / Start Frame:</strong> 
        <span>${escapeHtml(beat.start_frame_instruction || "Utilizar P1_front como referência inicial.")}</span>
      </div>
    </div>

    <!-- Bloco 0: Elementos Presentes na Cena (Personagens com DNA, Cenário com @tag e Props com @tags) -->
    <div class="shot-block elements-block" style="border-left: 3px solid var(--gold-primary); background: rgba(245, 158, 11, 0.03); margin-bottom: 12px;">
      <div class="block-header">
        <div class="block-title" style="color:var(--gold-primary);">📋 ELEMENTOS EM CENA (O QUE CADA BLOCO DE CENA PRECISA)</div>
      </div>
      <div style="padding:12px 14px; background:rgba(0,0,0,0.28); border-radius:6px; display:flex; flex-direction:column; gap:12px;">
        <!-- Cenário -->
        <div>
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <strong style="color:#cbd5e1; font-size:13px; letter-spacing:0.3px;">🏛️ Cenário & Locação:</strong>
            <span style="font-size:11px; color:var(--text-muted);">Clique na tag para copiar</span>
          </div>
          ${locationBoxHtml}
        </div>

        <!-- Personagens -->
        <div>
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <strong style="color:#cbd5e1; font-size:13px; letter-spacing:0.3px;">👤 Personagens em Cena:</strong>
            <span style="font-size:11px; color:var(--text-muted);">${charsPresent.length} presente(s)</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">${charsHtml}</div>
        </div>

        <!-- Props e Objetos -->
        <div>
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
            <strong style="color:#cbd5e1; font-size:13px; letter-spacing:0.3px;">📦 Objetos / Props em Jogo:</strong>
            <span style="font-size:11px; color:var(--text-muted);">${(propsPresent.length || propsInShot.length)} objeto(s)</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">${propsHtml}</div>
        </div>
      </div>
    </div>

    <!-- Bloco 1: O que Acontece no Vídeo (Ação & Nexo Narrativo em Português) -->
    <div class="shot-block action-block">
      <div class="block-header">
        <div class="block-title">🎬 1. O QUE ACONTECE NA CENA (AÇÃO & SUBTEXTO DRAMÁTICO - PT-BR)</div>
        <button class="btn-copy" onclick="copyText('${escapeForJs(beat.action_pt || "")}')">📋 Copiar Ação</button>
      </div>
      <div class="prompt-box action-box">${escapeHtml(beat.action_pt || "Ação contínua da cena.")}</div>
    </div>

    <!-- Bloco 2: Locução / Diálogo Contínuo em Português -->
    <div class="shot-block narration-block">
      <div class="block-header">
        <div class="block-title">🎙️ 2. LOCUÇÃO & DIÁLOGOS (PORTUGUÊS DO BRASIL - L-CUT)</div>
        <button class="btn-copy" onclick="copyText('${escapeForJs(beat.narration)}')">📋 Copiar Fala</button>
      </div>
      <div class="prompt-box narration-box">${escapeHtml(beat.narration)}</div>
      
      <!-- Player de Áudio Embutido -->
      ${beat.audio_file ? `
        <div class="audio-player-row">
          <button class="btn-play-audio" onclick="toggleAudio('${beat.audio_file.startsWith('/api/') ? beat.audio_file : '/api/audio/' + beat.audio_file}', this)">▶</button>
          <span class="audio-label">Ouvir Locução Neural PT-BR (${beat.audio_duration_s || 0}s)</span>
        </div>
      ` : ''}
    </div>

    <!-- Gaveta Retrátil de Prompts Técnicos ("Modo Clean") -->
    <div class="prompt-drawer">
      <button class="prompt-drawer-toggle" onclick="togglePromptDrawer(this)">
        <span style="display:flex; align-items:center; gap:8px;">
          <span>🎛️</span>
          <span>Ver Prompts Técnicos & Sliders (Kling AI / FLUX / Negativo)</span>
        </span>
        <span class="drawer-arrow">▼</span>
      </button>
      <div class="prompt-drawer-content" style="display:none;">
        <!-- Bloco 3: Controles de Câmera Kling -->
        <div class="shot-block" style="margin-bottom:0;">
          <div class="block-header">
            <div class="block-title">🎛️ 3. CONTROLES DE CÂMERA (SLIDERS NUMÉRICOS KLING AI)</div>
            <button class="btn-copy" onclick="copyText('${escapeForJs(slidersText)}')">📋 Copiar Sliders</button>
          </div>
          <div class="camera-sliders-grid">${slidersHtml}</div>
        </div>

        <!-- Bloco 4: Prompt de Imagem Estática (Start-Frame para FLUX / Midjourney) -->
        <div class="shot-block" style="margin-bottom:0;">
          <div class="block-header">
            <div class="block-title" style="color:var(--gold-primary);">🖼️ 4. PROMPT DE IMAGEM ESTÁTICA (START FRAME - FLUX.1 / MIDJOURNEY / IMAGEN 3)</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn-copy btn-generate-img" style="background:linear-gradient(135deg, #10b981, #059669); font-weight:700;" onclick="generateShotImage('${escapeForJs(beat.shot_id)}', '${escapeForJs(imagePrompt)}', this)">🎨 Gerar FLUX</button>
              <button class="btn-copy" style="border-color:rgba(245, 158, 11, 0.6); color:var(--gold-primary);" onclick="triggerShotUpload('${escapeForJs(beat.shot_id)}')">📁 Upload Imagem</button>
              <button class="btn-copy" onclick="copyText('${escapeForJs(imagePrompt)}')">📋 Copiar Prompt</button>
            </div>
          </div>
          <div class="prompt-box image-prompt-box">${escapeHtml(imagePrompt)}</div>
        </div>

        <!-- Bloco 5: Prompt de Vídeo (Dinâmica Temporal de 6s para Kling / Runway / Veo) -->
        <div class="shot-block" style="margin-bottom:0;">
          <div class="block-header">
            <div class="block-title" style="color:var(--cyan-accent);">🎬 5. PROMPT DE VÍDEO (DINÂMICA DE MOVIMENTO 6s - KLING / RUNWAY GEN-3 / VEO 2)</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn-copy" style="background:linear-gradient(135deg, #4f46e5, #4338ca); color:#fff; font-weight:700; border-color:#6366f1;" onclick="generateShotVideo('${escapeForJs(beat.shot_id)}', this)">🎬 Gerar Vídeo IA</button>
              <button class="btn-copy" onclick="copyText('${escapeForJs(videoPrompt)}')">📋 Copiar Vídeo</button>
            </div>
          </div>
          <div class="prompt-box video-prompt-box">${escapeHtml(videoPrompt)}</div>
        </div>

        <!-- Bloco 6: Prompt Negativo Cirúrgico -->
        <div class="shot-block" style="margin-bottom:0;">
          <div class="block-header">
            <div class="block-title">🚫 6. PROMPT NEGATIVO CIRÚRGICO (ANTI-ARTEFATOS)</div>
            <button class="btn-copy" onclick="copyText('${escapeForJs(negativePrompt)}')">📋 Copiar Negativo</button>
          </div>
          <div class="prompt-box negative-prompt-box">${escapeHtml(negativePrompt)}</div>
        </div>
      </div>
    </div>
  `;

  return card;
}

function renderTimeline(beats, totalDuration) {
  const track = document.getElementById("timeline-track");
  track.innerHTML = "";
  document.getElementById("timeline-time-display").textContent = `00:00 / 00:${Math.round(totalDuration)}`;

  beats.forEach((beat, idx) => {
    const dur = beat.duration_s || 6.0;
    const pct = (dur / totalDuration) * 100;

    const seg = document.createElement("div");
    seg.className = "timeline-segment";
    seg.style.width = `${pct}%`;
    seg.title = `Plano ${idx + 1} (${dur}s) - Clique para rolar até o card`;
    seg.innerHTML = `
      <div class="timeline-segment-name">Plano ${idx + 1}</div>
      <div class="timeline-segment-dur">${dur}s</div>
    `;

    seg.onclick = () => {
      const card = document.getElementById(`card-${beat.shot_id}`);
      if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.style.borderColor = "var(--gold-primary)";
        setTimeout(() => { card.style.borderColor = ""; }, 1200);
      }
    };

    track.appendChild(seg);
  });
}

// ==========================================
// COCKPIT DE PRODUÇÃO, FILTROS & PREVIEW
// ==========================================
let currentFilter = 'all';

function updateSceneCockpit(scene) {
  const beats = scene.beats || [];
  const total = beats.length;
  if (total === 0) return;

  let audioCount = 0;
  let imageCount = 0;
  let videoCount = 0;

  beats.forEach(b => {
    const hasAudio = Boolean(b.audio_file || b.audio_duration_s);
    const hasImage = Boolean(b.generated_image || (b.actor_image && !b.actor_image.includes("placeholder")));
    const hasVideo = Boolean(b.video_url);

    if (hasAudio) audioCount++;
    if (hasImage) imageCount++;
    if (hasVideo) videoCount++;
  });

  const elAudio = document.getElementById("metric-audio-count");
  if (elAudio) elAudio.textContent = `${audioCount}/${total}`;

  const elImage = document.getElementById("metric-image-count");
  if (elImage) elImage.textContent = `${imageCount}/${total}`;

  const elVideo = document.getElementById("metric-video-count");
  if (elVideo) elVideo.textContent = `${videoCount}/${total}`;

  // Cálculo ponderado: Áudio 20%, Imagem 40%, Vídeo 40%
  const audioWeight = (audioCount / total) * 20;
  const imageWeight = (imageCount / total) * 40;
  const videoWeight = (videoCount / total) * 40;
  const totalPct = Math.round(audioWeight + imageWeight + videoWeight);

  const elPct = document.getElementById("metric-percent");
  if (elPct) elPct.textContent = `${totalPct}%`;

  const elBar = document.getElementById("cockpit-progress-fill");
  if (elBar) elBar.style.width = `${totalPct}%`;

  // Contadores para os chips de filtro
  const needImageCount = beats.filter(b => !(b.generated_image || (b.actor_image && !b.actor_image.includes("placeholder")))).length;
  const readyVideoCount = beats.filter(b => (b.generated_image || (b.actor_image && !b.actor_image.includes("placeholder"))) && !b.video_url).length;
  const completedCount = videoCount;

  const fAll = document.getElementById("filter-count-all");
  if (fAll) fAll.textContent = total;
  const fNeedImg = document.getElementById("filter-count-need-image");
  if (fNeedImg) fNeedImg.textContent = needImageCount;
  const fReadyVid = document.getElementById("filter-count-ready-video");
  if (fReadyVid) fReadyVid.textContent = readyVideoCount;
  const fDone = document.getElementById("filter-count-completed");
  if (fDone) fDone.textContent = completedCount;

  applyCurrentFilter();
}

function setShotsFilter(filterType, btnEl) {
  currentFilter = filterType;
  document.querySelectorAll(".filter-chip").forEach(el => el.classList.remove("active"));
  if (btnEl) {
    btnEl.classList.add("active");
  } else {
    const target = document.querySelector(`.filter-chip[data-filter="${filterType}"]`);
    if (target) target.classList.add("active");
  }
  applyCurrentFilter();
}

function applyCurrentFilter() {
  const cards = document.querySelectorAll(".shot-card");
  cards.forEach(card => {
    const status = card.dataset.status;
    if (currentFilter === "all") {
      card.style.display = "block";
    } else if (currentFilter === "need_image") {
      card.style.display = status === "need_image" ? "block" : "none";
    } else if (currentFilter === "ready_video") {
      card.style.display = status === "ready_video" ? "block" : "none";
    } else if (currentFilter === "completed") {
      card.style.display = status === "completed" ? "block" : "none";
    }
  });
}

function togglePromptDrawer(btnEl) {
  btnEl.classList.toggle("open");
  const content = btnEl.nextElementSibling;
  const arrow = btnEl.querySelector(".drawer-arrow");
  if (content) {
    if (content.style.display === "none" || !content.style.display) {
      content.style.display = "flex";
      if (arrow) arrow.textContent = "▲";
    } else {
      content.style.display = "none";
      if (arrow) arrow.textContent = "▼";
    }
  }
}

// ==========================================
// MOTOR DE PRÉ-VISUALIZAÇÃO CINEMATOGRÁFICA
// ==========================================
let previewCurrentIndex = 0;
let previewIsPlaying = false;
let previewAudioObj = null;
let previewTimer = null;

function openScenePreviewModal() {
  if (!currentSceneData || !currentSceneData.beats || currentSceneData.beats.length === 0) {
    showToast("Nenhuma cena carregada para pré-visualização.", "warn");
    return;
  }
  const modal = document.getElementById("scene-preview-modal");
  if (!modal) return;
  modal.style.display = "flex";
  previewCurrentIndex = 0;
  playPreviewShot(0);
}

function closeScenePreviewModal() {
  const modal = document.getElementById("scene-preview-modal");
  if (modal) modal.style.display = "none";
  if (previewAudioObj) {
    previewAudioObj.pause();
    previewAudioObj = null;
  }
  if (previewTimer) {
    clearTimeout(previewTimer);
    previewTimer = null;
  }
  const mediaContainer = document.getElementById("preview-media-container");
  if (mediaContainer) {
    const video = mediaContainer.querySelector("video");
    if (video) video.pause();
  }
  previewIsPlaying = false;
}

function playPreviewShot(index) {
  const beats = currentSceneData.beats || [];
  if (index < 0 || index >= beats.length) {
    closeScenePreviewModal();
    showToast("🎉 Prévia da cena concluída!", "success");
    return;
  }

  if (previewAudioObj) {
    previewAudioObj.pause();
    previewAudioObj = null;
  }
  if (previewTimer) {
    clearTimeout(previewTimer);
    previewTimer = null;
  }

  previewCurrentIndex = index;
  const beat = beats[index];

  const badge = document.getElementById("preview-shot-badge");
  if (badge) badge.textContent = `PLANO ${String(index + 1).padStart(2, "0")}/${String(beats.length).padStart(2, "0")} — ${beat.shot_id}`;

  const title = document.getElementById("preview-shot-title");
  if (title) title.textContent = beat.action_pt || "Ação do Plano";

  const subtitle = document.getElementById("preview-subtitle-overlay");
  if (subtitle) {
    if (beat.narration) {
      subtitle.style.display = "block";
      subtitle.innerHTML = `🎙️ <em>"${escapeHtml(beat.narration)}"</em>`;
    } else {
      subtitle.style.display = "none";
    }
  }

  const indicator = document.getElementById("preview-timeline-indicator");
  if (indicator) indicator.textContent = `Plano ${index + 1} de ${beats.length} • Duração: ~${beat.duration_s || 6}s`;

  const container = document.getElementById("preview-media-container");
  container.innerHTML = "";

  const audioUrl = beat.audio_file ? (beat.audio_file.startsWith('/api/') ? beat.audio_file : '/api/audio/' + beat.audio_file) : null;

  if (beat.video_url) {
    const video = document.createElement("video");
    video.src = beat.video_url;
    video.autoplay = true;
    video.controls = false;
    video.style.width = "100%";
    video.style.height = "100%";
    video.style.objectFit = "contain";
    video.onended = () => {
      if (previewIsPlaying) nextPreviewShot();
    };
    container.appendChild(video);
    video.play().catch(e => console.log("Video auto-play prevented:", e));
  } else {
    const img = document.createElement("img");
    img.src = beat.generated_image || beat.actor_image || "assets/placeholder.svg";
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.objectFit = "contain";
    container.appendChild(img);

    if (audioUrl) {
      previewAudioObj = new Audio(audioUrl);
      previewAudioObj.play().catch(e => console.log("Audio play error:", e));
      previewAudioObj.onended = () => {
        if (previewIsPlaying) nextPreviewShot();
      };
    } else {
      const durMs = (beat.duration_s || 6.0) * 1000;
      previewTimer = setTimeout(() => {
        if (previewIsPlaying && previewCurrentIndex === index) {
          nextPreviewShot();
        }
      }, durMs);
    }
  }

  previewIsPlaying = true;
  const playBtn = document.getElementById("btn-preview-play-pause");
  if (playBtn) playBtn.textContent = "⏸ Pausar";
}

function togglePreviewPlayPause() {
  const container = document.getElementById("preview-media-container");
  const video = container ? container.querySelector("video") : null;
  const playBtn = document.getElementById("btn-preview-play-pause");

  if (previewIsPlaying) {
    previewIsPlaying = false;
    if (video) video.pause();
    if (previewAudioObj) previewAudioObj.pause();
    if (previewTimer) {
      clearTimeout(previewTimer);
      previewTimer = null;
    }
    if (playBtn) playBtn.textContent = "▶ Continuar";
  } else {
    previewIsPlaying = true;
    if (video) video.play();
    if (previewAudioObj) previewAudioObj.play();
    if (!video && !previewAudioObj) {
      const beat = (currentSceneData.beats || [])[previewCurrentIndex];
      const durMs = (beat && beat.duration_s ? beat.duration_s : 6.0) * 1000;
      previewTimer = setTimeout(() => {
        if (previewIsPlaying) nextPreviewShot();
      }, durMs);
    }
    if (playBtn) playBtn.textContent = "⏸ Pausar";
  }
}

function nextPreviewShot() {
  const beats = currentSceneData.beats || [];
  if (previewCurrentIndex < beats.length - 1) {
    playPreviewShot(previewCurrentIndex + 1);
  } else {
    closeScenePreviewModal();
    showToast("🎬 Prévia da cena concluída!", "success");
  }
}

function prevPreviewShot() {
  if (previewCurrentIndex > 0) {
    playPreviewShot(previewCurrentIndex - 1);
  }
}

// ==========================================
// ABA 2: BÍBLIA VISUAL & ASSETS
// ==========================================
async function loadVisualBible() {
  try {
    const res = await fetch("/api/bible");
    const bible = await res.json();

    // Preserva o estado de abas que o usuário já estava navegando
    const preservedViews = {};
    document.querySelectorAll(".asset-card").forEach(c => {
      if (c.id && c.dataset.activeView) {
        preservedViews[c.id] = c.dataset.activeView;
      }
    });

    const isStylized = currentVisualStyle === "stylized";
    const styleKey = isStylized ? "stylized" : "realistic";
    const placeholderImg = "assets/placeholder.svg";

    // 1. Personagens
    const charGrid = document.getElementById("bible-characters-grid");
    charGrid.innerHTML = "";
    (bible.characters || []).forEach((char, idx) => {
      const cardId = `char-card-${idx}`;
      const activeView = preservedViews[cardId] || "p1";

      // Prompts estruturados ou legados
      const pRealistic = char.prompts_realistic || {};
      const pStylized = char.prompts_stylized || {};

      const p1Prompt = isStylized
        ? (pStylized.p1 || char.casting_prompt_stylized || char.casting_prompt_midjourney || "")
        : (pRealistic.p1 || char.casting_prompt_realistic || char.casting_prompt_midjourney || "");

      const msPrompt = isStylized
        ? (pStylized.modelsheet || char.modelsheet_prompt_stylized || p1Prompt)
        : (pRealistic.modelsheet || char.modelsheet_prompt_realistic || p1Prompt);

      const exPrompt = isStylized
        ? (pStylized.expressions || char.expressions_prompt_stylized || p1Prompt)
        : (pRealistic.expressions || char.expressions_prompt_realistic || p1Prompt);

      // Imagens do estilo atual
      const imgsObj = isStylized ? (char.images_stylized || {}) : (char.images_realistic || {});
      const p1Img = imgsObj.p1 || (isStylized ? char.image_primary_stylized : char.image_primary_realistic) || char.image_primary || placeholderImg;
      const msImg = imgsObj.modelsheet || (isStylized ? char.image_modelsheet_stylized : char.image_modelsheet_realistic) || char.image_modelsheet || placeholderImg;
      const exImg = imgsObj.expressions || (isStylized ? char.image_expressions_stylized : char.image_expressions_realistic) || char.image_expressions || placeholderImg;

      const hasP1 = p1Img && !p1Img.includes("placeholder");
      const hasMs = msImg && !msImg.includes("placeholder");
      const hasEx = exImg && !exImg.includes("placeholder");

      // Imagem e prompt atualmente exibidos no card
      let curImg = p1Img;
      let curPrompt = p1Prompt;
      let curTitle = `Pose 1 (Frontal)`;
      let curBtnLabel = "🎨 Gerar Pose 1 com FLUX";

      if (activeView === "modelsheet") {
        curImg = msImg;
        curPrompt = msPrompt;
        curTitle = `Model Sheet (4 Vistas)`;
        curBtnLabel = "🎨 Gerar Model Sheet com FLUX";
      } else if (activeView === "expressions") {
        curImg = exImg;
        curPrompt = exPrompt;
        curTitle = `Expressões Faciais`;
        curBtnLabel = "🎨 Gerar Expressões com FLUX";
      }

      const card = document.createElement("div");
      card.className = "asset-card";
      card.id = cardId;
      card.dataset.activeView = activeView;
      card.dataset.activeTag = char.tag;
      card.dataset.activeType = "character";
      card.dataset.imgP1 = p1Img;
      card.dataset.imgModelsheet = msImg;
      card.dataset.imgExpressions = exImg;
      card.dataset.promptP1 = p1Prompt;
      card.dataset.promptModelsheet = msPrompt;
      card.dataset.promptExpressions = exPrompt;

      card.innerHTML = `
        <div class="asset-card-media" onclick="openImageModal(document.getElementById('${cardId}-img').src, '${escapeForJs(char.name)} • ${activeView.toUpperCase()}')">
          <img id="${cardId}-img" src="${curImg}" alt="${char.name}" style="cursor:zoom-in;">
          <div class="asset-media-zoom-hint">🔍 Expandir 16:9</div>
        </div>
        <div class="asset-card-body">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="asset-tag">${char.tag}</span>
            <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}">${isStylized ? '🎨 Pixar 3D' : '🎥 Realista 35mm'}</span>
          </div>
          <h4 class="asset-title">${char.name}</h4>
          <p class="asset-desc">${char.physical_description}</p>

          <!-- Mini-Galeria das 3 Vistas -->
          <div class="modelsheet-nav">
            <div class="modelsheet-thumb-tab ${activeView === 'p1' ? 'active' : ''}" onclick="switchCharAssetView('${cardId}', 'p1', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasP1 ? 'ready' : 'pending'}" id="${cardId}-dot-p1"></span>
                <span>Pose 1</span>
              </div>
              <span class="thumb-tab-sub">Frontal 1:1</span>
            </div>
            <div class="modelsheet-thumb-tab ${activeView === 'modelsheet' ? 'active' : ''}" onclick="switchCharAssetView('${cardId}', 'modelsheet', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasMs ? 'ready' : 'pending'}" id="${cardId}-dot-modelsheet"></span>
                <span>Model Sheet</span>
              </div>
              <span class="thumb-tab-sub">4 Vistas 16:9</span>
            </div>
            <div class="modelsheet-thumb-tab ${activeView === 'expressions' ? 'active' : ''}" onclick="switchCharAssetView('${cardId}', 'expressions', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasEx ? 'ready' : 'pending'}" id="${cardId}-dot-expressions"></span>
                <span>Expressões</span>
              </div>
              <span class="thumb-tab-sub">Grade 2x2 16:9</span>
            </div>
          </div>

          <!-- Prompt Editável com Salvamento -->
          <div class="asset-prompt-container" id="${cardId}-prompt-container">
            <div class="asset-prompt-header">
              <span id="${cardId}-prompt-title">Prompt: ${curTitle}</span>
              <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}" style="font-size:10px; padding:2px 6px;">${isStylized ? '🎨 Pixar 3D' : '🎥 35mm'}</span>
            </div>
            <textarea id="${cardId}-prompt-textarea" class="asset-prompt-textarea" rows="3" spellcheck="false">${curPrompt}</textarea>
            <div class="prompt-action-bar">
              <button class="btn-prompt-copy" onclick="copyCharActivePrompt('${cardId}')">📋 Copiar</button>
              <button class="btn-prompt-save" onclick="saveCustomPrompt('character', '${char.tag}', '${cardId}')">💾 Salvar Alterações</button>
            </div>
          </div>

          <!-- Matriz de Ações de Geração -->
          <div class="asset-actions-matrix">
            <button id="${cardId}-btn-gen-single" class="asset-primary-gen-btn" onclick="generateBibleAsset('character', '${char.tag}', '${cardId}', this)">
              ${curBtnLabel}
            </button>
            <div class="asset-secondary-actions-row">
              <button id="${cardId}-btn-gen-pack" class="btn-action-pack" onclick="generateBiblePack('character', '${char.tag}', '${cardId}', this)">
                ⚡ Gerar Pacote (3 Vistas)
              </button>
              <button class="btn-action-upload" onclick="triggerBibleUpload('character', '${char.tag}', '${cardId}')">
                📁 Upload Imagem
              </button>
            </div>
          </div>
        </div>
      `;
      charGrid.appendChild(card);
    });

    // 2. Locações
    const locGrid = document.getElementById("bible-locations-grid");
    locGrid.innerHTML = "";
    (bible.locations || []).forEach((loc, idx) => {
      const locCardId = `loc-${loc.tag.replace(/[^a-zA-Z0-9]/g, '_')}`;
      const activeView = preservedViews[locCardId] || "master";

      const pRealistic = loc.prompts_realistic || {};
      const pStylized = loc.prompts_stylized || {};

      const masterPrompt = isStylized
        ? (pStylized.master || loc.casting_prompt_stylized || loc.casting_prompt_midjourney || "")
        : (pRealistic.master || loc.casting_prompt_realistic || loc.casting_prompt_midjourney || "");

      const setPrompt = isStylized
        ? (pStylized.set_design || loc.matte_prompt_stylized || masterPrompt)
        : (pRealistic.set_design || loc.matte_prompt_realistic || masterPrompt);

      const lightPrompt = isStylized
        ? (pStylized.lighting || loc.lighting_prompt_stylized || masterPrompt)
        : (pRealistic.lighting || loc.lighting_prompt_realistic || masterPrompt);

      const imgsObj = isStylized ? (loc.images_stylized || {}) : (loc.images_realistic || {});
      const masterImg = imgsObj.master || (isStylized ? loc.image_primary_stylized : loc.image_primary_realistic) || loc.image_primary || placeholderImg;
      const setImg = imgsObj.set_design || (isStylized ? loc.image_matte_stylized : loc.image_matte_realistic) || loc.image_matte_painting || placeholderImg;
      const lightImg = imgsObj.lighting || (isStylized ? loc.image_lighting_stylized : loc.image_lighting_realistic) || loc.image_lighting || placeholderImg;

      const hasMaster = masterImg && !masterImg.includes("placeholder");
      const hasSet = setImg && !setImg.includes("placeholder");
      const hasLight = lightImg && !lightImg.includes("placeholder");

      let curImg = masterImg;
      let curPrompt = masterPrompt;
      let curTitle = `Master Shot`;
      let curBtnLabel = "🎨 Gerar Master Shot com FLUX";

      if (activeView === "set_design") {
        curImg = setImg;
        curPrompt = setPrompt;
        curTitle = `Set Design (Turnaround)`;
        curBtnLabel = "🎨 Gerar Set Design com FLUX";
      } else if (activeView === "lighting") {
        curImg = lightImg;
        curPrompt = lightPrompt;
        curTitle = `Estudo de Luz`;
        curBtnLabel = "🎨 Gerar Estudo de Luz com FLUX";
      }

      const card = document.createElement("div");
      card.className = "asset-card";
      card.id = locCardId;
      card.dataset.activeView = activeView;
      card.dataset.activeTag = loc.tag;
      card.dataset.activeType = "location";
      card.dataset.imgMaster = masterImg;
      card.dataset.imgSetDesign = setImg;
      card.dataset.imgLighting = lightImg;
      card.dataset.promptMaster = masterPrompt;
      card.dataset.promptSetDesign = setPrompt;
      card.dataset.promptLighting = lightPrompt;

      card.innerHTML = `
        <div class="asset-card-media" onclick="openImageModal(document.getElementById('${locCardId}-img').src, '${escapeForJs(loc.name)} • ${activeView.toUpperCase()}')">
          <img id="${locCardId}-img" src="${curImg}" alt="${loc.name}" style="cursor:zoom-in;">
          <div class="asset-media-zoom-hint">🔍 Expandir 16:9</div>
        </div>
        <div class="asset-card-body">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="asset-tag">${loc.tag}</span>
            <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}">${isStylized ? '🎨 Pixar 3D' : '🎥 Realista 35mm'}</span>
          </div>
          <h4 class="asset-title">${loc.name}</h4>
          <p class="asset-desc">${loc.description}</p>

          <!-- Mini-Galeria de Cenário -->
          <div class="modelsheet-nav">
            <div class="modelsheet-thumb-tab ${activeView === 'master' ? 'active' : ''}" onclick="switchLocationAssetView('${locCardId}', 'master', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasMaster ? 'ready' : 'pending'}" id="${locCardId}-dot-master"></span>
                <span>Master Shot</span>
              </div>
              <span class="thumb-tab-sub">16:9 Cinema</span>
            </div>
            <div class="modelsheet-thumb-tab ${activeView === 'set_design' ? 'active' : ''}" onclick="switchLocationAssetView('${locCardId}', 'set_design', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasSet ? 'ready' : 'pending'}" id="${locCardId}-dot-set_design"></span>
                <span>Set Design</span>
              </div>
              <span class="thumb-tab-sub">Turnaround 16:9</span>
            </div>
            <div class="modelsheet-thumb-tab ${activeView === 'lighting' ? 'active' : ''}" onclick="switchLocationAssetView('${locCardId}', 'lighting', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasLight ? 'ready' : 'pending'}" id="${locCardId}-dot-lighting"></span>
                <span>Estudo de Luz</span>
              </div>
              <span class="thumb-tab-sub">Luz 16:9</span>
            </div>
          </div>

          <!-- Prompt Editável com Salvamento -->
          <div class="asset-prompt-container" id="${locCardId}-prompt-container">
            <div class="asset-prompt-header">
              <span id="${locCardId}-prompt-title">Prompt: ${curTitle}</span>
              <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}" style="font-size:10px; padding:2px 6px;">${isStylized ? '🎨 Pixar 3D' : '🎥 35mm'}</span>
            </div>
            <textarea id="${locCardId}-prompt-textarea" class="asset-prompt-textarea" rows="3" spellcheck="false">${curPrompt}</textarea>
            <div class="prompt-action-bar">
              <button class="btn-prompt-copy" onclick="copyCharActivePrompt('${locCardId}')">📋 Copiar</button>
              <button class="btn-prompt-save" onclick="saveCustomPrompt('location', '${loc.tag}', '${locCardId}')">💾 Salvar Alterações</button>
            </div>
          </div>

          <!-- Matriz de Ações de Geração -->
          <div class="asset-actions-matrix">
            <button id="${locCardId}-btn-gen-single" class="asset-primary-gen-btn" onclick="generateBibleAsset('location', '${loc.tag}', '${locCardId}', this)">
              ${curBtnLabel}
            </button>
            <div class="asset-secondary-actions-row">
              <button id="${locCardId}-btn-gen-pack" class="btn-action-pack" onclick="generateBiblePack('location', '${loc.tag}', '${locCardId}', this)">
                ⚡ Gerar Pacote (3 Vistas)
              </button>
              <button class="btn-action-upload" onclick="triggerBibleUpload('location', '${loc.tag}', '${locCardId}')">
                📁 Upload Imagem
              </button>
            </div>
          </div>
        </div>
      `;
      locGrid.appendChild(card);
    });

    // 3. Props
    const propsGrid = document.getElementById("bible-props-grid");
    propsGrid.innerHTML = "";
    (bible.props || []).forEach((prop, idx) => {
      const propCardId = `prop-${prop.tag.replace(/[^a-zA-Z0-9]/g, '_')}`;
      const activeView = preservedViews[propCardId] || "hero";

      const pRealistic = prop.prompts_realistic || {};
      const pStylized = prop.prompts_stylized || {};

      const heroPrompt = isStylized
        ? (pStylized.hero || prop.casting_prompt_stylized || prop.casting_prompt_midjourney || "")
        : (pRealistic.hero || prop.casting_prompt_realistic || prop.casting_prompt_midjourney || "");

      const propSheetPrompt = isStylized
        ? (pStylized.propsheet || prop.propsheet_prompt_stylized || heroPrompt)
        : (pRealistic.propsheet || prop.propsheet_prompt_realistic || heroPrompt);

      const imgsObj = isStylized ? (prop.images_stylized || {}) : (prop.images_realistic || {});
      const heroImg = imgsObj.hero || (isStylized ? prop.image_primary_stylized : prop.image_primary_realistic) || prop.image_primary || placeholderImg;
      const sheetImg = imgsObj.propsheet || (isStylized ? prop.image_propsheet_stylized : prop.image_propsheet_realistic) || prop.image_propsheet || placeholderImg;

      const hasHero = heroImg && !heroImg.includes("placeholder");
      const hasSheet = sheetImg && !sheetImg.includes("placeholder");

      let curImg = heroImg;
      let curPrompt = heroPrompt;
      let curTitle = `Hero Prop`;
      let curBtnLabel = "🎨 Gerar Hero Prop com FLUX";

      if (activeView === "propsheet") {
        curImg = sheetImg;
        curPrompt = propSheetPrompt;
        curTitle = `Prop Model Sheet`;
        curBtnLabel = "🎨 Gerar Prop Sheet com FLUX";
      }

      const card = document.createElement("div");
      card.className = "asset-card";
      card.id = propCardId;
      card.dataset.activeView = activeView;
      card.dataset.activeTag = prop.tag;
      card.dataset.activeType = "prop";
      card.dataset.imgHero = heroImg;
      card.dataset.imgPropsheet = sheetImg;
      card.dataset.promptHero = heroPrompt;
      card.dataset.promptPropsheet = propSheetPrompt;

      card.innerHTML = `
        <div class="asset-card-media" onclick="openImageModal(document.getElementById('${propCardId}-img').src, '${escapeForJs(prop.name)} • ${activeView.toUpperCase()}')">
          <img id="${propCardId}-img" src="${curImg}" alt="${prop.name}" style="cursor:zoom-in;">
          <div class="asset-media-zoom-hint">🔍 Expandir 16:9</div>
        </div>
        <div class="asset-card-body">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="asset-tag">${prop.tag}</span>
            <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}">${isStylized ? '🎨 Pixar 3D' : '🎥 Realista 35mm'}</span>
          </div>
          <h4 class="asset-title">${prop.name}</h4>
          <p class="asset-desc">${prop.description}</p>

          <!-- Mini-Galeria de Objeto -->
          <div class="modelsheet-nav">
            <div class="modelsheet-thumb-tab ${activeView === 'hero' ? 'active' : ''}" onclick="switchPropAssetView('${propCardId}', 'hero', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasHero ? 'ready' : 'pending'}" id="${propCardId}-dot-hero"></span>
                <span>Hero Prop</span>
              </div>
              <span class="thumb-tab-sub">Isolado 1:1</span>
            </div>
            <div class="modelsheet-thumb-tab ${activeView === 'propsheet' ? 'active' : ''}" onclick="switchPropAssetView('${propCardId}', 'propsheet', this)">
              <div class="thumb-tab-header">
                <span class="thumb-status-dot ${hasSheet ? 'ready' : 'pending'}" id="${propCardId}-dot-propsheet"></span>
                <span>Prop Sheet</span>
              </div>
              <span class="thumb-tab-sub">Vistas 16:9</span>
            </div>
          </div>

          <!-- Prompt Editável com Salvamento -->
          <div class="asset-prompt-container" id="${propCardId}-prompt-container">
            <div class="asset-prompt-header">
              <span id="${propCardId}-prompt-title">Prompt: ${curTitle}</span>
              <span class="badge ${isStylized ? 'badge-gold' : 'badge-accent'}" style="font-size:10px; padding:2px 6px;">${isStylized ? '🎨 Pixar 3D' : '🎥 35mm'}</span>
            </div>
            <textarea id="${propCardId}-prompt-textarea" class="asset-prompt-textarea" rows="3" spellcheck="false">${curPrompt}</textarea>
            <div class="prompt-action-bar">
              <button class="btn-prompt-copy" onclick="copyCharActivePrompt('${propCardId}')">📋 Copiar</button>
              <button class="btn-prompt-save" onclick="saveCustomPrompt('prop', '${prop.tag}', '${propCardId}')">💾 Salvar Alterações</button>
            </div>
          </div>

          <!-- Matriz de Ações de Geração -->
          <div class="asset-actions-matrix">
            <button id="${propCardId}-btn-gen-single" class="asset-primary-gen-btn" onclick="generateBibleAsset('prop', '${prop.tag}', '${propCardId}', this)">
              ${curBtnLabel}
            </button>
            <div class="asset-secondary-actions-row">
              <button id="${propCardId}-btn-gen-pack" class="btn-action-pack" onclick="generateBiblePack('prop', '${prop.tag}', '${propCardId}', this)">
                ⚡ Gerar Pacote (2 Vistas)
              </button>
              <button class="btn-action-upload" onclick="triggerBibleUpload('prop', '${prop.tag}', '${propCardId}')">
                📁 Upload Imagem
              </button>
            </div>
          </div>
        </div>
      `;
      propsGrid.appendChild(card);
    });
  } catch (err) {
    console.error("Erro ao carregar Bíblia Visual:", err);
  }
}

// ==========================================
// ABA 3: LIVRO & ROTEIRO — SPLIT-SCREEN (LEITURA & DIREÇÃO)
// ==========================================
async function loadBookText() {
  const chapterSelect = document.getElementById("select-book-chapter");
  const firstChapter = chapterSelect ? parseInt(chapterSelect.value, 10) || 1 : 1;
  await loadChapterDetail(firstChapter);
}

async function onBookChapterChange(chapterNum) {
  await loadChapterDetail(parseInt(chapterNum, 10));
}

async function loadChapterDetail(chapterNum) {
  const titleEl = document.getElementById("book-reader-title");
  const bodyEl = document.getElementById("book-reader-body");
  const badgeEl = document.getElementById("book-reader-status-badge");
  const wordCountEl = document.getElementById("book-reader-word-count");

  if (titleEl) titleEl.textContent = `Carregando Capítulo ${chapterNum}...`;
  if (bodyEl) bodyEl.innerHTML = `<div class="reader-placeholder"><span>⏳</span> Carregando texto integral do capítulo ${chapterNum}...</div>`;

  try {
    const res = await fetch(`/api/book-chapter?num=${chapterNum}`);
    if (!res.ok) throw new Error("Falha ao buscar capítulo");
    const data = await res.json();
    currentChapterData = data;

    renderBookReader(data);

    // Carrega a cena correspondente na coluna da direita
    const sceneId = data.scene_id || `SC_${String(chapterNum).padStart(2, "0")}`;
    await loadSceneForSplitShots(sceneId);

  } catch (err) {
    console.error("Erro ao carregar detalhes do capítulo:", err);
    if (bodyEl) bodyEl.innerHTML = `<div class="reader-placeholder" style="color:#ef4444;">Erro ao carregar capítulo: ${err.message}</div>`;
  }
}

function renderBookReader(data) {
  if (!data) return;
  const titleEl = document.getElementById("book-reader-title");
  const bodyEl = document.getElementById("book-reader-body");
  const badgeEl = document.getElementById("book-reader-status-badge");
  const wordCountEl = document.getElementById("book-reader-word-count");
  const btnPt = document.getElementById("btn-lang-pt");
  const btnOrig = document.getElementById("btn-lang-orig");

  if (titleEl) titleEl.textContent = data.title || `Capítulo ${data.number}`;
  if (wordCountEl) wordCountEl.textContent = `${data.word_count || 0} palavras`;

  // Atualiza estado dos botões de idioma
  if (btnPt && btnOrig) {
    btnPt.classList.toggle("active", currentReaderLang === "pt");
    btnOrig.classList.toggle("active", currentReaderLang === "orig");
  }

  // Atualiza badge de tradução
  if (badgeEl) {
    if (data.is_portuguese) {
      badgeEl.className = "badge badge-emerald";
      badgeEl.textContent = "🇧🇷 Original em Português";
    } else if (data.has_translation) {
      badgeEl.className = "badge badge-emerald";
      badgeEl.textContent = "✅ Traduzido p/ Português";
    } else {
      badgeEl.className = "badge badge-accent";
      badgeEl.textContent = "⏳ Inglês (Clique em 'Traduzir')";
    }
  }

  // Define qual texto exibir
  let textToDisplay = "";
  if (currentReaderLang === "pt") {
    textToDisplay = data.translated_text || data.original_text;
    if (!data.has_translation && !data.is_portuguese) {
      textToDisplay = `[Texto em Inglês — Clique em "Traduzir Capítulo" acima para gerar a versão em Português]\n\n` + data.original_text;
    }
  } else {
    textToDisplay = data.original_text;
  }

  if (bodyEl) {
    bodyEl.textContent = textToDisplay || "Texto vazio ou não encontrado.";
  }
}

function switchReaderLanguage(lang) {
  currentReaderLang = lang;
  if (currentChapterData) {
    renderBookReader(currentChapterData);
  }
}

async function triggerChapterTranslate() {
  const chapterSelect = document.getElementById("select-book-chapter");
  const providerSelect = document.getElementById("select-llm-provider");
  const btn = document.getElementById("btn-trigger-translate");

  const chapterNum = chapterSelect ? parseInt(chapterSelect.value, 10) : 1;
  const provider = providerSelect ? providerSelect.value : "gemini";

  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Traduzindo Cap. ${chapterNum}...`;
  }
  showToast(`Iniciando tradução literária do Cap. ${chapterNum} com IA (${provider.toUpperCase()})...`);

  try {
    const res = await fetch("/api/book-chapter/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chapter: chapterNum,
        provider: provider
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast(data.message || "Capítulo traduzido com sucesso!");
      currentReaderLang = "pt";
      await loadChapterDetail(chapterNum);
    } else {
      showToast("Erro na tradução: " + (data.message || "Falha na comunicação"));
    }
  } catch (err) {
    showToast("Erro de rede ao traduzir: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

async function loadSceneForSplitShots(sceneId) {
  const sceneTitleEl = document.getElementById("split-shots-scene-title");
  const statusBadgeEl = document.getElementById("split-shots-status-badge");
  const countEl = document.getElementById("split-shots-count");
  const listEl = document.getElementById("split-shots-list");

  try {
    const res = await fetch(`/api/scene/${sceneId}`);
    if (res.ok) {
      const data = await res.json();
      renderSplitShots(data);
    } else {
      // Cena ainda não existe
      if (sceneTitleEl) sceneTitleEl.textContent = `${sceneId} — Aguardando Decupagem`;
      if (statusBadgeEl) {
        statusBadgeEl.className = "badge badge-accent";
        statusBadgeEl.textContent = "⏳ Pendente";
      }
      if (countEl) countEl.textContent = "0 planos";
      if (listEl) {
        listEl.innerHTML = `
          <div class="split-shots-empty-state">
            <div class="empty-icon">🎬</div>
            <h4>Cena ${sceneId} ainda não decupada</h4>
            <p>Clique em <strong>"Decupar Cena (6s)"</strong> acima para a IA gerar os planos com ações em PT-BR, locuções neurais e prompts fotorrealistas.</p>
          </div>
        `;
      }
    }
  } catch (err) {
    console.error("Erro ao carregar planos da split-screen:", err);
  }
}

function renderSplitShots(sceneData) {
  const sceneTitleEl = document.getElementById("split-shots-scene-title");
  const statusBadgeEl = document.getElementById("split-shots-status-badge");
  const countEl = document.getElementById("split-shots-count");
  const listEl = document.getElementById("split-shots-list");

  if (!sceneData || !sceneData.beats) return;

  const beats = sceneData.beats;
  if (sceneTitleEl) sceneTitleEl.textContent = sceneData.title || sceneData.scene_id;
  if (statusBadgeEl) {
    statusBadgeEl.className = "badge badge-emerald";
    statusBadgeEl.textContent = "✅ Decupado (6s)";
  }
  if (countEl) countEl.textContent = `${beats.length} planos • ~${beats.length * 6}s`;

  if (!listEl) return;
  listEl.innerHTML = "";

  beats.forEach((beat, idx) => {
    const card = document.createElement("div");
    card.className = "split-shot-card";
    card.id = `split-card-${beat.shot_id}`;

    const audioUrl = beat.audio_file ? beat.audio_file : `/api/audio/${beat.shot_id}.mp3`;
    const heroImg = beat.generated_image || beat.actor_image || "";
    const imgPrompt = beat.image_prompt_en || beat.prompt_en || "";
    const vidPrompt = beat.video_prompt_en || beat.prompt_en || "";

    card.innerHTML = `
      <div class="split-shot-card-header">
        <div>
          <span class="split-shot-id">Plano ${String(idx + 1).padStart(2, "0")} • ${beat.shot_id}</span>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${beat.shot_type || 'Plano de 6s'}</div>
        </div>
        <span class="split-shot-lens">🎥 ${beat.lens_mm || 35}mm</span>
      </div>

      <!-- Caixa de Ação Dramática (PT-BR) -->
      <div class="split-shot-action-box">
        <strong>Ação Cênica:</strong> ${beat.action_pt || 'Sem descrição física.'}
      </div>

      <!-- Caixa de Locução com Player de Áudio -->
      <div class="split-shot-narration-box">
        <button class="split-shot-audio-btn" onclick="toggleAudio('${audioUrl}', this)" title="Reproduzir Locução">
          ▶
        </button>
        <div style="flex:1;">
          <div style="font-size:10px; text-transform:uppercase; font-weight:700; color:#34d399; letter-spacing:0.05em;">Locução Contínua (${beat.duration_s || 6}s):</div>
          <div>"${beat.narration || beat.action_pt || ''}"</div>
        </div>
      </div>

      <!-- Hero Thumbnail se gerada -->
      ${heroImg ? `
        <div style="position:relative; border-radius:6px; overflow:hidden; border:1px solid rgba(255,255,255,0.1); cursor:zoom-in;" onclick="openImageModal('${heroImg}', '${beat.shot_id}')">
          <img src="${heroImg}" alt="${beat.shot_id}" style="width:100%; height:140px; object-fit:cover; display:block;">
          <span style="position:absolute; bottom:6px; right:6px; background:rgba(0,0,0,0.7); font-size:10px; padding:2px 6px; border-radius:4px; color:#fff;">16:9 Cinema</span>
        </div>
      ` : ''}

      <!-- Ações Rápidas de Prompt (Copiar p/ ferramentas externas) -->
      <div class="split-shot-prompt-actions">
        <button class="btn-prompt-mini" onclick="copyQuickPrompt('${escapeForJs(imgPrompt)}')">
          📋 Copiar Imagem (FLUX/Midj.)
        </button>
        <button class="btn-prompt-mini" onclick="copyQuickPrompt('${escapeForJs(vidPrompt)}')">
          🎬 Copiar Vídeo (Kling/Runway)
        </button>
        <button class="btn-prompt-mini" style="color:var(--cyan-accent);" onclick="triggerShotUpload('${escapeForJs(beat.shot_id)}')">
          📁 Upload Imagem
        </button>
        <button class="btn-prompt-mini" style="color:#10b981; font-weight:700;" onclick="generateShotImage('${escapeForJs(beat.shot_id)}', '${escapeForJs(imgPrompt)}', this)">
          🎨 Gerar IA
        </button>
      </div>
    `;
    listEl.appendChild(card);
  });
}

function copyQuickPrompt(text) {
  if (!text) {
    showToast("Nenhum prompt disponível para copiar.");
    return;
  }
  copyText(text);
}

async function regenerateActiveSceneAudio() {
  if (!currentChapterData) return;
  const sceneId = currentChapterData.scene_id || "SC_01";
  showToast(`Sintetizando locuções neurais para ${sceneId}...`);
  try {
    const res = await fetch("/api/generate-audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_id: sceneId })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast("Áudios e tempos atualizados com sucesso!");
      await loadSceneForSplitShots(sceneId);
    } else {
      showToast("Erro ao gerar áudios: " + (data.message || "Falha"));
    }
  } catch (err) {
    showToast("Erro ao conectar com gerador de áudio.");
  }
}

async function exportTimelineFromBook() {
  if (!currentChapterData) return;
  const sceneId = currentChapterData.scene_id || "SC_01";
  showToast(`Gerando manifesto CapCut para ${sceneId}...`);
  try {
    const res = await fetch("/api/export-timeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_id: sceneId })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast("Manifesto CapCut pronto em 07_timeline_export!");
    } else {
      showToast("Erro ao exportar timeline.");
    }
  } catch (err) {
    showToast("Erro na exportação da timeline.");
  }
}

// ==========================================
// FUNÇÕES AUXILIARES E EVENTOS
// ==========================================
function toggleAudio(url, btn) {
  if (currentAudio && !currentAudio.paused) {
    currentAudio.pause();
    currentAudioButton.textContent = "▶";
    if (currentAudio.src.endsWith(url)) {
      return;
    }
  }

  currentAudio = new Audio(url);
  currentAudioButton = btn;
  btn.textContent = "⏸";

  currentAudio.play();
  currentAudio.onended = () => {
    btn.textContent = "▶";
  };
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("Texto copiado para a área de transferência!");
  }).catch(err => {
    console.error("Falha ao copiar:", err);
  });
}

function copyTag(tag) {
  if (!tag) return;
  const cleanTag = String(tag).trim();
  navigator.clipboard.writeText(cleanTag).then(() => {
    showToast(`🏷️ Tag "${cleanTag}" copiada! Pronta para usar no prompt.`);
  }).catch(err => {
    console.error("Falha ao copiar tag:", err);
    showToast(`Copiado: ${cleanTag}`);
  });
}

function showToast(msg) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2600);
}

function setupEventListeners() {
  document.getElementById("btn-re-audio").onclick = async () => {
    showToast("Regenerando locuções neurais...");
    try {
      const res = await fetch("/api/generate-audio", { method: "POST" });
      const data = await res.json();
      showToast(data.message || "Áudios gerados com sucesso!");
      if (currentSceneData) {
        loadSceneDetails(currentSceneData.scene_id);
      }
    } catch (err) {
      showToast("Erro ao regenerar áudios.");
    }
  };

  const batchVideoBtn = document.getElementById("btn-batch-video");
  if (batchVideoBtn) {
    batchVideoBtn.onclick = async () => {
      await generateSceneVideosBatch();
    };
  }

  document.getElementById("btn-export-timeline").onclick = async () => {
    showToast("Gerando manifesto e rascunho nativo do CapCut...");
    try {
      const res = await fetch("/api/export-timeline", { method: "POST" });
      const data = await res.json();
      showToast(data.message || "Rascunho CapCut pronto em 07_timeline_export!");
    } catch (err) {
      showToast("Erro ao exportar timeline.");
    }
  };
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeForJs(str) {
  if (!str) return "";
  return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, " ");
}

function getRoleBadge(role) {
  if (!role) return `<span class="role-badge action">🎬 Ação / Emissor</span>`;
  if (role.includes("action")) {
    return `<span class="role-badge action">🎬 Ação / Emissor (6s)</span>`;
  }
  if (role.includes("reaction")) {
    return `<span class="role-badge reaction">👀 Reação / Receptor (6s)</span>`;
  }
  if (role.includes("insert")) {
    return `<span class="role-badge insert">🍎 Detalhe / Insert (6s)</span>`;
  }
  return `<span class="role-badge action">🎬 ${role}</span>`;
}

function getEyelineBadge(eyeline) {
  if (!eyeline || eyeline === "center") {
    return `<span class="eyeline-badge">⊙ Foco Central</span>`;
  }
  if (eyeline === "screen_right") {
    return `<span class="eyeline-badge">➔ Olhar p/ Direita (180°)</span>`;
  }
  if (eyeline === "screen_left") {
    return `<span class="eyeline-badge">⬅ Olhar p/ Esquerda (180°)</span>`;
  }
  return `<span class="eyeline-badge">👁️ ${eyeline}</span>`;
}

async function loadBookChapters() {
  try {
    const res = await fetch("/api/book-chapters");
    const data = await res.json();
    const select = document.getElementById("select-book-chapter");
    if (!select) return;

    if (data.chapters && data.chapters.length > 0) {
      select.innerHTML = "";
      data.chapters.forEach(ch => {
        const opt = document.createElement("option");
        opt.value = ch.number;
        opt.textContent = ch.title;
        select.appendChild(opt);
      });
      // Carrega o primeiro capítulo na split-screen
      const firstNum = data.chapters[0].number;
      await loadChapterDetail(firstNum);
    }
    await loadBookChaptersStatus();
  } catch (err) {
    console.error("Erro ao carregar capítulos:", err);
  }
}

async function loadBookChaptersStatus() {
  try {
    const res = await fetch("/api/book-status");
    const data = await res.json();
    const container = document.getElementById("chapters-status-grid");
    if (!container) return;

    container.innerHTML = "";
    (data.chapters || []).forEach(ch => {
      const card = document.createElement("div");
      card.className = `chapter-status-card ${ch.status}`;

      const badgeHtml = ch.status === "completed"
        ? `<span class="badge badge-emerald">✅ Pronto (${ch.total_shots} planos • ${ch.duration_s}s)</span>`
        : `<span class="badge badge-subtle">⏳ Pendente</span>`;

      const actionBtn = ch.status === "completed"
        ? `<button class="btn btn-secondary btn-sm" onclick="openSceneFromBook('${ch.scene_id}')">🎬 Ver Planos</button>`
        : `<button class="btn btn-primary btn-sm" onclick="decoupageChapterDirectly(${ch.number})">⚡ Decupar</button>`;

      card.innerHTML = `
        <div class="chapter-card-header">
          <span class="chapter-card-num">CAPÍTULO ${ch.number}</span>
          ${badgeHtml}
        </div>
        <div class="chapter-card-title">${ch.title}</div>
        <div class="chapter-card-footer">
          ${actionBtn}
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Erro ao carregar status dos capítulos:", err);
  }
}

function openSceneFromBook(sceneId) {
  switchMainTab("shots");
  loadSceneDetails(sceneId);
}

async function decoupageChapterDirectly(chapterNum) {
  const select = document.getElementById("select-book-chapter");
  if (select) select.value = chapterNum;
  await triggerDecoupage();
}

// ==========================================
// GERAÇÃO DE IMAGENS COM IA (GOOGLE IMAGEN 3 / FLUX)
// ==========================================
async function generateShotImage(shotId, prompt, buttonEl) {
  if (!prompt) {
    showToast("Prompt inválido para geração.");
    return;
  }
  const originalHtml = buttonEl.innerHTML;
  buttonEl.disabled = true;
  buttonEl.innerHTML = `<span>⏳</span> Gerando...`;
  showToast(`Gerando imagem com IA para ${shotId}...`);

  try {
    const sceneId = currentSceneData ? (currentSceneData.scene_id || "SC_01") : "SC_01";
    const res = await fetch("/api/generate-image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt,
        asset_type: "shot",
        identifier: shotId,
        scene_id: sceneId,
        style: currentVisualStyle || "realistic"
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast("✨ Imagem gerada com sucesso!");
      const imgUrl = `${data.image_url}?t=${Date.now()}`;
      const heroBox = document.getElementById(`hero-box-${shotId}`);
      if (heroBox) {
        heroBox.className = "shot-cinematic-hero";
        heroBox.innerHTML = `
          <div class="shot-hero-media-wrapper" onclick="openImageModal('${imgUrl}', 'Plano: ${shotId}')">
            <img src="${imgUrl}" alt="Quadro 16:9 ${shotId}" class="shot-hero-img" id="hero-img-${shotId}">
            <div class="shot-hero-overlay">
              <div class="shot-hero-badges">
                <span class="badge-film-lens">🎥 35mm</span>
                <span class="badge-aspect">16:9 Cinema</span>
                <span class="badge-source">✨ Render Fotorrealista (IA)</span>
              </div>
              <div class="shot-hero-actions">
                <button class="btn-hero-zoom" onclick="event.stopPropagation(); openImageModal('${imgUrl}', 'Plano: ${shotId}')">🔍 Expandir 16:9</button>
              </div>
            </div>
          </div>
        `;
      }
    } else {
      showToast(`Erro ao gerar imagem: ${data.message || 'Falha no motor de IA'}`);
    }
  } catch (err) {
    console.error("Erro na geração de imagem:", err);
    showToast("Erro de conexão ao gerar imagem.");
  } finally {
    buttonEl.disabled = false;
    buttonEl.innerHTML = originalHtml;
  }
}

// ==========================================
// GERAÇÃO DE VÍDEO IA (IMAGE-TO-VIDEO COM CHAINING)
// ==========================================
async function generateShotVideo(shotId, buttonEl) {
  const originalHtml = buttonEl ? buttonEl.innerHTML : "";
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.innerHTML = `<span>⏳</span> Renderizando Vídeo IA...`;
  }

  const sceneId = currentSceneData ? (currentSceneData.scene_id || "SC_01") : "SC_01";
  showToast(`Iniciando renderização de vídeo I2V para ${shotId} no fal.ai...`);

  try {
    const res = await fetch("/api/generate-video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scene_id: sceneId,
        shot_id: shotId,
        use_chaining: true
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast(data.message || `✨ Vídeo ${shotId} renderizado com sucesso!`);
      await loadSceneDetails(sceneId);
    } else {
      showToast(`Erro ao gerar vídeo: ${data.message || 'Falha no renderizador'}`);
    }
  } catch (err) {
    console.error("Erro ao gerar vídeo:", err);
    showToast("Erro de conexão ao gerar vídeo IA.");
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.innerHTML = originalHtml;
    }
  }
}

async function generateSceneVideosBatch() {
  const btn = document.getElementById("btn-batch-video");
  const originalHtml = btn ? btn.innerHTML : "";
  const sceneId = currentSceneData ? (currentSceneData.scene_id || "SC_01") : "SC_01";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Iniciando fila de render...`;
  }
  showToast(`Enfileirando renderização em lote para a cena ${sceneId}...`);

  try {
    const res = await fetch("/api/generate-scene-videos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_id: sceneId })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      const taskId = data.task_id;
      showToast(`Fila iniciada! Acompanhando render dos vídeos...`);

      // Polling de acompanhamento
      const interval = setInterval(async () => {
        try {
          const tRes = await fetch(`/api/tasks`);
          if (!tRes.ok) return;
          const tData = await tRes.json();
          const task = (tData.tasks || []).find(t => t.task_id === taskId);
          if (task) {
            if (btn) {
              btn.innerHTML = `<span>⏳</span> ${task.progress}% - ${task.message || 'Renderizando...'}`;
            }
            if (task.status === "completed") {
              clearInterval(interval);
              showToast("🎉 Todos os vídeos da cena foram gerados com sucesso!");
              if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
              }
              await loadSceneDetails(sceneId);
            } else if (task.status === "failed") {
              clearInterval(interval);
              showToast("Falha na renderização em lote: " + (task.error || "Erro"));
              if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
              }
            }
          }
        } catch (e) {
          console.warn("Polling error:", e);
        }
      }, 4000);
    } else {
      showToast("Erro ao iniciar lote: " + (data.message || "Falha"));
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    }
  } catch (err) {
    showToast("Erro de rede ao iniciar render em lote.");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// ==========================================
// LIGHTBOX MODAL PARA IMAGENS 16:9
// ==========================================
function openImageModal(imgUrl, title) {
  const modal = document.getElementById("image-modal");
  const modalImg = document.getElementById("image-modal-img");
  const modalTitle = document.getElementById("image-modal-title");
  if (modal && modalImg) {
    modalImg.src = imgUrl;
    if (modalTitle) modalTitle.textContent = title || "Visualização Cinematográfica 16:9";
    modal.style.display = "flex";
  }
}

function closeImageModal() {
  const modal = document.getElementById("image-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

// ==========================================
// MÚLTIPLOS PROJETOS & LIVROS (NOVO PDF)
// ==========================================
async function loadProjectsList() {
  try {
    const res = await fetch("/api/projects");
    const data = await res.json();
    const select = document.getElementById("select-active-project");
    if (!select) return;

    select.innerHTML = "";
    (data.projects || []).forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.title;
      if (p.is_active) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Erro ao carregar projetos:", err);
  }
}

async function loadProjectConfig() {
  try {
    const res = await fetch("/api/project/config");
    const cfg = await res.json();
    currentVisualStyle = cfg.visual_style || "realistic";
    updateStyleButtonsUI(currentVisualStyle);
  } catch (err) {
    console.error("Erro ao carregar config do projeto:", err);
  }
}

async function switchProject(projectId) {
  showToast("Carregando história: " + projectId + "...");
  try {
    const res = await fetch("/api/projects/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId })
    });
    await res.json();
    await loadProjectConfig();
    await loadScenesList();
    await loadVisualBible();
    await loadBookText();
    await loadBookChapters();
    showToast("História carregada com sucesso!");
  } catch (err) {
    showToast("Erro ao alternar de história.");
  }
}

async function setVisualStyle(style) {
  currentVisualStyle = style;
  updateStyleButtonsUI(style);
  showToast("Estilo alterado para: " + (style === "stylized" ? "🎨 Animação 3D" : "🎥 Realista 35mm"));
  
  try {
    await fetch("/api/project/style", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visual_style: style })
    });
    // Atualiza Bíblia Visual para exibir os prompts do estilo selecionado
    await loadVisualBible();
  } catch (err) {
    console.error("Erro ao salvar estilo:", err);
  }
}

function updateStyleButtonsUI(style) {
  const btnReal = document.getElementById("btn-style-realistic");
  const btnStyl = document.getElementById("btn-style-stylized");
  if (!btnReal || !btnStyl) return;

  if (style === "stylized") {
    btnReal.classList.remove("active");
    btnStyl.classList.add("active");
  } else {
    btnReal.classList.add("active");
    btnStyl.classList.remove("active");
  }
}

// ==========================================
// MODAL DE EDIÇÃO RÁPIDA DE PLANO
// ==========================================
function openEditShotModal(shotId) {
  if (!currentSceneData || !currentSceneData.beats) return;
  const beat = currentSceneData.beats.find(b => b.shot_id === shotId);
  if (!beat) {
    showToast(`Plano ${shotId} não encontrado para edição.`);
    return;
  }

  document.getElementById("edit-shot-id-input").value = beat.shot_id;
  document.getElementById("edit-scene-id-input").value = currentSceneData.scene_id || "SC_01";
  document.getElementById("edit-shot-badge").textContent = `${currentSceneData.scene_id || "SC_01"} — ${beat.shot_id}`;
  
  document.getElementById("edit-shot-action").value = beat.action_pt || "";
  document.getElementById("edit-shot-narration").value = beat.narration || "";
  document.getElementById("edit-shot-img-prompt").value = beat.image_prompt_en || beat.prompt_en || "";
  document.getElementById("edit-shot-vid-prompt").value = beat.video_prompt_en || beat.prompt_en || "";

  const sliders = beat.kling_camera_controls || {};
  document.getElementById("edit-shot-zoom").value = sliders.zoom !== undefined ? sliders.zoom : 0.0;
  document.getElementById("edit-shot-horiz").value = sliders.horizontal !== undefined ? sliders.horizontal : 0.0;
  document.getElementById("edit-shot-vert").value = sliders.vertical !== undefined ? sliders.vertical : 0.0;
  document.getElementById("edit-shot-tilt").value = sliders.tilt !== undefined ? sliders.tilt : 0.0;

  const modal = document.getElementById("edit-shot-modal");
  modal.style.display = "flex";
  modal.classList.add("show");
}

function closeEditShotModal() {
  const modal = document.getElementById("edit-shot-modal");
  modal.style.display = "none";
  modal.classList.remove("show");
}

async function submitShotEdit() {
  const shotId = document.getElementById("edit-shot-id-input").value;
  const sceneId = document.getElementById("edit-scene-id-input").value;
  const btn = document.getElementById("btn-save-shot-edit");

  const actionPt = document.getElementById("edit-shot-action").value.trim();
  const narration = document.getElementById("edit-shot-narration").value.trim();
  const imgPrompt = document.getElementById("edit-shot-img-prompt").value.trim();
  const vidPrompt = document.getElementById("edit-shot-vid-prompt").value.trim();

  const zoom = parseFloat(document.getElementById("edit-shot-zoom").value) || 0.0;
  const horiz = parseFloat(document.getElementById("edit-shot-horiz").value) || 0.0;
  const vert = parseFloat(document.getElementById("edit-shot-vert").value) || 0.0;
  const tilt = parseFloat(document.getElementById("edit-shot-tilt").value) || 0.0;

  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Salvando alterações...`;
  }

  try {
    const res = await fetch("/api/shot/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scene_id: sceneId,
        shot_id: shotId,
        action_pt: actionPt,
        narration: narration,
        image_prompt_en: imgPrompt,
        video_prompt_en: vidPrompt,
        kling_camera_controls: {
          zoom: zoom,
          horizontal: horiz,
          vertical: vert,
          tilt: tilt,
          pan: 0.0,
          roll: 0.0
        }
      })
    });

    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast(`🎉 Plano ${shotId} atualizado com sucesso!`);
      closeEditShotModal();
      await loadSceneDetails(sceneId);
    } else {
      showToast(`Erro ao salvar plano: ${data.message || 'Falha na requisição'}`);
    }
  } catch (err) {
    showToast(`Erro de rede ao salvar: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

function openNewProjectModal() {
  document.getElementById("new-project-modal").classList.add("show");
  document.getElementById("pdf-drop-zone").onclick = () => {
    document.getElementById("pdf-file-input").click();
  };
}

function closeNewProjectModal() {
  document.getElementById("new-project-modal").classList.remove("show");
}

function handlePdfSelected(input) {
  if (input.files && input.files[0]) {
    selectedPdfFile = input.files[0];
    const lbl = document.getElementById("pdf-selected-name");
    lbl.textContent = `PDF Selecionado: ${selectedPdfFile.name} (${Math.round(selectedPdfFile.size / 1024)} KB)`;
    
    // Sugere nome do projeto
    const titleInput = document.getElementById("new-project-title");
    if (!titleInput.value) {
      titleInput.value = selectedPdfFile.name.replace(/\.pdf$/i, "");
    }
  }
}

async function submitNewProject() {
  const title = document.getElementById("new-project-title").value.trim();
  if (!title) {
    showToast("Por favor, digite o título da história.");
    return;
  }

  const radios = document.getElementsByName("modal-style");
  let chosenStyle = "realistic";
  for (const r of radios) {
    if (r.checked) chosenStyle = r.value;
  }

  showToast("Criando história e processando PDF...");
  closeNewProjectModal();

  const payload = {
    title: title,
    visual_style: chosenStyle
  };

  const executeCreate = async (finalPayload) => {
    try {
      const res = await fetch("/api/projects/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalPayload)
      });
      const data = await res.json();
      if (data.status === "ok") {
        showToast(data.message);
        await loadProjectsList();
        await switchProject(data.project_id);
      } else {
        showToast("Erro: " + data.message);
      }
    } catch (err) {
      showToast("Erro ao criar nova história.");
    }
  };

  if (selectedPdfFile) {
    const reader = new FileReader();
    reader.onload = async () => {
      payload.pdf_name = selectedPdfFile.name;
      payload.pdf_base64 = reader.result.split(",")[1];
      await executeCreate(payload);
    };
    reader.readAsDataURL(selectedPdfFile);
  } else {
    await executeCreate(payload);
  }
}

// ==========================================
// SUB-ABAS DE MODEL SHEETS (PERSONAGEM, CENÁRIO, PROP)
// ==========================================
function switchCharAssetView(cardId, viewType, tabEl) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.querySelectorAll(".modelsheet-thumb-tab").forEach(b => b.classList.remove("active"));
  if (tabEl) tabEl.classList.add("active");
  card.dataset.activeView = viewType;

  const isStylized = currentVisualStyle === "stylized";
  const styleLabel = isStylized ? "Pixar 3D" : "Realista 35mm";
  const imgEl = document.getElementById(`${cardId}-img`);
  const titleEl = document.getElementById(`${cardId}-prompt-title`);
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  const singleBtn = document.getElementById(`${cardId}-btn-gen-single`);

  let imgUrl = "";
  let promptText = "";
  let titleStr = "";
  let btnLabel = "";

  if (viewType === "p1") {
    imgUrl = card.dataset.imgP1;
    promptText = card.dataset.promptP1;
    titleStr = `Pose 1 (Frontal)`;
    btnLabel = "🎨 Gerar Pose 1 com FLUX";
  } else if (viewType === "modelsheet") {
    imgUrl = card.dataset.imgModelsheet;
    promptText = card.dataset.promptModelsheet;
    titleStr = `Model Sheet (4 Vistas)`;
    btnLabel = "🎨 Gerar Model Sheet com FLUX";
  } else if (viewType === "expressions") {
    imgUrl = card.dataset.imgExpressions;
    promptText = card.dataset.promptExpressions;
    titleStr = `Expressões Faciais`;
    btnLabel = "🎨 Gerar Expressões com FLUX";
  }

  if (imgEl && imgUrl) imgEl.src = imgUrl;
  if (titleEl) titleEl.textContent = `Prompt: ${titleStr}`;
  if (textareaEl) textareaEl.value = promptText || "";
  if (singleBtn) singleBtn.innerHTML = btnLabel;
}

function switchLocationAssetView(cardId, viewType, tabEl) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.querySelectorAll(".modelsheet-thumb-tab").forEach(b => b.classList.remove("active"));
  if (tabEl) tabEl.classList.add("active");
  card.dataset.activeView = viewType;

  const isStylized = currentVisualStyle === "stylized";
  const styleLabel = isStylized ? "Pixar 3D" : "Realista 35mm";
  const imgEl = document.getElementById(`${cardId}-img`);
  const titleEl = document.getElementById(`${cardId}-prompt-title`);
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  const singleBtn = document.getElementById(`${cardId}-btn-gen-single`);

  let imgUrl = "";
  let promptText = "";
  let titleStr = "";
  let btnLabel = "";

  if (viewType === "master") {
    imgUrl = card.dataset.imgMaster;
    promptText = card.dataset.promptMaster;
    titleStr = `Master Shot`;
    btnLabel = "🎨 Gerar Master Shot com FLUX";
  } else if (viewType === "set_design") {
    imgUrl = card.dataset.imgSetDesign;
    promptText = card.dataset.promptSetDesign;
    titleStr = `Set Design (Turnaround)`;
    btnLabel = "🎨 Gerar Set Design com FLUX";
  } else if (viewType === "lighting") {
    imgUrl = card.dataset.imgLighting;
    promptText = card.dataset.promptLighting;
    titleStr = `Estudo de Luz`;
    btnLabel = "🎨 Gerar Estudo de Luz com FLUX";
  }

  if (imgEl && imgUrl) imgEl.src = imgUrl;
  if (titleEl) titleEl.textContent = `Prompt: ${titleStr}`;
  if (textareaEl) textareaEl.value = promptText || "";
  if (singleBtn) singleBtn.innerHTML = btnLabel;
}

function switchPropAssetView(cardId, viewType, tabEl) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.querySelectorAll(".modelsheet-thumb-tab").forEach(b => b.classList.remove("active"));
  if (tabEl) tabEl.classList.add("active");
  card.dataset.activeView = viewType;

  const isStylized = currentVisualStyle === "stylized";
  const styleLabel = isStylized ? "Pixar 3D" : "Realista 35mm";
  const imgEl = document.getElementById(`${cardId}-img`);
  const titleEl = document.getElementById(`${cardId}-prompt-title`);
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  const singleBtn = document.getElementById(`${cardId}-btn-gen-single`);

  let imgUrl = "";
  let promptText = "";
  let titleStr = "";
  let btnLabel = "";

  if (viewType === "hero") {
    imgUrl = card.dataset.imgHero;
    promptText = card.dataset.promptHero;
    titleStr = `Hero Prop`;
    btnLabel = "🎨 Gerar Hero Prop com FLUX";
  } else if (viewType === "propsheet") {
    imgUrl = card.dataset.imgPropsheet;
    promptText = card.dataset.promptPropsheet;
    titleStr = `Prop Model Sheet`;
    btnLabel = "🎨 Gerar Prop Sheet com FLUX";
  }

  if (imgEl && imgUrl) imgEl.src = imgUrl;
  if (titleEl) titleEl.textContent = `Prompt: ${titleStr}`;
  if (textareaEl) textareaEl.value = promptText || "";
  if (singleBtn) singleBtn.innerHTML = btnLabel;
}

function copyCharActivePrompt(cardId) {
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  if (textareaEl) {
    copyText(textareaEl.value);
  }
}

async function saveCustomPrompt(entityType, tag, cardId) {
  const card = document.getElementById(cardId);
  if (!card) return;

  const activeView = card.dataset.activeView || (entityType === "character" ? "p1" : entityType === "location" ? "master" : "hero");
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  const promptVal = textareaEl ? textareaEl.value.trim() : "";

  if (!promptVal) {
    showToast("O prompt não pode ficar vazio.");
    return;
  }

  showToast(`Salvando alterações de prompt para ${tag} (${activeView.toUpperCase()})...`);
  try {
    const res = await fetch("/api/bible/update-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entity_type: entityType,
        tag: tag,
        view_type: activeView,
        prompt: promptVal,
        style: currentVisualStyle || "realistic"
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast("✨ " + (data.message || "Prompt salvo com sucesso no manifesto!"));
      // Atualiza dataset na memória
      if (activeView === "p1") card.dataset.promptP1 = promptVal;
      else if (activeView === "modelsheet") card.dataset.promptModelsheet = promptVal;
      else if (activeView === "expressions") card.dataset.promptExpressions = promptVal;
      else if (activeView === "master") card.dataset.promptMaster = promptVal;
      else if (activeView === "set_design") card.dataset.promptSetDesign = promptVal;
      else if (activeView === "lighting") card.dataset.promptLighting = promptVal;
      else if (activeView === "hero") card.dataset.promptHero = promptVal;
      else if (activeView === "propsheet") card.dataset.promptPropsheet = promptVal;
    } else {
      showToast("Erro ao salvar prompt: " + (data.message || "Falha"));
    }
  } catch (err) {
    console.error("Erro ao salvar prompt customizado:", err);
    showToast("Erro de rede ao salvar prompt.");
  }
}

// ==========================================
// UPLOAD DE IMAGENS EXTERNAS (MIDJOURNEY, COMFYUI, ETC.)
// ==========================================
function triggerShotUpload(shotId) {
  const fileInput = document.getElementById("shot-image-upload");
  if (!fileInput) return;

  fileInput.value = "";
  fileInput.onchange = async () => {
    if (!fileInput.files || !fileInput.files[0]) return;
    const file = fileInput.files[0];
    const reader = new FileReader();
    showToast(`Processando upload de imagem para o plano ${shotId}...`);

    reader.onload = async () => {
      try {
        const base64Data = reader.result;
        const sceneId = currentSceneData ? (currentSceneData.scene_id || "SC_01") : "SC_01";

        const res = await fetch("/api/upload-image", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_base64: base64Data,
            filename: file.name,
            target_type: "shot",
            identifier: shotId,
            scene_id: sceneId
          })
        });

        const data = await res.json();
        if (res.ok && data.status === "ok") {
          showToast(`✨ ${data.message || 'Imagem externa vinculada com sucesso!'}`);
          const imgUrl = `${data.image_url}?t=${Date.now()}`;

          // Atualiza dados na memória da cena
          if (currentSceneData && currentSceneData.beats) {
            const beat = currentSceneData.beats.find(b => b.shot_id === shotId);
            if (beat) {
              beat.generated_image = data.image_url;
              beat.actor_image = data.image_url;
            }
          }

          // Atualiza o Hero Box do plano na tela
          const heroBox = document.getElementById(`hero-box-${shotId}`);
          if (heroBox) {
            heroBox.className = "shot-cinematic-hero";
            heroBox.innerHTML = `
              <div class="shot-hero-media-wrapper" onclick="openImageModal('${imgUrl}', 'Plano: ${shotId}')">
                <img src="${imgUrl}" alt="Quadro 16:9 ${shotId}" class="shot-hero-img" id="hero-img-${shotId}">
                <div class="shot-hero-overlay">
                  <div class="shot-hero-badges">
                    <span class="badge-film-lens">📁 Imagem Externa</span>
                    <span class="badge-aspect">16:9 Cinema</span>
                    <span class="badge-source">✨ Midjourney / Render Externo</span>
                  </div>
                  <div class="shot-hero-actions">
                    <button class="btn-hero-zoom" onclick="event.stopPropagation(); openImageModal('${imgUrl}', 'Plano: ${shotId}')">🔍 Expandir 16:9</button>
                    <button class="btn-hero-zoom" style="background:rgba(255,255,255,0.12); border-color:rgba(255,255,255,0.3); font-weight:600;" onclick="event.stopPropagation(); triggerShotUpload('${escapeForJs(shotId)}')">📁 Trocar Imagem</button>
                  </div>
                </div>
              </div>
            `;
          }
        } else {
          showToast(`Erro ao salvar imagem: ${data.message || 'Falha no upload'}`);
        }
      } catch (err) {
        console.error("Erro no upload de imagem de plano:", err);
        showToast("Erro ao processar arquivo: " + err.message);
      }
    };
    reader.readAsDataURL(file);
  };
  fileInput.click();
}

function triggerBibleUpload(entityType, tag, cardId) {
  const card = document.getElementById(cardId);
  if (!card) return;
  const activeView = card.dataset.activeView || (entityType === "character" ? "p1" : entityType === "location" ? "master" : "hero");

  const fileInput = document.getElementById("bible-asset-upload");
  if (!fileInput) return;

  fileInput.value = "";
  fileInput.onchange = async () => {
    if (!fileInput.files || !fileInput.files[0]) return;
    const file = fileInput.files[0];
    const reader = new FileReader();
    showToast(`Processando upload de imagem para ${tag} (${activeView.toUpperCase()})...`);

    reader.onload = async () => {
      try {
        const base64Data = reader.result;
        const res = await fetch("/api/upload-image", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_base64: base64Data,
            filename: file.name,
            target_type: "bible",
            entity_type: entityType,
            tag: tag,
            view_type: activeView,
            style: currentVisualStyle || "realistic"
          })
        });

        const data = await res.json();
        if (res.ok && data.status === "ok") {
          showToast(`✨ ${data.message || 'Imagem externa salva na Bíblia Visual!'}`);
          const imgUrl = `${data.image_url}?t=${Date.now()}`;

          // Atualiza dados no card
          if (activeView === "p1") card.dataset.imgP1 = imgUrl;
          else if (activeView === "modelsheet") card.dataset.imgModelsheet = imgUrl;
          else if (activeView === "expressions") card.dataset.imgExpressions = imgUrl;
          else if (activeView === "master") card.dataset.imgMaster = imgUrl;
          else if (activeView === "set_design") card.dataset.imgSetDesign = imgUrl;
          else if (activeView === "lighting") card.dataset.imgLighting = imgUrl;
          else if (activeView === "hero") card.dataset.imgHero = imgUrl;
          else if (activeView === "propsheet") card.dataset.imgPropsheet = imgUrl;

          const imgEl = document.getElementById(`${cardId}-img`);
          if (imgEl) imgEl.src = imgUrl;

          // Atualiza status dot para ready
          const dot = document.getElementById(`${cardId}-dot-${activeView}`);
          if (dot) dot.className = "thumb-status-dot ready";
        } else {
          showToast(`Erro ao salvar na Bíblia Visual: ${data.message || 'Falha no upload'}`);
        }
      } catch (err) {
        console.error("Erro no upload para a Bíblia:", err);
        showToast("Erro ao processar imagem: " + err.message);
      }
    };
    reader.readAsDataURL(file);
  };
  fileInput.click();
}

// ==========================================
// GERAÇÃO DE MODEL SHEETS & ATIVOS COM FAL.AI (FLUX.3)
// ==========================================
async function generateBibleAsset(entityType, tag, cardId, btnEl) {
  const card = document.getElementById(cardId);
  if (!card) return;

  const activeView = card.dataset.activeView || (entityType === "character" ? "p1" : entityType === "location" ? "master" : "hero");
  const textareaEl = document.getElementById(`${cardId}-prompt-textarea`);
  const prompt = textareaEl ? textareaEl.value.trim() : "";
  if (!prompt) {
    showToast("Prompt inválido para geração.");
    return;
  }

  const btn = btnEl || document.getElementById(`${cardId}-btn-gen-single`);
  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Gerando no FLUX...`;
  }
  showToast(`Gerando ${activeView.toUpperCase()} para ${tag} via FLUX...`);

  try {
    const res = await fetch("/api/generate-sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entity_type: entityType,
        tag: tag,
        view_type: activeView,
        prompt: prompt,
        style: currentVisualStyle || "realistic"
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      const newUrl = `${data.image_url}?t=${Date.now()}`;
      showToast(`✨ ${activeView.toUpperCase()} gerado com sucesso via FLUX!`);

      // Atualiza a imagem na tela
      const imgEl = document.getElementById(`${cardId}-img`);
      if (imgEl) imgEl.src = newUrl;

      // Atualiza o cache do card in-place
      if (activeView === "p1") card.dataset.imgP1 = newUrl;
      else if (activeView === "modelsheet") card.dataset.imgModelsheet = newUrl;
      else if (activeView === "expressions") card.dataset.imgExpressions = newUrl;
      else if (activeView === "master") card.dataset.imgMaster = newUrl;
      else if (activeView === "set_design") card.dataset.imgSetDesign = newUrl;
      else if (activeView === "lighting") card.dataset.imgLighting = newUrl;
      else if (activeView === "hero") card.dataset.imgHero = newUrl;
      else if (activeView === "propsheet") card.dataset.imgPropsheet = newUrl;

      // Atualiza status dot para ready
      const dot = document.getElementById(`${cardId}-dot-${activeView}`);
      if (dot) dot.className = "thumb-status-dot ready";

    } else {
      showToast(`Erro ao gerar: ${data.message || 'Falha no motor FLUX'}`);
    }
  } catch (err) {
    console.error("Erro na geração de asset da Bíblia:", err);
    showToast("Erro de conexão ao gerar com fal.ai: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

async function generateBiblePack(entityType, tag, cardId, btnEl) {
  const card = document.getElementById(cardId);
  if (!card) return;

  const btn = btnEl || document.getElementById(`${cardId}-btn-gen-pack`);
  const originalHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Gerando Pacote (FLUX)...`;
  }
  showToast(`Iniciando geração em lote (Pacote Completo) para ${tag} no fal.ai...`);

  try {
    const res = await fetch("/api/generate-pack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entity_type: entityType,
        tag: tag,
        style: currentVisualStyle || "realistic"
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast(data.message || "✨ Pacote completo gerado com sucesso via FLUX!");
      const results = data.results || {};
      const t = Date.now();

      // Atualiza caches no card e status dots
      Object.keys(results).forEach(vKey => {
        const u = `${results[vKey]}?t=${t}`;
        if (vKey === "p1") card.dataset.imgP1 = u;
        else if (vKey === "modelsheet") card.dataset.imgModelsheet = u;
        else if (vKey === "expressions") card.dataset.imgExpressions = u;
        else if (vKey === "master") card.dataset.imgMaster = u;
        else if (vKey === "set_design") card.dataset.imgSetDesign = u;
        else if (vKey === "lighting") card.dataset.imgLighting = u;
        else if (vKey === "hero") card.dataset.imgHero = u;
        else if (vKey === "propsheet") card.dataset.imgPropsheet = u;

        const dot = document.getElementById(`${cardId}-dot-${vKey}`);
        if (dot) dot.className = "thumb-status-dot ready";
      });

      // Atualiza a imagem exibida atualmente se ela fez parte do pacote
      const activeView = card.dataset.activeView || "p1";
      const imgEl = document.getElementById(`${cardId}-img`);
      if (imgEl && results[activeView]) {
        imgEl.src = `${results[activeView]}?t=${t}`;
      }
    } else {
      showToast(`Erro ao gerar pacote: ${data.message || 'Falha no FLUX'}`);
    }
  } catch (err) {
    console.error("Erro na geração de pacote:", err);
    showToast("Erro de rede ao gerar pacote: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

// ==========================================
// DECUPAGEM CINEMATOGRÁFICA AUTÔNOMA COM IA
// ==========================================
async function triggerDecoupage() {
  const chapterSelect = document.getElementById("select-book-chapter");
  const providerSelect = document.getElementById("select-llm-provider");
  const btn = document.getElementById("btn-trigger-decoupage");

  const chapterNum = chapterSelect ? parseInt(chapterSelect.value, 10) : 1;
  const provider = providerSelect ? providerSelect.value : "gemini";

  const originalBtnHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Decupando Capítulo ${chapterNum} com IA (${provider.toUpperCase()})...`;
  }

  showToast(`Iniciando Decupagem do Cap. ${chapterNum} via ${provider.toUpperCase()}... Aplicando smixs + 180° + 6s.`);

  try {
    const res = await fetch("/api/decoupage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chapter: chapterNum,
        provider: provider
      })
    });

    const data = await res.json();
    if (res.ok && data.status === "ok") {
      showToast(data.message || `Capítulo ${chapterNum} decupado com sucesso!`);
      const targetSceneId = data.scene_id || (chapterNum === 1 ? "SC_01" : `SC_${String(chapterNum).padStart(2, "0")}`);
      
      // Atualiza lista de cenas e status dos capítulos
      await loadScenesList();
      await loadBookChaptersStatus();
      
      // Atualiza a coluna de planos na tela split-screen
      await loadSceneForSplitShots(targetSceneId);
      
      // Se estiver na aba shots, carrega os detalhes lá também
      if (currentSceneData && currentSceneData.scene_id === targetSceneId) {
        await loadSceneDetails(targetSceneId);
      }
    } else {
      showToast("Erro na decupagem: " + (data.message || "Falha na comunicação"));
    }
  } catch (err) {
    showToast("Erro de rede ao decupar com IA: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalBtnHtml;
    }
  }
}
