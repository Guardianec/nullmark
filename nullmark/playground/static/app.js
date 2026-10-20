"use strict";
const $ = id => document.getElementById(id);
let result = null,
  selectedSide = "marked",
  selectedIndex = 0;
let installedModels = [];
const num = id => Number($(id).value);
const fmt = value => value == null ? "—" : Number(value).toFixed(3);

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function status(message, type = "") {
  $("status").textContent = message;
  $("status").className = `status ${type}`;
}

function settings() {
  return {
    model: $("model").value,
    ollama_model: $("model").value === "ollama" ? $("ollama-model").value : null,
    ollama_digest: $("model").value === "ollama" ? installedModels.find(m => m.name === $("ollama-model").value)?.digest ?? null : null,
    offload: $("offload").value,
    context_length: num("context-length"),
    scheme: $("scheme").value,
    device: $("device").value,
    prompt: $("prompt").value,
    seed: num("seed"),
    key_index: num("key-index"),
    max_new_tokens: num("length"),
    temperature: num("temperature"),
    top_k: num("top-k"),
    top_p: num("top-p"),
    paired: $("paired").checked,
    kgw: {
      greenlist_ratio: num("ratio"),
      bias: num("bias"),
      context_width: num("context"),
      threshold: num("kgw-threshold")
    },
    synthid: {
      ngram_len: num("ngram"),
      depth: num("depth"),
      context_history_size: num("history"),
      threshold: num("synthid-threshold")
    }
  };
}

function updateControls() {
  const scheme = $("scheme").value;
  $("kgw-settings").hidden = scheme !== "kgw";
  $("synthid-settings").hidden = scheme !== "synthid";
  $("key-settings").hidden = scheme === "none";
  $("paired").disabled = scheme === "none";
  const local = $("model").value === "ollama";
  $("ollama-settings").hidden = !local;
  $("device").disabled = local;
  $("device").hidden = local;
  $("offload").hidden = !local;
  $("offload").disabled = !local;
  $("device-label").htmlFor = local ? "offload" : "device";
  $("device-label").textContent = local ? "GGUF offload" : "Device";
  $("model-note").textContent = local ? "High-quality local generation. Direct GGUF inference with per-token watermark control; Ollama discovers weights only." : $("model").value === "builtin-tiny" ? "Fast, offline random-weight model. Synthetic word sequences; software demonstration only." : "Reproducible small reference model. First use may download pinned GPT-2 weights; slower on CPU.";
}
$("scheme").addEventListener("change", updateControls);
$("model").addEventListener("change", () => {
  updateControls();
  if ($("model").value === "ollama" && !installedModels.length) refreshModels();
});

