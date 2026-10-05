# AHS muguet layering review — 2026-09-07

**Status: ARCHITECTURE PROPOSAL ONLY. No new dose, physical addition or release accepted.**

## Target and actual bottle

The target remains CHANEL Allure Homme Sport Eau de Toilette, not Eau Extreme, Sport Cologne, Versace Pour Homme or a muguet soliflore. The user reports inadequate muguet immediately after spraying. That observation is accepted as sensory feedback; its mechanism is not yet demonstrated.

[CHANEL's official EDT description](https://www.chanel.com/us/fragrance/p/123630/allure-homme-sport-eau-de-toilette-spray/) identifies mandarin, cedar, tonka and white musk. It does not disclose the full formula or establish muguet as its dominant note. A substantial muguet-style supporting accord remains a plausible reconstruction hypothesis, not an ingredient or ratio claim.

The complete current-bottle parent is [AHS_UserBottle_DHM200_30mL_20260907.md](../../formulas/AHS_UserBottle_DHM200_30mL_20260907.md): user-reported 30 mL; DHM neat 200 microlitres; Helional neat 100 microlitres; all other v3 rows retained. Only positive additions are in scope. Existing quantities, stock forms, natural identities, carriers and historical diagnostics remain unchanged. No Mayol addition event has been reported.

## Layer architecture — build on what is already in the bottle

These are intended relationships, not observed independent notes or sequential evaporation promises.

| Function | Existing support | Proposed action | Specific failure to check |
|---|---|---|---|
| Fresh floral/green contour | Helional 100 microlitres neat; retained citrus/aromatic materials | Hold fixed. Do not automatically add more Helional, DHM, Calone or aldehydes | Sharper ozone, green/hay emphasis or more aromatic impact without floral body |
| Soft muguet body | Existing formula has no row expressly assigned this rounded-body role; that does not prove the effect is absent | Florol neat/as supplied is the primary addition candidate | Soapy/cosmetic flower or obscured mandarin |
| Transparent connection through the heart | Hedione 670 microlitres neat, neroli and the existing floral traces | Hold fixed; evaluate interaction with the body addition | A detached floral cloud instead of continuity |
| Link into the woody/musky drydown | Benzyl Salicylate 250 microlitres neat, existing methylionone, woods and musks | Hold fixed; no automatic extra fixative/musk layer | Muguet becoming a separate bouquet over a disconnected dry base |
| Optional watery density/definition | Already partly occupied by Helional and the proposed body material | Nympheal only as a conditional contrast, not an automatic second addition | More creaminess/density with no distinct target benefit |

[Florol's manufacturer](https://studio.dsm-firmenich.com/product/florolr-pe-966458) describes soft fresh muguet and floral diffusion. That supports selecting it for the body question, not a proven dose.

[Givaudan describes Nympheal](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/nympheal) as diffusive watery/green cyclamen-muguet with floral density and creaminess. It is not simply a fast top-note booster. Its overlap must be tested before selecting both additions.

[IFF describes Helional](https://www.iff.com/scent/ingredients-compendium/helional/) as green/cyclamen with ozone and hay facets. Increasing it is not equivalent to building rounded muguet.

[Mayol's manufacturer](https://studio.dsm-firmenich.com/product/mayolr-pe-957230) supports soft floral, citrus and woody/methylionone connections. Mayol-only remains a role-matched alternative. Adding one material can create several relationships with the existing formula; more ingredients do not establish better layering.

## What the completed Mayol screen established

The [full bound Mayol-only report](../../formulas/AHS_UserBottle_Mayol60_AddOnly_20260907.md) and [verification receipt](../verification/AHS_Mayol60_20260907_review.json) document a hypothetical addition of 60 microlitres to an untouched nominal 30 mL bottle. This is the same nominal ratio as 10 microlitres into 5 mL, not 10 microlitres into the whole bottle.

The fresh parent-linked G15 guard passes with parent and temporal comparisons present. All 27 existing rows and stock declarations remain unchanged. Overall status is FAIL: 103 PASS, 35 WARN, 9 FAIL, 1 SKIP. Ten focused pre-mix tests pass. The bound artifact validates CURRENT; this is an integrity status, not a release pass.

Mayol's modeled opening/5min/30min/4h OAV is 198.719/211.227/239.310/253.038. These are uncalibrated active-concentrate-screen values with the finished matrix omitted. They do not establish immediate punch, sensory balance or Chanel similarity.

## Physics defects prevent OAV-based dose optimization

| Material | Current main local record | Manufacturer comparison | Remaining authority |
|---|---|---|---|
| Mayol | MW166.3; VP1.5 Pa at25C; air ODT3 ppb UNVERIFIED | MW156; VP0.00672 Pa at20C | Identity/physical-data reconciliation required; temperatures differ |
| Florol | MW154.25; VP0.007 Pa at25C; air ODT10 ppb UNVERIFIED | MW173 on product page; VP0.00712 Pa at20C | MW conflict; do not copy a20C pressure into25C without evidence |
| Nympheal | MW204.3; VP0.01 Pa at25C; air ODT2 ppb UNVERIFIED | MW204.3; VP0.001 hPa =0.1 Pa, temperature not stated on that table | Pressure/source-condition conflict and unverified threshold |
| Helional | VP0.01 Pa at25C; air ODT0.1 ppb with local PEER_SINGLE attribution | IFF VP0.000288 mmHg at23C, approximately0.0384 Pa | Different pressure/source temperature; local attribution is not a newly verified threshold study |

Parent inspected the current YAML/ODT fields and official pages. No shared data was silently changed.

A one-input Mayol sensitivity calculation, retaining the same inferred enthalpy and all other uncertain inputs but substituting temperature-adjusted manufacturer VP, changes illustrative opening OAV from198.7 to about1.43. This is NOT a corrected simulation or real OAV. It demonstrates why optimizing a dose against198.7 would be unreliable.

The previous report also retains stock-basis, Lavender coverage, exact-mass and named-reference failures. Stock-data failures do not revoke user-declared ownership, including Coumarin20% in DEP.

## Decision and evidence needed for a real correction

Preferred design: reinforce soft body with Florol inside the existing multi-material architecture. Nympheal is conditional; Mayol is an alternative comparison, not something to stack automatically.

First establish whether body reinforcement improves the immediate0–5min effect while preserving mandarin and connection at30min and the drydown. If an additional watery accent is still justified, compare Florol-only against Florol-plus-Nympheal, with otherwise matched parent portions, vehicle additions, nominal final volume and application amount. A carrier-matched Nympheal omission must lose a useful quality for the second addition to earn its place. Comparisons remain unexecuted and require an actual dosing/safety record before physical work.

Reject the candidate if increased floral prominence comes with soapiness, citrus suppression, detached floral density or poorer reference identity. The user's own reference perception matters; marketing-note omission is not evidence of ingredient absence.

**No exact dose or fixed Florol:Nympheal ratio is released by this review.** Manufacturer descriptions and OAV screens cannot supply that result. Fixing identifiable data errors improves screening, but does not remove the need for sensory comparison.

## Verification and ownership

Native read-only reviews: ahs_muguet_review (target/role critique) and ahs_mayol_manifest_audit (inventory/physics). Parent retained architecture, edits and final acceptance and verified selected findings locally. No worker wrote shared files. The complete historical formulas and their embedded reports remain byte-preserved. No inventory/core-engine edit, physical compounding, Git commit or push occurred.
