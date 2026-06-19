/*
MMF sourcing brief generator. Web front end script.

Handles the live behavior of the page. For this version it covers the real
generate flow only. The user fills in a company name, pastes notes, optionally
attaches one PDF, and clicks Generate. The script posts the form to the server,
shows a working state, and renders the returned PDF inline in the preview pane.
*/

(function () {
  "use strict";

  // Grab the elements the script drives.
  var companyEl = document.getElementById("company");
  var notesEl = document.getElementById("notes");
  var charcountEl = document.getElementById("charcount");
  var dropzoneEl = document.getElementById("dropzone");
  var deckInputEl = document.getElementById("deck_input");
  var fileSummaryEl = document.getElementById("file_summary");
  var fileListEl = document.getElementById("file_list");
  var generateBtn = document.getElementById("generate_btn");
  var generateLabel = document.getElementById("generate_label");

  var docNameEl = document.getElementById("doc_name");
  var previewMetaEl = document.getElementById("preview_meta");
  var stateIdle = document.getElementById("state_idle");
  var stateWorking = document.getElementById("state_working");
  var stateError = document.getElementById("state_error");
  var stateDone = document.getElementById("state_done");
  var errorTextEl = document.getElementById("error_text");
  var pdfEmbed = document.getElementById("pdf_embed");

  // Track the one attached file and the current object url so it can be freed.
  var attachedFile = null;
  var lastObjectUrl = null;

  // Live character count under the notes box.
  function updateCharCount() {
    var n = notesEl.value.length;
    charcountEl.textContent = n.toLocaleString() + " chars";
  }
  notesEl.addEventListener("input", updateCharCount);

  // Mirror the company name into the preview header as the user types.
  function updateDocName() {
    var name = companyEl.value.trim();
    docNameEl.textContent = name || "Company name";
  }
  companyEl.addEventListener("input", updateDocName);

  // Render the attached file row, or clear it when there is no file.
  function renderFile() {
    fileListEl.innerHTML = "";
    if (!attachedFile) {
      fileSummaryEl.textContent = "no file";
      return;
    }
    fileSummaryEl.textContent = "1 file";

    var row = document.createElement("div");
    row.className = "file_row";

    var ext = document.createElement("div");
    ext.className = "file_ext";
    ext.textContent = "PDF";

    var meta = document.createElement("div");
    meta.className = "file_meta";
    var name = document.createElement("div");
    name.className = "file_name";
    name.textContent = attachedFile.name;
    var sub = document.createElement("div");
    sub.className = "file_sub";
    sub.textContent = formatSize(attachedFile.size) + " ready";
    meta.appendChild(name);
    meta.appendChild(sub);

    var remove = document.createElement("button");
    remove.className = "file_remove";
    remove.type = "button";
    remove.textContent = "\u00d7";
    remove.addEventListener("click", function () {
      attachedFile = null;
      deckInputEl.value = "";
      renderFile();
    });

    row.appendChild(ext);
    row.appendChild(meta);
    row.appendChild(remove);
    fileListEl.appendChild(row);
  }

  // Human readable file size.
  function formatSize(bytes) {
    if (bytes < 1024) { return bytes + " B"; }
    if (bytes < 1024 * 1024) { return Math.round(bytes / 1024) + " KB"; }
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // Accept a chosen file only when it is a PDF.
  function acceptFile(file) {
    if (!file) { return; }
    if (file.type !== "application/pdf" && !/\.pdf$/i.test(file.name)) {
      showError("That file is not a PDF. Export it to PDF and try again.");
      return;
    }
    attachedFile = file;
    renderFile();
  }

  // Wire the drop zone to the hidden file input.
  dropzoneEl.addEventListener("click", function () { deckInputEl.click(); });
  deckInputEl.addEventListener("change", function () {
    acceptFile(deckInputEl.files[0]);
  });
  dropzoneEl.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropzoneEl.classList.add("over");
  });
  dropzoneEl.addEventListener("dragleave", function () {
    dropzoneEl.classList.remove("over");
  });
  dropzoneEl.addEventListener("drop", function (e) {
    e.preventDefault();
    dropzoneEl.classList.remove("over");
    if (e.dataTransfer && e.dataTransfer.files.length) {
      acceptFile(e.dataTransfer.files[0]);
    }
  });

  // Switch the preview pane between its states.
  function showState(which) {
    stateIdle.classList.toggle("hidden", which !== "idle");
    stateWorking.classList.toggle("hidden", which !== "working");
    stateError.classList.toggle("hidden", which !== "error");
    stateDone.classList.toggle("hidden", which !== "done");
  }

  // Show an error in the preview pane and reset the button.
  function showError(message) {
    errorTextEl.textContent = message;
    previewMetaEl.textContent = "error";
    showState("error");
    setBusy(false);
  }

  // Toggle the generating state of the button.
  function setBusy(busy) {
    generateBtn.disabled = busy;
    generateLabel.textContent = busy ? "Synthesizing" : "Generate brief";
    var star = generateBtn.querySelector(".star");
    if (star) { star.classList.toggle("hidden", busy); }
    var ring = generateBtn.querySelector(".ring");
    if (busy && !ring) {
      ring = document.createElement("span");
      ring.className = "ring";
      generateBtn.insertBefore(ring, generateLabel);
    } else if (!busy && ring) {
      ring.remove();
    }
  }

  // Post the form and render the returned PDF inline.
  function generate() {
    var company = companyEl.value.trim();
    if (!company) {
      showError("Enter a company name to generate a brief.");
      companyEl.focus();
      return;
    }

    setBusy(true);
    previewMetaEl.textContent = "rendering";
    showState("working");

    var form = new FormData();
    form.append("company", company);
    form.append("notes", notesEl.value);
    if (attachedFile) { form.append("deck", attachedFile); }

    fetch("/generate", { method: "POST", body: form })
      .then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) {
            throw new Error(stripTags(text) || ("Request failed with status " + response.status));
          });
        }
        return response.blob();
      })
      .then(function (blob) {
        if (lastObjectUrl) { URL.revokeObjectURL(lastObjectUrl); }
        lastObjectUrl = URL.createObjectURL(blob);
        pdfEmbed.setAttribute("src", lastObjectUrl);
        previewMetaEl.textContent = "2 page PDF";
        showState("done");
        setBusy(false);
      })
      .catch(function (error) {
        showError(error.message || "Something went wrong generating the brief.");
      });
  }

  // Turn a short html error page from the server into plain text.
  function stripTags(html) {
    var tmp = document.createElement("div");
    tmp.innerHTML = html;
    return (tmp.textContent || "").trim();
  }

  generateBtn.addEventListener("click", generate);

  // Allow command or control plus enter to generate from anywhere on the page.
  document.addEventListener("keydown", function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!generateBtn.disabled) { generate(); }
    }
  });

  // Set the starting state.
  updateCharCount();
  updateDocName();
  renderFile();
  showState("idle");
})();