function localModelStatus() {
  const model = installedModels.find(m => m.name === $("ollama-model").value);
  if (model) $("ollama-status").textContent = `${model.parameter_size} · ${model.quantization} · ${(model.size/1e9).toFixed(1)} GB installed. Direct GGUF; loads on Generate.`;
}
async function refreshModels() {
  $("refresh-models").disabled = true;
  $("ollama-status").textContent = "Checking installed models on localhost…";
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    installedModels = data.models || [];
    const previous = $("ollama-model").value;
    $("ollama-model").replaceChildren();
    const choose = node("option", "Choose an installed model");
    choose.value = "";
    $("ollama-model").append(choose);
    installedModels.forEach(model => {
      const option = node("option", `${model.name}${model.supported ? "":" · unsupported"}`);
      option.value = model.name;
      option.disabled = !model.supported;
      $("ollama-model").append(option);
    });
    if (!installedModels.length) $("ollama-model").append(node("option", "No local models available"));
    if (installedModels.some(m => m.name === previous && m.supported)) $("ollama-model").value = previous;
    $("ollama-status").textContent = data.status || "Local model discovery unavailable.";
    localModelStatus();
  } catch (error) {
    $("ollama-status").textContent = "Local discovery failed. Start Ollama and refresh.";
  } finally {
    $("refresh-models").disabled = false;
  }
}
$("refresh-models").addEventListener("click", refreshModels);
$("ollama-model").addEventListener("change", localModelStatus);
async function post(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The local server could not complete this request.");
  return data;
}
$("fresh").addEventListener("click", async () => {
  try {
    await post("/api/key", {});
    $("key-note").textContent = "Fresh hidden configuration created. Previous results retain their original key context.";
    status("Fresh hidden key ready for the next generation.");
  } catch (error) {
    status(error.message, "error");
  }
});
$("settings").addEventListener("submit", async event => {
  event.preventDefault();
  if (!$("settings").reportValidity()) return;
  const controls = [...document.querySelectorAll("#settings input, #settings select, #settings button, #prompt")];
  const payload = settings();
  if (payload.model === "ollama" && !installedModels.some(m => m.name === payload.ollama_model && m.supported)) {
    status("Select an installed local GGUF model before generating.", "error");
    return;
  }
  controls.forEach(el => el.disabled = true);
  $("generate").textContent = "Generating…";
  status("Loading model / generating locally… Large GGUF models may take a while to load.", "busy");
  $("results").setAttribute("aria-busy", "true");
  try {
    result = await post("/api/generate", payload);
    selectedSide = "marked";
    selectedIndex = 0;
    render();
    const s = result.model.sampling;
    status(`Complete · ${result.model.name} · ${result.model.backend} / ${result.model.device} · seed ${result.seed} · ${result.marked.token_count} tokens · T ${s.temperature} / k ${s.top_k} / p ${s.top_p}${result.key_ref ? " · key ref " + result.key_ref.slice(0,12) : ""}`);
  } catch (error) {
    status(error.message || "Connection lost. Check the local server terminal.", "error");
  } finally {
    controls.forEach(el => el.disabled = false);
    $("generate").replaceChildren(document.createTextNode("Generate continuation "), node("span", "↗"));
    $("results").removeAttribute("aria-busy");
    updateControls();
  }
});

function sampleCard(sample, side) {
  const article = node("article", null, "sample"),
    head = node("div", null, "sample-head");
  head.append(node("h3", side === "plain" ? "Plain control" : result.scheme === "none" ? "Plain generation" : "Watermarked"), node("span", side === "plain" ? "NO BIAS" : result.scheme.toUpperCase()));
  article.append(head);
  const text = node("div", null, "token-text");
  text.setAttribute("aria-label", `${side} generated tokens`);
  sample.tokens.forEach((token, index) => {
    const kind = token.scored && !token.special ? token.kgw ? token.kgw.green ? "green" : "red" : token.synthid ? "synthid" : "" : "";
    const b = node("button", token.token_text, "token " + kind);
    b.type = "button";
    b.dataset.side = side;
    b.dataset.index = index;
    b.setAttribute("aria-label", `Token ${index+1}: ${token.token_text}; ${token.scored ? token.kgw ? token.kgw.green ? "green":"red" : "g-values available" : token.reason}`);
    b.title = b.getAttribute("aria-label");
    if (index === result.first_divergence) b.classList.add("divergence");
    b.addEventListener("click", () => select(side, index));
    text.append(b);
    if (result.model.name === "builtin-tiny") text.append(document.createTextNode(" "));
  });
  article.append(text);
  const exact = node("details", null, "exact-text");
  exact.append(node("summary", "Exact decoded text"), node("pre", sample.text));
  article.append(exact);
  const d = sample.detection,
    stats = node("div", null, "stats");
  [
    ["Tokens", sample.token_count],
    [d ? d.statistic === "mean_g" ? "Mean-g" : "z-score" : "Score", fmt(d?.score)],
    ["Threshold", fmt(d?.threshold)]
  ].forEach(([label, value]) => {
    const stat = node("div", null, "stat");
    stat.append(node("span", label), node("strong", value));
    stats.append(stat);
  });
  article.append(stats);
  let decision = "No watermark detector selected.";
  if (d) decision = d.status === "insufficient_text" ? "Not enough scored tokens for detection. Generate a longer continuation." : `${d.prediction ? "Detected":"Not detected"} · ${d.tokens_scored} tokens scored${d.p_value != null ? " · approximate p = "+d.p_value.toExponential(2):" · uncalibrated mean-g"}`;
  if (d) decision = `${result.scheme === "kgw" ? "KGW" : "SynthID mean-g"} · ${decision}`;
  article.append(node("div", decision, "decision"));
  return article;
}

