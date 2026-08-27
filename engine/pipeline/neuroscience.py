"""Neuroscience, hedonic processing, receptor genetics, and psychoactive compound database.

Literature-grounded reference database for hedonic_neuroscience pipeline gate.
All citations are advisory (INFO/WARN, never BLOCK).
"""

# Compound psychoactivity database — neuroactive effects at dose thresholds
_PSYCHOACTIVE_EFFECTS: dict[str, list[dict]] = {
    "linalool": [
        {
            "effect": "anxiolytic_GABA_A",
            "threshold_active_pct": 5.0,
            "mechanism": "GABA-A receptor positive allosteric modulation",
            "citations": ["cit_linck_2010", "cit_harada_2018_linalool"],
            "consumer_impact": "Lavender/bergamot formulas >5% linalool may measurably reduce anxiety",
        },
        {
            "effect": "cardiovascular_calming",
            "threshold_active_pct": 2.0,
            "mechanism": "Autonomic — reduces heart rate and blood pressure",
            "citations": ["cit_seol_2016", "cit_sayorwan_2012"],
            "consumer_impact": "Linalool-rich top notes calm autonomically despite high VP",
        },
    ],
    "limonene": [
        {
            "effect": "mood_u_curve_inverted",
            "threshold_low_pct": 2.0,
            "threshold_high_pct": 5.0,
            "mechanism": "Serotonin/dopamine elevation in PFC at low dose; anxiogenic at high dose",
            "citations": ["cit_komiya_2006", "cit_carvalho_freitas_2002"],
            "consumer_impact": "≤2% limonene = calming citrus; >5% = potentially agitating — inverted U-curve",
        },
    ],
    "cedrol": [
        {
            "effect": "sedative_GABA_A",
            "threshold_active_pct": 2.0,
            "mechanism": "GABA-A — systemic absorption, NOT olfactory receptor",
            "citations": ["cit_zhang_2019_cedrol", "cit_kagawaa_2003"],
            "consumer_impact": "Cedarwood drydown >2% cedrol may cause drowsiness via systemic GABA — sedative is pharmacological, not olfactory",
        },
    ],
    "vanillin": [
        {
            "effect": "mood_elevation_serotonin",
            "threshold_active_pct": 0.5,
            "mechanism": "Increased serotonin in rodent brain studies",
            "citations": ["cit_peng_2022_vanillin", "cit_imanishi_2018"],
            "consumer_impact": "Gourmand drydown with vanillin >0.5% may be neurochemically comforting",
        },
    ],
    "eugenol": [
        {
            "effect": "trigeminal_warmth_TRPV1",
            "threshold_active_pct": 0.1,
            "mechanism": "TRPV1 agonist (capsaicin receptor) — somatosensory warmth",
            "citations": ["cit_yang_2003_eugenol", "cit_ohkubo_1997"],
            "consumer_impact": "Clove/cinnamon warmth is trigeminal (skin sensation), not olfactory",
        },
    ],
    "menthol": [
        {
            "effect": "trigeminal_cooling_TRPM8",
            "threshold_active_pct": 0.05,
            "mechanism": "TRPM8 agonist (cold/menthol receptor)",
            "citations": ["cit_mckemy_2002"],
            "consumer_impact": "Peppermint cooling is non-olfactory — freshness via skin cold receptor",
        },
    ],
    "beta_caryophyllene": [
        {
            "effect": "endocannabinoid_CB2",
            "threshold_active_pct": 0.5,
            "mechanism": "Selective CB2 cannabinoid receptor agonist — anti-inflammatory, anxiolytic",
            "citations": ["cit_gertsch_2008", "cit_klauke_2014"],
            "consumer_impact": "Black pepper/clove EO contains β-caryophyllene — mild endocannabinoid effect at >0.5%",
        },
    ],
    "coumarin": [
        {
            "effect": "vasodilatory_transdermal",
            "threshold_active_pct": 0.1,
            "mechanism": "Transdermal absorption — vasodilation, mild anticoagulant",
            "citations": ["cit_coumarin_pharmacology"],
            "consumer_impact": "Coumarin at IFRA levels is safe; above 0.1% active = potential systemic vasodilation",
        },
    ],
    "cineole": [
        {
            "effect": "cognitive_alertness_cerebral_blood_flow",
            "threshold_active_pct": 2.0,
            "mechanism": "Increased cerebral blood flow — improved cognitive task performance",
            "citations": ["cit_moss_2012_cineole"],
            "consumer_impact": "Rosemary/eucalyptus formulas >2% 1,8-cineole may improve alertness",
        },
    ],
    "geraniol": [
        {
            "effect": "antimicrobial_skin_flora",
            "threshold_active_pct": 1.0,
            "mechanism": "Antimicrobial/antifungal — reduces skin pathogen load",
            "citations": ["cit_solorzano_2012", "cit_pattnaik_1997"],
            "consumer_impact": "Rose/geranium formulas >1% geraniol may reduce body odor via skin flora inhibition",
        },
    ],
    "patchouli_alcohol": [
        {
            "effect": "anti_inflammatory_COX2",
            "threshold_active_pct": 0.5,
            "mechanism": "COX-2 inhibition — anti-inflammatory",
            "citations": ["cit_su_2014_patchouli", "cit_xian_2011"],
            "consumer_impact": "Patchouli has pharmacological dimension beyond woody-earthy odor",
        },
    ],
    "citronellol": [
        {
            "effect": "insect_repellent_spatial",
            "threshold_active_pct": 2.0,
            "mechanism": "Spatial repellency — mosquito avoidance",
            "citations": ["cit_muller_2008", "cit_nerio_2010"],
            "consumer_impact": "Citronellol >2% may provide mild mosquito repellent function",
        },
    ],
}


