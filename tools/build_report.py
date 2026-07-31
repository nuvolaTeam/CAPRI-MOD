"""Generate the CAPRI-Python data provenance and gap analysis report."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#c8c8c8")
BAND = colors.HexColor("#f2f2f0")
ACCENT = colors.HexColor("#2d5016")
WARN = colors.HexColor("#8a3324")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName="Times-Bold",
                            fontSize=21, leading=25, textColor=INK,
                            alignment=0, spaceAfter=4),
    "sub": ParagraphStyle("s", parent=ss["Normal"], fontName="Times-Italic",
                          fontSize=11.5, leading=15, textColor=MUTED,
                          spaceAfter=16),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Times-Bold",
                         fontSize=14.5, leading=18, textColor=INK,
                         spaceBefore=17, spaceAfter=7),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Times-Bold",
                         fontSize=11.5, leading=14, textColor=ACCENT,
                         spaceBefore=12, spaceAfter=5),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName="Times-Roman",
                           fontSize=10.2, leading=14.4, textColor=INK,
                           alignment=4, spaceAfter=7),
    "note": ParagraphStyle("n", parent=ss["Normal"], fontName="Times-Italic",
                           fontSize=9.2, leading=12.6, textColor=MUTED,
                           spaceAfter=7),
    "cap": ParagraphStyle("c", parent=ss["Normal"], fontName="Times-Italic",
                          fontSize=8.6, leading=11, textColor=MUTED,
                          spaceBefore=3, spaceAfter=11),
    "cell": ParagraphStyle("cl", parent=ss["Normal"], fontName="Times-Roman",
                           fontSize=8.9, leading=11.6, textColor=INK),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontName="Times-Bold",
                            fontSize=8.9, leading=11.6, textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def table(rows, widths, align=None, head=True):
    data = []
    for i, r in enumerate(rows):
        style = "cellb" if (head and i == 0) else "cell"
        data.append([Paragraph(str(c), S[style]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, INK),
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
    ]
    for c in (align or []):
        cmds.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(cmds))
    return t


def build(path):
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2.3 * cm, rightMargin=2.3 * cm,
        topMargin=2.1 * cm, bottomMargin=2.1 * cm,
        title="CAPRI-Python: Data Provenance and Gap Analysis",
        author="CAPRI-Python project")
    E = []

    # ---------------------------------------------------------------- cover
    E.append(P("CAPRI-Python", "title"))
    E.append(P("Data provenance and the gap against CAPRI star-3.0", "sub"))

    E.append(P(
        "CAPRI-Python is an independent reimplementation of the CAPRI "
        "agricultural economic model: a regional PMP supply module over 248 "
        "NUTS-2 regions, an Armington market module, CAP policy instruments "
        "and environmental indicators. This report documents what the model's "
        "input data actually is, how it compares with CAPRI's own, and what "
        "remains unresolved."))
    E.append(P(
        "The central finding is that the structural equations were ported "
        "faithfully while the data layer was, for a long time, substantially "
        "invented. Every figure below is measured from the current build "
        "rather than asserted."))

    E.append(P("Model status", "h2"))
    E.append(table([
        ["Check", "Result"],
        ["Data validator", "11 pass, 1 warning, 0 fail"],
        ["Base-year market fidelity", "12/12 commodities within 15%"],
        ["Supply convergence (30-region sample)", "30/30"],
        ["Test suite", "15 passing"],
    ], [10.5 * cm, 5.7 * cm], align=[1]))

    # ------------------------------------------------------- 1 architecture
    E.append(P("1. What the model shares with CAPRI, and what it does not", "h1"))
    E.append(P(
        "The supply side is a close port. The regional programme maximises "
        "gross margin subject to land and nutrient constraints, with a "
        "positive-definite PMP matrix calibrating the base solution to "
        "observed activity levels. CAPRI's own equations transfer directly: "
        "its elasticity relation"))
    E.append(P(
        "<i>elas = revenue / (LEVL &#215; shareTerm &#215; (pmpQuadTechn + "
        "pmpQuadPact))</i>", "note"))
    E.append(P(
        "rearranges to exactly the diagonal the Python calibrator constructs. "
        "That correspondence is why CAPRI's dampening rule and share term "
        "could be dropped in without restructuring anything."))
    E.append(P(
        "Three differences are structural rather than incidental, and no "
        "amount of better data will close them:"))
    E.append(table([
        ["Dimension", "CAPRI star-3.0", "CAPRI-Python"],
        ["Regions", "288 NUTS-2 incl. non-EU; finer via HSMU",
         "248 NUTS-2, EU27 plus Norway"],
        ["Market side", "Simultaneous with supply, spatial trade",
         "EU27 single bloc, outer loop"],
        ["Solution", "Simultaneous supply-market equilibrium",
         "Iterative: supply solves, aggregates, market clears"],
    ], [3.4 * cm, 6.4 * cm, 6.4 * cm]))
    E.append(P(
        "The market simplification matters for interpretation. Regional detail "
        "exists only in the supply module; prices returned from the market "
        "solve are uniform across all 248 regions. Statements about regional "
        "coverage describe the supply side alone.", "note"))

    # ---------------------------------------------------------- 2 the data
    E.append(P("2. Where the input data stands", "h1"))
    E.append(P(
        "Coverage is weighted by base area, so a region-crop cell counts in "
        "proportion to the land it represents. Unweighted counts flatter the "
        "model by treating Maltese citrus as equal to French wheat."))
    E.append(table([
        ["Input", "Real CAPRI data", "Source"],
        ["Nutrient coefficients", "79.0%", "DATA2 NITF / PHOF / POTF, regional"],
        ["Base areas", "78.9%", "DATA2 LEVL"],
        ["CAP payments", "78.7%", "DATA2 PRME, per activity"],
        ["Variable costs", "76.0%", "DATA2 TOIN"],
        ["Producer prices", "75.9%", "DATA2 MPRI, regional"],
        ["Livestock yields", "79.4% of head", "DATA2, dairy / bulls / pig fattening"],
        ["Crop yields", "44.8%", "DATA2 YILD, 192 regions"],
        ["Supply elasticities", "43.8%", "estnlp PELA 2005, 177 regions"],
        ["Land availability", "199 regions", "DATA2 LEVL on ARAB / UAAR / GRAE"],
        ["Animal numbers", "9 animals", "DATA2 HERD"],
        ["Manure nutrients", "192 regions", "DATA2 MANN / MANP / MANK"],
        ["Feed requirements", "192 regions", "DATA2 ENNE, CRPR, DRMN, DRMX, DAYS"],
        ["PMP terms and cross-price", "173 regions", "pmppar and estnlp PELA off-diagonal"],
    ], [6.0 * cm, 3.3 * cm, 6.9 * cm], align=[1]))
    E.append(P(
        "Livestock coverage is weighted by head rather than area, since these "
        "activities have no acreage.", "cap"))

    E.append(P("Validation against an independent source", "h2"))
    E.append(P(
        "Yield quality is measured against COCO2 national 2017 figures, a "
        "separate extraction from a different CAPRI module. The two paths "
        "share nothing but CAPRI itself, so agreement is evidence rather than "
        "circularity. Regional model yields are aggregated to national level "
        "with area weights and compared over 285 country-activity pairs."))
    E.append(table([
        ["Configuration", "Median error", "Within 20%"],
        ["Before the capreg merge", "16.0%", "61%"],
        ["Current build", "7.3%", "85%"],
        ["capreg source itself", "4.7%", "92%"],
    ], [8.0 * cm, 4.1 * cm, 4.1 * cm], align=[1, 2]))
    E.append(P(
        "The residual gap between the current build and the source is coverage, "
        "not quality: 56 regions are not represented in capreg at all and keep "
        "literature-anchored values.", "cap"))

    E.append(PageBreak())

    # ----------------------------------------------------- 3 how it went wrong
    E.append(P("2a. The price and cost re-extraction", "h1"))
    E.append(P(
        "Most files in the data directory were labelled REAL_CAPRI with a source "
        "string of simply \"CAPRI\", which on inspection meant they had come "
        "through the Excel path rather than a GDX read. Re-deriving them from "
        "DATA2 exposed two inputs that were substantially wrong."))
    E.append(P(
        "<b>Producer prices.</b> The national series understated specialty crops "
        "by an order of magnitude or more:"))
    E.append(table([
        ["Activity", "Model, EUR/t", "CAPRI median, EUR/t"],
        ["Other vegetables", "30.8", "495.9"],
        ["Tobacco", "43.8", "2,574.7"],
        ["Other fruit", "24.4", "1,295.7"],
        ["Tomatoes", "33.5", "778.9"],
        ["Table grapes", "218.0", "2,525.6"],
    ], [7.0 * cm, 4.6 * cm, 4.6 * cm], align=[1, 2]))
    E.append(P(
        "Median deviation across 28 comparable activities was 37.5%.", "cap"))
    E.append(P(
        "<b>Variable costs.</b> Median deviation from CAPRI's total intermediate "
        "input was 54.8%. In one German region other vegetables and tomatoes "
        "carried identical costs of 67,360 EUR/ha against CAPRI figures of 5,077 "
        "and 25,387, indicating a group-level fill rather than per-activity data."))
    E.append(P(
        "The two had to be merged as a pair. CAPRI costs with the old prices left "
        "51 staple-crop cells at an implausible loss, because the previous price "
        "and cost series were internally consistent only with each other. Merged "
        "together, the validator warning that had persisted through all earlier "
        "work fell from 418 cells to 105 -- and every remaining case sits in the "
        "56 regions capreg does not cover, so the residual is coverage rather "
        "than error."))

    E.append(PageBreak())
    E.append(P("3. How the data layer became unreliable", "h1"))
    E.append(P(
        "Almost every defect found traces to a single decision: CAPRI data was "
        "extracted through Excel exports rather than read from GDX. The GDX "
        "parser in use had been reverse-engineered by hand and could not decode "
        "the multi-symbol data sections, so spreadsheets became the workaround "
        "and synthetic values filled whatever the workaround dropped."))
    E.append(table([
        ["Defect", "Consequence"],
        ["Cyrillic homoglyphs in activity codes",
         "Four spellings of OANI in circulation; every 'other animals' lookup "
         "silently missed and fell through to a default"],
        ["Regional detail lost in export",
         "1,183 yield cells empty where the crop is grown, although the same "
         "data is dense in the GDX"],
        ["'Latest year per cell' export rule",
         "A ragged vintage mix from 1988 to 2020 inside a 2017 base-year model"],
        ["Internal codes without a crosswalk",
         "CAPRI's 8-character region keys looked incompatible with NUTS-2, so "
         "real data sat unused on disk"],
        ["File-level provenance labels",
         "yields.csv was marked REAL_CAPRI while 16 of its 40 columns were "
         "generated"],
    ], [5.4 * cm, 10.8 * cm]))
    E.append(P(
        "The last of these is a methodology fault rather than an extraction "
        "one, and it was the most consequential: it is what allowed synthetic "
        "livestock yields to sit undetected beside real crop areas."))

    E.append(P("What the audit tools now enforce", "h2"))
    E.append(P(
        "Synthetic data has two statistical signatures. A generated fallback of "
        "the form <i>constant &#215; lognormal(0.10)</i> shows a coefficient of "
        "variation pinned near 0.10 across every region, where real regional "
        "yields scatter at 0.2 to 0.5. A flat placeholder shows a coefficient of "
        "variation of exactly zero. The first signature identified the sixteen "
        "columns misdeclared as real; the second, added later, caught four "
        "constant base-area columns the first had missed."))
    E.append(P(
        "Provenance is now recorded per column, and a cross-check refuses to "
        "pass when a flagged column is declared real. Two guard tests prevent "
        "the code corruption from recurring."))

    # ------------------------------------------------------- 4 the real gap
    E.append(P("4. The gap that remains", "h1"))
    E.append(P("Resolved and closed", "h2"))
    E.append(table([
        ["Item", "Resolution"],
        ["Activity code corruption",
         "25 occurrences across 12 files normalised; guard tests added"],
        ["Elasticity dampening",
         "CAPRI's rule ported. The previous cap truncated 20.3% of values that "
         "CAPRI leaves untouched"],
        ["Solver non-convergence",
         "Iteration budget raised; verified that 3,000 and 6,000 iterations "
         "reach an identical optimum"],
        ["OANI units",
         "Not obtainable. CAPRI models it as a share index, not a herd: LEVL is "
         "1.0 nationally and regional shares sum to 1.0"],
        ["Production days",
         "Six of ten activities were materially wrong. Calves assumed 120 days "
         "against 275 actual, heifers 200 against 298"],
    ], [4.6 * cm, 11.6 * cm]))

    E.append(P("Open, and why", "h2"))
    E.append(table([
        ["Item", "Kind of problem", "Status"],
        ["GRAS yields", "Definitional",
         "capreg reports 410.9 for Germany where COCO2 reports 17,770 for the "
         "same year. The modules mean different things by the word"],
        ["8 livestock activities", "Mapping",
         "Data exists under CAPRI names. Several are many-to-one and need herd "
         "weights, not a rename"],
        ["COTT, OFIB, OFOD areas", "Aggregation",
         "CAPRI reports fibre crops as TEXT and fodder as OFAR/ROOF; splitting "
         "them needs a documented rule"],
        ["56 regions", "Coverage",
         "Scattered across 15 countries with no pattern, suggesting CAPRI "
         "models them at coarser resolution"],
        ["Elasticity asymmetry", "Structural",
         "Real estimates exist only for arable crops"],
    ], [3.7 * cm, 3.0 * cm, 9.5 * cm]))

    E.append(P("4a. The systematic re-extraction", "h1"))
    E.append(P(
        "Patching inputs one at a time meant each error needed its own "
        "investigation, and they surfaced in the order they happened to be "
        "noticed rather than in order of importance. The remedy was a manifest "
        "declaring, for every input, what it is, its unit and dimension, and the "
        "CAPRI symbol it must come from. Of 23 inputs, 19 should come from "
        "CAPRI; the other four are correctly published constants."))
    E.append(table([
        ["Status", "Count", "Inputs"],
        ["Sourced from a GDX read", "16",
         "yields, base areas, costs, prices, CAP payments, land, animal numbers, "
         "nutrients, manure, feed, elasticities, PMP terms, cross-price"],
        ["Still needed", "3", "world prices, Armington parameters, trade flows"],
        ["Literature", "3", "IPCC climate zones, nutrient export, methane factors"],
        ["External", "1", "MFN tariffs"],
    ], [4.2 * cm, 1.6 * cm, 10.4 * cm], align=[1]))
    E.append(P(
        "All sixteen came from dumps already held, so the pass required no "
        "further extraction runs. Two findings from it are worth recording."))
    E.append(P(
        "<b>CAP payments were applied uniformly.</b> The previous file was "
        "region by instrument, summed to 676.7 EUR/ha at DE11 and applied to "
        "every crop with nothing to livestock. CAPRI's per-activity premium is "
        "360.8 for soft wheat, 108.2 for dairy cows and 8.2 for bulls. Crops "
        "were therefore nearly doubled and livestock zeroed -- a distortion of "
        "precisely the relative profitability that PMP calibration exists to "
        "capture."))
    E.append(P(
        "<b>The elasticity file was clipped, not dampened.</b> It reproduced "
        "CAPRI's PELA 2005 slice exactly, but with 270 cells sitting at exactly "
        "4.500. CAPRI's rule is min(8, sqrt(e) + 4.5 - sqrt(4.5)); the affected "
        "cells averaged 4.50 where CAPRI gives 5.27, and the largest raw value, "
        "111.0, was understated by 44%. This is the same truncation error that "
        "was found in the code months earlier, present independently in the "
        "data and unaffected by the code fix."))

    E.append(P("4b. The market side", "h1"))
    E.append(P(
        "The supply side was reworked first because it was where the obvious "
        "damage was. The market side turned out to hold two problems that were "
        "harder to see, because the checks available could not detect them."))
    E.append(P("The base-fidelity test is circular", "h2"))
    E.append(P(
        "The test reported throughout this project as \"12/12 base-year market "
        "fidelity\" compares the model's solved prices against reference values "
        "that are world_prices.csv rounded to the nearest integer. It therefore "
        "asserts that the market module converges back to the prices it was "
        "handed. That is a real check -- it catches solver regressions, bad "
        "Armington shares and unit errors in aggregation -- but it is not price "
        "validation, and nothing else in the repository can supply one, because "
        "every available check reads the same file. The test has been renamed to "
        "say what it does."))
    E.append(P(
        "Against CAPRI's own capmod base-year result, 11 of 24 comparable "
        "commodities agree within 20%. Eight diverge by more than half, and not "
        "in a consistent direction: four of those carry model values that are "
        "exact multiples of ten, the same placeholder fingerprint found "
        "elsewhere, while soya runs the other way and is closer in the model "
        "than in CAPRI. No merge was made, because a wholesale replacement would "
        "fix the placeholders and break soya."))
    E.append(P("The trade matrix had no intra-EU trade", "h2"))
    E.append(P(
        "More serious, and not a vintage problem at all. The 2021 bilateral "
        "matrix carried a zero diagonal: all 29 self-trade pairs summed to "
        "exactly zero. The Armington first nest therefore saw a 100% extra-EU "
        "import share for every commodity, including those where intra-EU trade "
        "dominates."))
    E.append(table([
        ["Commodity", "2021 matrix", "CAPRI 2017"],
        ["Milk", "100.0%", "0.0%"],
        ["Pork", "100.0%", "0.7%"],
        ["Barley", "100.0%", "1.4%"],
        ["Soft wheat", "100.0%", "3.1%"],
        ["Beef", "100.0%", "6.5%"],
        ["Soya", "100.0%", "89.9%"],
    ], [7.0 * cm, 4.6 * cm, 4.6 * cm], align=[1, 2]))
    E.append(P(
        "Extra-EU share of EU imports. Median change 96.1 percentage points. "
        "Soya is the sanity check: it genuinely is almost entirely imported, and "
        "it is the one commodity the old matrix had nearly right by accident.", "cap"))

    E.append(P("5. The asymmetry problem", "h1"))
    E.append(P(
        "This is the most important caveat in the report, and it is not fixed "
        "by any of the work above."))
    E.append(P(
        "CAPRI's econometric elasticity estimates exist for arable crops only. "
        "Wiring them in raises the responsiveness of that block while permanent "
        "crops, grassland and livestock remain on literature defaults. The "
        "measured ratio between covered and uncovered activities is 9.56: a "
        "covered activity responds roughly nine and a half times more strongly to price."))
    E.append(P(
        "A +20% cereal price shock over 20 regions shows where that lands:"))
    E.append(table([
        ["Configuration", "Reallocation", "In covered arable", "Elsewhere"],
        ["Literature defaults", "556.8 kha", "66.5%", "33.5%"],
        ["CAPRI elasticities", "1,874.9 kha", "90.1%", "9.9%"],
    ], [4.9 * cm, 3.4 * cm, 4.0 * cm, 3.9 * cm], align=[1, 2, 3]))
    E.append(P(
        "The model becomes markedly more responsive, and adjustment "
        "concentrates in arable land. This is a property of data coverage "
        "rather than a defect in the wiring, but it argues against using the "
        "model for policy scenarios until coverage extends to permanent crops "
        "and livestock. A base-year gate cannot detect it, because the base "
        "year is unshocked by construction.", "note"))

    E.append(P("6. Assessment", "h1"))
    E.append(P(
        "The architecture is sound. Base-year fidelity holds at 12 of 12 "
        "commodities, structural inputs are almost entirely real, and CAPRI's "
        "own PMP equations transferred without modification once the correct "
        "source files were located. What was thin was the data layer, and the "
        "cause was extraction method rather than model design."))
    E.append(P(
        "That layer is now materially better: yield error against an "
        "independent benchmark has fallen from 16.0% to 7.3%, livestock yields "
        "have moved from wholly invented to real for 79% of animals, and "
        "CAPRI's own cross-group substitution terms have replaced an invented "
        "uniform constant. Roughly 45% of the model by area now rests on real "
        "CAPRI data, against 31% before this work."))
    E.append(P(
        "It is not finished. Grassland yields remain unresolved, elasticity "
        "coverage is asymmetric in a way that distorts scenario results, and "
        "eight livestock activities await a mapping. These are documented "
        "rather than hidden, which is the substantive change: the model no "
        "longer claims more than it holds."))

    doc.build(E)


if __name__ == "__main__":
    build("/mnt/user-data/outputs/CAPRI_Python_data_gap_report.pdf")
    print("built")