function render() {
  $("outputs").replaceChildren();
  $("outputs").classList.toggle("single", !result.plain);
  if (result.plain) $("outputs").append(sampleCard(result.plain, "plain"));
  $("outputs").append(sampleCard(result.marked, "marked"));
  $("legend").replaceChildren();
  const legend = result.scheme === "kgw" ? [
    ["G · green", "green-dot"],
    ["R · red", "red-dot"],
    ["— · unscored", ""]
  ] : result.scheme === "synthid" ? [
    ["● / ○ · depth g-values", ""],
    ["— · masked / context", ""]
  ] : [
    ["— · plain tokens", ""]
  ];
  legend.forEach(([text, cls]) => $("legend").append(node("span", text, cls)));
  $("comparison").textContent = result.plain ? (result.first_divergence == null ? "Identical token streams in this sample. " : `First divergence: token ${result.first_divergence+1}. `) + "Same prompt, model and sampling seed. Later token positions are not guaranteed to align. A watermark biases sampling; it inserts no visible symbols." : "Select a token to inspect the actual generation context. Watermarks bias sampling; they insert no visible symbols.";
  $("detector-note").textContent = (result.scheme === "synthid" ? "SynthID mean-g is uncalibrated. This threshold does not establish a statistical false-positive rate. " : result.scheme === "kgw" ? "KGW uses the pinned HF n-gram scorer; p-values use a normal approximation, without empirical calibration. " : "No detector selected. ") + "Trace: retokenized continuation only, excluding prompt. Detection is never proof of authorship.";
  $("chart-label").textContent = result.scheme === "none" ? "NO DETECTOR" : result.scheme === "synthid" ? "CUMULATIVE MEAN-G" : "CUMULATIVE Z-SCORE";
  document.querySelector(".chart-key").hidden = result.scheme === "none";
  chart();
  select("marked", 0);
}

function select(side, index) {
  selectedSide = side;
  const sample = result?.[side];
  if (!sample?.tokens.length) return;
  selectedIndex = Math.max(0, Math.min(index, sample.tokens.length - 1));
  const t = sample.tokens[selectedIndex];
  document.querySelectorAll(".token").forEach(el => {
    const selected = el.dataset.side === side && Number(el.dataset.index) === selectedIndex;
    el.classList.toggle("selected", selected);
    el.setAttribute("aria-pressed", String(selected));
  });
  document.querySelectorAll(".sample").forEach(el => el.classList.toggle("active", Boolean(el.querySelector(".selected"))));
  $("position").textContent = `${side === "plain" || result.scheme === "none" ? "Plain":"Marked"} · ${selectedIndex+1} / ${sample.tokens.length}`;
  $("prev").disabled = selectedIndex === 0;
  $("next").disabled = selectedIndex === sample.tokens.length - 1;
  const box = $("inspection");
  box.className = "";
  box.replaceChildren(node("p", JSON.stringify(t.token_text), "selected-token"));
  const dl = node("dl");
  const entries = [
    ["Position / ID", `${t.index+1} / ${t.token_id}`],
    ["Context", t.context_text ? JSON.stringify(t.context_text) : "—"],
    ["Context IDs", t.context.join(", ") || "—"],
    ["State", t.special ? "Special token (neutral)" : t.scored ? t.kgw ? t.kgw.green ? "G · green" : "R · red" : "Scored" : t.reason]
  ];
  const p = result.public_parameters;
  if (result.scheme === "kgw") entries.push(["Parameters", `γ ${p.greenlist_ratio} · bias ${p.bias} · context ${p.context_width}`]);
  if (result.scheme === "synthid") entries.push(["Parameters", `n ${p.ngram_len} · depth ${p.depth} · history ${p.context_history_size}`]);
  if (t.kgw) entries.push(["Context trace z", fmt(t.kgw.cumulative_z)]);
  if (t.synthid) entries.push(["Token mean-g", fmt(t.synthid.mean_g)], ["Cumulative mean-g", fmt(t.synthid.cumulative_mean_g)]);
  entries.forEach(([k, v]) => dl.append(node("dt", k), node("dd", v)));
  box.append(dl);
  if (t.synthid) {
    const depths = node("div", null, "g-values");
    t.synthid.g_values.forEach((g, i) => {
      const cell = node("span", `${i+1} ${g ? "●":"○"}`, "g-value" + (g ? " on" : ""));
      cell.title = `Depth ${i+1}: g = ${g}`;
      depths.append(cell);
    });
    box.append(depths);
  }
  box.append(node("p", `Generation-token context trace; the chart uses the detector's retokenized input. ${sample.roundtrip_exact ? "Token round-trip is exact." : "Decoded text retokenizes differently; detector positions may differ."} Logits and probabilities are not recorded.`, "inspection-note"));
}
$("prev").addEventListener("click", () => select(selectedSide, selectedIndex - 1));
$("next").addEventListener("click", () => select(selectedSide, selectedIndex + 1));
const NS = "http://www.w3.org/2000/svg";