# Olfactory receptor genetics — population polymorphism database
_OR_GENETICS: dict[str, dict] = {
    "OR5AN1": {
        "receptor_type": "macrocyclic_ketone_nitro_musk",
        "ligands": ["muscone", "civettone", "exaltolide", "ambrettolide", "musk ketone"],
        "variant": "L289F",
        "variant_frequency": 0.63,
        "effect": "L289F more sensitive; L/L reference at 35%",
        "citations": ["cit_emter_2024", "cit_ahmed_2018", "cit_sato_akuhara_2023"],
        "dose_cap_active_pct": 10.0,
    },
    "OR5A2": {
        "receptor_type": "polycyclic_musk_lactone",
        "ligands": ["galaxolide", "tonalide", "habanolide"],
        "variant": "P172L",
        "variant_frequency": 0.27,  # European
        "effect": "P172L 50× less sensitive — 27% European near-anosmic",
        "citations": ["cit_emter_2024"],
        "dose_cap_active_pct": 5.0,
    },
    "OR1N2": {
        "receptor_type": "macrocyclic_ketone_civettone",
        "ligands": ["civettone", "muscone"],
        "variant": "W23R/V230G/T287M",
        "variant_frequency": 0.52,  # functional
        "effect": "52% population has functional receptor; 48% near-anosmic to civettone",
        "citations": ["cit_emter_2024"],
        "dose_cap_active_pct": 5.0,
    },
    "OR5A1": {
        "receptor_type": "ionone_ketone",
        "ligands": ["beta-ionone", "alpha-ionone", "dihydro-beta-ionone", "alpha-irone"],
        "variant": "D183N",
        "variant_frequency": 0.05,  # NN homozygotes near-anosmic
        "effect": "D allele dominant; NN carriers (5-10% pop.) near-anosmic to β-ionone",
        "citations": ["cit_jaeger_2013_or5a1", "cit_sato_akuhara_2023"],
        "dose_cap_active_pct": 5.0,
    },
    "OR10J5": {
        "receptor_type": "cedarwood_sesquiterpene",
        "ligands": ["alpha-cedrene", "cis-thujopsene"],
        "variant": None,
        "variant_frequency": None,
        "effect": "More sensitive to α-cedrene than lyral — cedarwood character receptor",
        "citations": ["cit_woo_2017_or10j5"],
        "dose_cap_active_pct": 2.0,
    },
    "OR1A1": {
        "receptor_type": "broad_spectrum",
        "ligands": ["muscone", "citral", "citronellal", "linalool"],
        "variant": None,
        "variant_frequency": None,
        "effect": "Broad receptor — low genetic variation, safe mass-market target",
        "citations": ["cit_ahmed_2018"],
        "dose_cap_active_pct": None,
    },
}


