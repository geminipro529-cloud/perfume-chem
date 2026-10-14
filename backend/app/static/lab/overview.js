"use strict";

// Overview page: backup, restore and workspace export.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

bindSavingForm("#backup-form", async (data, form, saved) => {
  const result = await request("/backups", { method: "POST", body: JSON.stringify(data), timeoutMs: 0 });
  saved();
  $("#backup-output").textContent = JSON.stringify(result, null, 2);
  $("#stage-restore-form [name=snapshot_path]").value = result.snapshot_path;
  notify("Verified backup created.");
});

bindSavingForm("#stage-restore-form", async (data, form, saved) => {
  const result = await request("/restores/stage", { method: "POST", body: JSON.stringify(data) });
  saved();
  $("#backup-output").textContent = JSON.stringify(result, null, 2);
  notify("Restore validated and staged. Replacement still requires stopped-server maintenance.");
});

$("#export-workspace").addEventListener("click", async () => {
  try {
    const result = await request("/export", { timeoutMs: 0 });
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "perfume-chem-lab-export.json";
    link.click();
    URL.revokeObjectURL(link.href);
    $("#backup-output").textContent = `Exported ${Object.keys(result.tables).length} ordered tables.`;
    notify("Workspace export prepared.");
  } catch (error) { notify(error.message, true); }
});