function svgNode(tag, attrs, text) {
  const el = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  if (text != null) el.textContent = text;
  return el;
}

function chart() {
  const box = $("chart");
  box.replaceChildren();
  const samples = [result.marked, result.plain].filter(Boolean);
  const get = t => t.kgw?.cumulative_z ?? t.synthid?.cumulative_mean_g ?? null;
  const values = samples.flatMap(s => s.detector_tokens.map(get).filter(v => v != null));
  if (!values.length) {
    box.append(node("p", result.scheme === "none" ? "No detector selected." : "Not enough scored tokens. Generate a longer continuation.", "chart-empty"));
    return;
  }
  const threshold = result.marked.detection.threshold;
  let lo = result.scheme === "synthid" ? 0 : Math.min(0, ...values) - .5,
    hi = result.scheme === "synthid" ? 1 : Math.max(threshold, ...values) + 1;
  const W = 540,
    H = 200,
    L = 42,
    R = 18,
    T = 18,
    B = 34,
    max = Math.max(...samples.map(s => s.detector_tokens.length));
  const x = i => L + i / Math.max(1, max - 1) * (W - L - R),
    y = v => T + (hi - v) / (hi - lo) * (H - T - B);
  const svg = svgNode("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": `Cumulative ${result.scheme === "kgw" ? "KGW z-score":"SynthID mean-g"} over continuation tokens; threshold ${threshold}. Numeric scores are shown in each sample panel.`
  });
  svg.append(svgNode("title", {}, "Cumulative detector evidence"));
  for (let i = 0; i < 4; i++) {
    const v = lo + (hi - lo) * i / 3;
    svg.append(svgNode("line", {
      x1: L,
      x2: W - R,
      y1: y(v),
      y2: y(v),
      stroke: "#e3e8e1"
    }), svgNode("text", {
      x: L - 7,
      y: y(v) + 3,
      "text-anchor": "end"
    }, v.toFixed(1)));
  }
  svg.append(svgNode("line", {
    x1: L,
    x2: W - R,
    y1: y(threshold),
    y2: y(threshold),
    stroke: "#a16c3b",
    "stroke-dasharray": "4 4"
  }), svgNode("text", {
    x: W - R,
    y: y(threshold) - 5,
    "text-anchor": "end"
  }, `threshold ${threshold}`));
  samples.forEach((s, i) => {
    const pts = s.detector_tokens.map((t, j) => get(t) == null ? null : `${x(j)},${y(get(t))}`).filter(Boolean);
    svg.append(svgNode("polyline", {
      points: pts.join(" "),
      fill: "none",
      stroke: i ? "#87968c" : "#146957",
      "stroke-width": i ? 1.6 : 2,
      "stroke-dasharray": i ? "4 3" : "none"
    }));
  });
  svg.append(svgNode("text", {
    x: L,
    y: H - 14
  }, "1"), svgNode("text", {
    x: W - R,
    y: H - 14,
    "text-anchor": "end"
  }, String(max)), svgNode("text", {
    x: W / 2,
    y: H - 4,
    "text-anchor": "middle"
  }, "continuation token position"));
  box.append(svg);
}
updateControls();
