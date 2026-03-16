(function () {
  const API_BASE = "";

  let currentJobId = null;
  let selectedFile = null;

  const el = (id) => document.getElementById(id);
  const setStatus = (id, text, className = "") => {
    const s = el(id);
    if (!s) return;
    s.textContent = text;
    s.className = "status " + className;
  };
  const setLoading = (id) => setStatus(id, "Loading…", "loading");
  const setError = (id, msg) => setStatus(id, msg || "Error", "error");
  const setSuccess = (id, msg) => setStatus(id, msg || "Done", "success");
  const clearStatus = (id) => setStatus(id, "");

  const uploadZone = el("uploadZone");
  const fileInput = el("fileInput");
  const browseLink = el("browseLink");
  const uploadBtn = el("uploadBtn");
  const uploadStatus = el("uploadStatus");
  const uploadProgressFill = el("uploadProgressFill");
  const uploadProgressText = el("uploadProgressText");
  const jobIdLine = el("jobIdLine");
  const jobMetaLine = el("jobMetaLine");
  const subject = el("subject");
  const className = el("className");
  const term = el("term");
  const uploadedBy = el("uploadedBy");
  const processBtn = el("processBtn");
  const processStatus = el("processStatus");
  const processProgressText = el("processProgressText");
  const processProgressFill = el("processProgressFill");
  const textChunk = el("textChunk");
  const generateFromTextBtn = el("generateFromTextBtn");
  const generateTextStatus = el("generateTextStatus");
  const generateFromJobBtn = el("generateFromJobBtn");
  const generateJobStatus = el("generateJobStatus");
  const refreshQuestionsBtn = el("refreshQuestionsBtn");
  const exportDocxLink = el("exportDocxLink");
  const exportPdfLink = el("exportPdfLink");
  const questionsText = el("questionsText");
  const questionsEmpty = el("questionsEmpty");
  const systemTime = el("systemTime");

  if (browseLink) browseLink.addEventListener("click", () => fileInput && fileInput.click());
  if (fileInput) fileInput.addEventListener("change", (e) => { selectFile(e.target.files); });
  if (uploadZone) {
    uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
    uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
    uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
      selectFile(e.dataTransfer.files);
    });
  }

  function hasUploadMeta() {
    return !!(subject && subject.value && className && className.value && term && term.value && uploadedBy && uploadedBy.value.trim());
  }

  function updateUploadButtonState() {
    if (!uploadBtn) return;
    uploadBtn.disabled = !(selectedFile && hasUploadMeta());
  }

  [subject, className, term, uploadedBy].forEach((node) => {
    if (node) node.addEventListener("change", updateUploadButtonState);
    if (node) node.addEventListener("input", updateUploadButtonState);
  });

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let idx = 0;
    while (size >= 1024 && idx < units.length - 1) {
      size /= 1024;
      idx += 1;
    }
    return `${size.toFixed(idx === 0 ? 0 : 2)} ${units[idx]}`;
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const normalized = value.endsWith("Z") || value.includes("+") ? value : value + "Z";
    const d = new Date(normalized);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString(undefined, { hour12: false });
  }

  function renderSystemTime() {
    if (!systemTime) return;
    const now = new Date();
    systemTime.textContent = "System time: " + now.toLocaleString(undefined, { hour12: false });
  }

  function selectFile(files) {
    if (!files || files.length === 0) return;
    selectedFile = files[0];
    updateUploadButtonState();
    if (uploadZone) {
      const p = uploadZone.querySelector(".upload-text");
      if (p) p.textContent = "Selected: " + selectedFile.name + " (" + formatBytes(selectedFile.size || 0) + ")";
    }
  }

  async function upload() {
    if (!selectedFile || !hasUploadMeta()) return;
    setLoading("uploadStatus");
    uploadBtn.disabled = true;
    if (uploadProgressFill) uploadProgressFill.style.width = "0%";
    if (uploadProgressText) uploadProgressText.textContent = "Uploading...";

    const form = new FormData();
    form.append("file", selectedFile);
    form.append("subject", subject.value);
    form.append("class_name", className.value);
    form.append("term", term.value);
    form.append("uploaded_by", uploadedBy.value.trim());

    const xhr = new XMLHttpRequest();
    xhr.open("POST", API_BASE + "/api/upload", true);

    xhr.upload.onprogress = (evt) => {
      if (!evt.lengthComputable) return;
      const percent = Math.min(100, Math.round((evt.loaded / evt.total) * 100));
      if (uploadProgressFill) uploadProgressFill.style.width = percent + "%";
      if (uploadProgressText) uploadProgressText.textContent = `${percent}% (${formatBytes(evt.loaded)} / ${formatBytes(evt.total)})`;
    };

    xhr.onerror = () => {
      setError("uploadStatus", "Upload failed");
      uploadBtn.disabled = false;
    };

    xhr.onload = () => {
      let data = {};
      try {
        data = JSON.parse(xhr.responseText || "{}");
      } catch (e) {}

      if (xhr.status < 200 || xhr.status >= 300) {
        setError("uploadStatus", data.detail || "Upload failed");
        uploadBtn.disabled = false;
        return;
      }

      currentJobId = data.job_id;
      jobIdLine.innerHTML = "Job: <strong>" + currentJobId + "</strong>";
      jobMetaLine.textContent =
        `Subject: ${data.subject || "-"} | Class: ${data.class_name || "-"} | ${data.term || "-"} | Uploaded by: ${data.uploaded_by || "-"} | Uploaded at (system time): ${formatDateTime(data.uploaded_at || new Date().toISOString())}`;
      setSuccess("uploadStatus", "Uploaded");
      if (uploadProgressFill) uploadProgressFill.style.width = "100%";
      if (uploadProgressText) uploadProgressText.textContent = "Upload complete";
      processBtn.disabled = false;
      generateFromJobBtn.disabled = false;
      refreshQuestionsBtn.disabled = false;
    };

    xhr.send(form);
  }

  if (uploadBtn) uploadBtn.addEventListener("click", upload);

  async function process() {
    if (!currentJobId) return;
    setLoading("processStatus");
    processBtn.disabled = true;
    if (processProgressText) processProgressText.textContent = "Chunking and embedding in progress...";
    if (processProgressFill) processProgressFill.classList.add("process-animated");

    const pollId = setInterval(async () => {
      if (!currentJobId) return;
      try {
        const jr = await fetch(API_BASE + "/api/jobs/" + encodeURIComponent(currentJobId));
        const j = await jr.json().catch(() => ({}));
        if (jr.ok && processProgressText) {
          processProgressText.textContent = `Status: ${j.status || "-"} | Chunks: ${j.chunks_count || 0}`;
        }
      } catch (e) {}
    }, 2000);

    try {
      const r = await fetch(API_BASE + "/api/process/" + encodeURIComponent(currentJobId), { method: "POST" });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || "Process failed");
      setSuccess("processStatus", "Ready");
      if (processProgressText) processProgressText.textContent = "Processing complete";
    } catch (e) {
      setError("processStatus", e.message);
      processBtn.disabled = false;
      if (processProgressText) processProgressText.textContent = "Processing failed";
    } finally {
      clearInterval(pollId);
      if (processProgressFill) {
        processProgressFill.classList.remove("process-animated");
        processProgressFill.style.width = "100%";
      }
    }
  }

  if (processBtn) processBtn.addEventListener("click", process);

  function showQuestions(text) {
    if (!questionsText) return;
    questionsText.textContent = text || "";
    questionsText.classList.toggle("visible", !!text);
    if (currentJobId) {
      if (exportDocxLink) {
        exportDocxLink.href = API_BASE + "/api/export/" + encodeURIComponent(currentJobId) + "?format=docx";
        exportDocxLink.style.display = "inline-flex";
      }
      if (exportPdfLink) {
        exportPdfLink.href = API_BASE + "/api/export/" + encodeURIComponent(currentJobId) + "?format=pdf";
        exportPdfLink.style.display = "inline-flex";
      }
    }
  }

  async function generateFromText() {
    const text = (textChunk && textChunk.value || "").trim();
    if (text.length < 50) {
      setError("generateTextStatus", "Paste at least 50 characters");
      return;
    }
    setLoading("generateTextStatus");
    generateFromTextBtn.disabled = true;
    try {
      const r = await fetch(API_BASE + "/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text_chunk: text, num_questions: 5 }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || "Generate failed");
      showQuestions(data.questions_text);
      setSuccess("generateTextStatus", (data.num_generated || 0) + " questions");
    } catch (e) {
      setError("generateTextStatus", e.message);
    }
    generateFromTextBtn.disabled = false;
  }

  if (generateFromTextBtn) generateFromTextBtn.addEventListener("click", generateFromText);

  async function generateFromJob() {
    if (!currentJobId) return;
    setLoading("generateJobStatus");
    generateFromJobBtn.disabled = true;
    try {
      const r = await fetch(API_BASE + "/api/questions/" + encodeURIComponent(currentJobId) + "/generate", { method: "POST" });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || "Generate failed");
      showQuestions(data.questions_text);
      setSuccess("generateJobStatus", (data.num_generated || 0) + " questions");
    } catch (e) {
      setError("generateJobStatus", e.message);
    }
    generateFromJobBtn.disabled = false;
  }

  if (generateFromJobBtn) generateFromJobBtn.addEventListener("click", generateFromJob);

  async function refreshQuestions() {
    if (!currentJobId) return;
    setLoading("generateTextStatus");
    setLoading("generateJobStatus");
    try {
      const r = await fetch(API_BASE + "/api/questions/" + encodeURIComponent(currentJobId));
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || "Fetch failed");
      showQuestions(data.questions_text || "");
    } catch (e) {
      showQuestions("");
    }
    clearStatus("generateTextStatus");
    clearStatus("generateJobStatus");
  }

  if (refreshQuestionsBtn) refreshQuestionsBtn.addEventListener("click", refreshQuestions);

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const t = tab.getAttribute("data-tab");
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((x) => x.classList.remove("active"));
      tab.classList.add("active");
      const panel = document.getElementById("panel" + (t === "text" ? "Text" : "Job"));
      if (panel) panel.classList.add("active");
    });
  });

  updateUploadButtonState();
  renderSystemTime();
  setInterval(renderSystemTime, 1000);
})();
