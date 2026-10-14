"use strict";

// Perfumery page: hypotheses and trial plans.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, bench, bottles, experiments, perfumery, assistant, science, boot.

bindSavingForm("#hypothesis-form", async (data, form, saved) => {
  const splitValues = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
  {
    const result = await request("/intervention-hypotheses", {
      method: "POST",
      body: JSON.stringify({
        brief_name: data.brief_name,
        observations: splitValues(data.observations),
        family: data.family || null,
        profile: null,
        mode: data.mode,
        forbidden_materials: splitValues(data.forbidden_materials),
        limit: Number(data.limit),
      }),
    });
    saved();
    $("#hypothesis-output").textContent = JSON.stringify(result, null, 2);
    notify(`${result.hypotheses.length} inventory-valid hypotheses generated.`);
  }
});

bindSavingForm("#trial-plan-form", async (data, form, saved) => {
  {
    const result = await request("/intervention-trials/plan", {
      method: "POST",
      body: JSON.stringify({
        brief_name: data.brief_name,
        material: data.material,
        bottle_total_mass_g: Number(data.bottle_total_mass_g),
        current_material_active_mass_g: Number(data.current_material_active_mass_g),
        stock_active_mass_fraction: Number(data.stock_active_mass_fraction),
        stock_density_g_ml: data.stock_density_g_ml ? Number(data.stock_density_g_ml) : null,
        target_active_ppm_w_w: Number(data.target_active_ppm_w_w),
        threshold_matrix: data.threshold_matrix,
        pipette: {
          minimum_ul: Number(data.pipette_minimum_ul),
          increment_ul: Number(data.pipette_increment_ul),
          maximum_single_step_ul: Number(data.pipette_maximum_ul),
          standard_uncertainty_ul: 0,
          systematic_standard_uncertainty_ul: 0,
        },
        evaluation_attribute: data.evaluation_attribute,
        evaluation_times_seconds: data.evaluation_times_seconds.split(",").map((item) => Number(item.trim())),
      }),
    });
    saved();
    $("#trial-plan-output").textContent = JSON.stringify(result, null, 2);
    notify(`Trial planned at ${result.achieved_active_ppm_w_w.toFixed(3)} ppm w/w.`);
  }
});