# Hedonic neuroscience — high-level findings for gate advisory
_HEDONIC_FINDINGS: list[dict] = [
    {
        "finding": "Olfaction bypasses thalamus — projects directly to amygdala (2 synapses) and hippocampus (3 synapses)",
        "implication": "Odors trigger emotion BEFORE conscious recognition — unique among senses",
        "citations": ["cit_gottfried_2006", "cit_cahill_1995"],
        "pipeline_effect": "Top-note design is critical — first-impression judgment within 500ms pre-cognitive",
    },
    {
        "finding": "vmPFC area 11 integrates appetitive + aversive odor signals into continuous salience",
        "implication": "More than 5 simultaneously perceptible channels exceed vmPFC integration capacity",
        "citations": ["cit_nature_comms_2026_vmpfc"],
        "pipeline_effect": "WARN if >5 materials have OAV >10 — cognitive overload, olfactory white risk",
    },
    {
        "finding": "Personal perfume memories activate amygdala + hippocampus in fMRI",
        "implication": "Named-reference perfumes trigger autobiographical memory BEFORE conscious fragrance evaluation",
        "citations": ["cit_herz_2009_perfume_fmri"],
        "pipeline_effect": "INFO: reference-claim formulas leverage this neural mechanism — it is intentional, not a defect",
    },
    {
        "finding": "Anticipatory pleasure (wanting) uses ventral striatum; consummatory pleasure (liking) uses mOFC",
        "implication": "Perfume unboxing/dopamine = wanting. Drydown experience = liking. Different neural targets.",
        "citations": ["cit_zou_2016_meta", "cit_olid_2018"],
        "pipeline_effect": "Opening should maximize dopamine (novel, surprising). Drydown should maximize opioid (comforting, familiar).",
    },
    {
        "finding": "Olfactory habituation is receptor-type-specific — limonene-type receptors adapt in 45-90s",
        "implication": "Linear citrus soliflores lose perceptibility in <2 minutes",
        "citations": ["cit_sinding_2017", "cit_dalton_2000"],
        "pipeline_effect": "Already in olfactory_fatigue gate — diversify top notes across receptor types",
    },
    {
        "finding": "fMRI shows brand-label pairing changes odor perception — medial PFC activation",
        "implication": "Prada label on same formula produces different neural response than generic label",
        "citations": ["cit_mcclure_2004", "cit_plassmann_2008"],
        "pipeline_effect": "Consumer testing must account for brand expectation bias",
    },
    {
        "finding": "Stevens power law: perceived intensity = k × (C/ODT)^n where n=0.2-0.6",
        "implication": "Doubling concentration gives only 1.15-1.5× perceived intensity — diminishing returns",
        "citations": ["cit_stevens_1960", "cit_cain_1969"],
        "pipeline_effect": "Already in stevens_power_law gate — don't overdose expecting linear response",
    },
    {
        "finding": "Humans can discriminate at most 3-4 components in a mixture",
        "implication": "Formulas with >18 materials risk olfactory white — no individual character discernible",
        "citations": ["cit_laing_francis_1989", "cit_livermore_laing_1989"],
        "pipeline_effect": "Already in carles_material_count gate",
    },
    {
        "finding": "Odor-color associations are cross-culturally consistent — fruity=warm, pine=green, mint=cool",
        "implication": "Bottle color creates expectation that modifies odor perception",
        "citations": ["cit_gilbert_kemp_1996", "cit_zellner_2013"],
        "pipeline_effect": "INFO: juice color expectation should match olfactory profile or create intentional surprise",
    },
    {
        "finding": "Amygdala hyperactivation to trauma-associated odors in PTSD patients",
        "implication": "Smoky/leather/diesel accords may trigger trauma responses in sensitive populations",
        "citations": ["cit_vermetten_bremner_2002", "cit_cortese_2015"],
        "pipeline_effect": "WARN: leather/smoke-heavy formulas should note potential PTSD trigger sensitivity",
    },
]
