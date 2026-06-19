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
  var clearBtn = document.getElementById("clear_btn");

  var docNameEl = document.getElementById("doc_name");
  var previewMetaEl = document.getElementById("preview_meta");
  var stateIdle = document.getElementById("state_idle");
  var stateWorking = document.getElementById("state_working");
  var stateError = document.getElementById("state_error");
  var stateDone = document.getElementById("state_done");
  var errorTextEl = document.getElementById("error_text");
  var pdfEmbed = document.getElementById("pdf_embed");
  var downloadBtn = document.getElementById("download_btn");
  var preparedByEl = document.getElementById("prepared_by");
  var analystEl = document.getElementById("analyst");
  var recGridEl = document.getElementById("rec_grid");
  var recCountEl = document.getElementById("rec_count");
  var selectedRec = "";

  // Sector picker elements.
  var sectorChipsEl = document.getElementById("sector_chips");
  var sectorCountEl = document.getElementById("sector_count");
  var sectorSubEl = document.getElementById("sector_sub");
  var docSectorEl = document.getElementById("doc_sector");
  var selectedMain = "";

  // Track the one attached file and the current object url so it can be freed.
  var attachedFile = null;
  var lastObjectUrl = null;
  var lastFileName = "brief.pdf";
  var defaultPreparedBy = preparedByEl.value;
  var defaultAnalyst = analystEl.value;

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

  // Reflect the picked sector in the preview header.
  function updateSectorPreview() {
    var sub = sectorSubEl.value.trim();
    if (!selectedMain) { docSectorEl.textContent = "SECTOR TBD"; return; }
    docSectorEl.textContent = sub
      ? selectedMain.toUpperCase() + " - " + sub.toUpperCase()
      : selectedMain.toUpperCase();
  }

  // Single select chips for the main sector label.
  Array.prototype.forEach.call(sectorChipsEl.querySelectorAll(".chip"), function (chip) {
    chip.addEventListener("click", function () {
      var val = chip.getAttribute("data-sector");
      if (selectedMain === val) {
        selectedMain = "";
        chip.classList.remove("active");
      } else {
        selectedMain = val;
        Array.prototype.forEach.call(sectorChipsEl.querySelectorAll(".chip"), function (c) {
          c.classList.toggle("active", c === chip);
        });
      }
      sectorCountEl.textContent = selectedMain ? "1 selected" : "none selected";
      updateSectorPreview();
    });
  });
  sectorSubEl.addEventListener("input", updateSectorPreview);

  // Single select chips for the recorded recommendation.
  Array.prototype.forEach.call(recGridEl.querySelectorAll(".rec_chip"), function (chip) {
    chip.addEventListener("click", function () {
      var val = chip.getAttribute("data-rec");
      if (selectedRec === val) {
        selectedRec = "";
        chip.classList.remove("active");
      } else {
        selectedRec = val;
        Array.prototype.forEach.call(recGridEl.querySelectorAll(".rec_chip"), function (c) {
          c.classList.toggle("active", c === chip);
        });
      }
      recCountEl.textContent = selectedRec ? selectedRec + " (team)" : "no decision recorded";
    });
  });

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
    form.append("sector_main", selectedMain);
    form.append("sector_sub", sectorSubEl.value.trim());
    form.append("prepared_by", preparedByEl.value.trim());
    form.append("analyst", analystEl.value.trim());
    form.append("recommendation", selectedRec);

    fetch("/generate", { method: "POST", body: form })
      .then(function (response) {
        if (!response.ok) {
          return response.text().then(function (text) {
            throw new Error(stripTags(text) || ("Request failed with status " + response.status));
          });
        }
        lastFileName = filenameFromResponse(response) || (company.replace(/[^A-Za-z0-9]+/g, "_") + "_onepager.pdf");
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

  // Pull the saved filename out of the content disposition header.
  function filenameFromResponse(response) {
    var header = response.headers.get("Content-Disposition") || "";
    var match = /filename="?([^"]+)"?/.exec(header);
    return match ? match[1] : "";
  }

  // Save the generated PDF with its real name through a temporary link.
  function downloadPdf() {
    if (!lastObjectUrl) { return; }
    var a = document.createElement("a");
    a.href = lastObjectUrl;
    a.download = lastFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
  downloadBtn.addEventListener("click", downloadPdf);

  // Turn a short html error page from the server into plain text.
  function stripTags(html) {
    var tmp = document.createElement("div");
    tmp.innerHTML = html;
    return (tmp.textContent || "").trim();
  }

  // Reset every input so a new company can be entered from scratch.
  function clearAll() {
    companyEl.value = "";
    notesEl.value = "";
    sectorSubEl.value = "";
    selectedMain = "";
    Array.prototype.forEach.call(sectorChipsEl.querySelectorAll(".chip"), function (c) {
      c.classList.remove("active");
    });
    sectorCountEl.textContent = "none selected";
    preparedByEl.value = defaultPreparedBy;
    analystEl.value = defaultAnalyst;
    selectedRec = "";
    Array.prototype.forEach.call(recGridEl.querySelectorAll(".rec_chip"), function (c) {
      c.classList.remove("active");
    });
    recCountEl.textContent = "no decision recorded";
    attachedFile = null;
    deckInputEl.value = "";
    renderFile();
    updateCharCount();
    updateDocName();
    updateSectorPreview();
    previewMetaEl.textContent = "draft";
    showState("idle");
    companyEl.focus();
  }
  clearBtn.addEventListener("click", clearAll);

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
  updateSectorPreview();
  showState("idle");
})();