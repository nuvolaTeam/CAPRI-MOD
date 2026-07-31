"""Generate the CAPRI-Python input data reference."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#c8c8c8")
BAND = colors.HexColor("#f2f2f0")
ACCENT = colors.HexColor("#2d5016")
FLAG = colors.HexColor("#8a3324")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName="Times-Bold",
                            fontSize=21, leading=25, textColor=INK,
                            alignment=0, spaceAfter=4),
    "sub": ParagraphStyle("s", parent=ss["Normal"], fontName="Times-Italic",
                          fontSize=11.5, leading=15, textColor=MUTED, spaceAfter=15),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Times-Bold",
                         fontSize=14.5, leading=18, textColor=INK,
                         spaceBefore=16, spaceAfter=7),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Times-Bold",
                         fontSize=11.5, leading=14, textColor=ACCENT,
                         spaceBefore=12, spaceAfter=5),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName="Times-Roman",
                           fontSize=10.2, leading=14.2, textColor=INK,
                           alignment=4, spaceAfter=7),
    "note": ParagraphStyle("n", parent=ss["Normal"], fontName="Times-Italic",
                           fontSize=9.2, leading=12.4, textColor=MUTED, spaceAfter=7),
    "cap": ParagraphStyle("c", parent=ss["Normal"], fontName="Times-Italic",
                          fontSize=8.5, leading=11, textColor=MUTED,
                          spaceBefore=3, spaceAfter=11),
    "cell": ParagraphStyle("cl", parent=ss["Normal"], fontName="Times-Roman",
                           fontSize=8.2, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontName="Times-Bold",
                            fontSize=8.2, leading=10.6, textColor=INK),
    "mono": ParagraphStyle("m", parent=ss["Normal"], fontName="Courier",
                           fontSize=7.6, leading=10, textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def table(rows, widths, align=None, mono_cols=()):
    data = []
    for i, r in enumerate(rows):
        row = []
        for j, c in enumerate(r):
            style = "cellb" if i == 0 else ("mono" if j in mono_cols else "cell")
            row.append(Paragraph(str(c), S[style]))
        data.append(row)
    t = Table(data, colWidths=widths, repeatRows=1)
    cmds = [("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, RULE),
            ("LINEBELOW", (0, -1), (-1, -1), 0.8, INK),
            ("BACKGROUND", (0, 0), (-1, 0), BAND)]
    for c in (align or []):
        cmds.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(cmds))
    return t


def build(path):
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="CAPRI-Python: Input Data Reference",
                            author="CAPRI-Python project")
    E = []
    W = 17.0  # usable width in cm

    E.append(P("CAPRI-Python", "title"))
    E.append(P("Input data reference: files, variables, CAPRI provenance and "
               "remaining gaps", "sub"))
    E.append(P(
        "This is the reference document for the model's input data. It lists "
        "every file the model loads, the variable each holds, its units and "
        "dimensions, the CAPRI symbol it derives from, and how much of it rests "
        "on real CAPRI data rather than assumption. Everything is measured from "
        "the current build."))
    E.append(P(
        "The companion document, <i>Data provenance and the gap against CAPRI "
        "star-3.0</i>, covers how the data layer came to be unreliable and what "
        "was done about it. This one is the inventory."))

    # ---------------------------------------------------------- 1 overview
    E.append(P("1. Overview", "h1"))
    E.append(table([
        ["", "Count", ""],
        ["Input files loaded by the model", "23", "plus derived and source files"],
        ["Sourced from a CAPRI GDX read", "19", "every CAPRI-sourced input"],
        ["Correctly published constants", "3", "IPCC factors, agronomic coefficients"],
        ["External to CAPRI", "1", "MFN tariffs"],
        ["Regions", "248", "NUTS-2, EU27 plus Norway"],
        ["Activities", "40", "29 crops, 11 livestock"],
        ["Market commodities", "32", "EU27 as a single bloc"],
    ], [7.4 * cm, 2.0 * cm, 7.6 * cm], align=[1]))

    E.append(P("Model status", "h2"))
    E.append(table([
        ["Check", "Result"],
        ["Data validator", "11 pass, 1 warning, 0 fail"],
        ["Market module reproduces its own prices", "12/12 within 15%"],
        ["Supply convergence, 30-region sample", "30/30"],
        ["Test suite", "15 passing"],
    ], [10.0 * cm, 7.0 * cm]))
    E.append(P(
        "The second check is solver consistency, not price validation: its "
        "reference values are world_prices.csv rounded. It catches solver "
        "regressions and bad Armington shares, and says nothing about whether "
        "the prices are correct.", "cap"))

    # ------------------------------------------------------- 2 file listing
    E.append(P("2. Input files", "h1"))
    E.append(P("Supply side", "h2"))
    E.append(table([
        ["File", "Shape", "Variable / unit", "CAPRI symbol"],
        ["yields.csv", "248 x 40", "output per ha or head, t", "DATA2 YILD; COMI for dairy"],
        ["base_areas.csv", "248 x 29", "activity level, 1000 ha / head", "DATA2 LEVL"],
        ["variable_costs.csv", "248 x 40", "intermediate cost, EUR/ha", "DATA2 TOIN"],
        ["land_availability.csv", "248 x 5", "land endowment, 1000 ha",
         "DATA2 LEVL on ARAB, UAAR, GRAE"],
        ["animal_numbers.csv", "245 x 11", "herd size, 1000 head", "DATA2 HERD"],
        ["supply_elasticities_regional.csv", "173 x 15", "own-price elasticity",
         "estnlp PELA, 2005 slice"],
        ["pmp_diagonal_terms.csv", "2560 x 2", "PMP own term, EUR/ha squared",
         "pmppar p_pmpQuadTechn"],
        ["pmp_crossgroup_terms.csv", "7524 x 3", "PMP cross term", "pmppar p_pmpQuadPact"],
        ["input_requirements.csv", "26375 x 3", "physical input use",
         "DATA2 SEED, FERT, REPM, ELEC"],
    ], [4.6 * cm, 1.9 * cm, 4.6 * cm, 5.9 * cm]))

    E.append(P("Market side", "h2"))
    E.append(table([
        ["File", "Shape", "Variable / unit", "CAPRI symbol"],
        ["producer_prices.csv", "40 x 1", "farm-gate price, EUR/t", "DATA2 MPRI, regional"],
        ["world_prices.csv", "37 x 1", "world price, EUR/t",
         "capmod dataOut Fob at World"],
        ["armington_params.csv", "32 x 4", "substitution elasticities",
         "p_rhoArm1 / p_rhoArm2, GAMS source"],
        ["trade_flows_2017.csv", "547 x 33", "bilateral trade, 1000 t",
         "capmod dataOut ImportQ"],
        ["eu_mfn_tariffs.csv", "1 x 32", "applied tariff", "external, TARIC / WTO"],
    ], [4.6 * cm, 1.9 * cm, 4.6 * cm, 5.9 * cm]))

    E.append(P("Policy, feed and environment", "h2"))
    E.append(table([
        ["File", "Shape", "Variable / unit", "CAPRI symbol"],
        ["cap_payments.csv", "248 x 5", "CAP premium, EUR/ha", "DATA2 PRME, per activity"],
        ["feed_requirements.csv", "10 x 11", "energy, protein, DM, days",
         "DATA2 ENNE, CRPR, DRMN, DRMX, DAYS"],
        ["coco_feed_availability_national.csv", "28 x 11", "feed supply, 1000 t DM",
         "DATA2 feed items"],
        ["nutrient_coefs.csv", "40 x 3", "N, P2O5, K2O applied, kg/ha",
         "DATA2 NITF, PHOF, POTF"],
        ["climate_zones.csv", "521 x 2", "zone shares", "literature, IPCC"],
        ["crop_nutrient_export.csv", "35 x 3", "nutrient removal, kg/t",
         "literature, agronomic"],
        ["manure_ch4_ef_regional.csv", "46 x 2", "methane factor", "literature, IPCC"],
    ], [4.6 * cm, 1.9 * cm, 4.6 * cm, 5.9 * cm]))

    E.append(PageBreak())

    # -------------------------------------------------------- 3 how much real
    E.append(P("3. How much rests on CAPRI data", "h1"))
    E.append(P(
        "Weighted by base area, so a region-activity cell counts in proportion "
        "to the land it represents. Unweighted counts flatter the model by "
        "treating Maltese citrus as equal to French wheat."))
    E.append(table([
        ["Input", "Real CAPRI data", "Limiting factor"],
        ["Variable costs", "79.0%", "56 regions absent from capreg"],
        ["Nutrient coefficients", "79.0%", "same"],
        ["Base areas", "78.9%", "same"],
        ["Producer prices", "78.9%", "same"],
        ["CAP payments", "78.7%", "same"],
        ["Livestock yields", "79.4% of head", "3 of 11 activities merged"],
        ["Supply elasticities", "43.8%", "PELA covers arable only"],
        ["Crop yields", "41.4%", "COCO gaps plus the 56 regions"],
    ], [6.0 * cm, 4.0 * cm, 7.0 * cm], align=[1]))
    E.append(P(
        "The 56 unreachable regions are scattered across 15 countries with no "
        "common pattern, which suggests CAPRI models them at a coarser "
        "resolution rather than that a mapping is missing.", "cap"))

    E.append(P("Validation against an independent source", "h2"))
    E.append(P(
        "Yield quality is measured against COCO2 national 2017 figures, a "
        "separate extraction from a different CAPRI module. The two paths share "
        "nothing but CAPRI itself."))
    E.append(table([
        ["Configuration", "Median error", "Within 20%"],
        ["Before the capreg merge", "16.0%", "61%"],
        ["Current build", "7.3%", "85%"],
        ["capreg source itself", "4.7%", "92%"],
    ], [8.0 * cm, 4.5 * cm, 4.5 * cm], align=[1, 2]))

    # ------------------------------------------------------ 4 CAPRI compare
    E.append(P("4. Comparison with CAPRI star-3.0", "h1"))
    E.append(P("Structural differences", "h2"))
    E.append(P(
        "Three differences are by design and no data will close them:"))
    E.append(table([
        ["Dimension", "CAPRI star-3.0", "CAPRI-Python"],
        ["Regions", "288 NUTS-2 incl. non-EU; finer via HSMU", "248 NUTS-2, EU27 plus Norway"],
        ["Market", "Simultaneous with supply, spatial trade",
         "EU27 single bloc, outer loop"],
        ["Solution", "Simultaneous equilibrium",
         "Iterative: supply solves, aggregates, market clears"],
    ], [3.4 * cm, 6.8 * cm, 6.8 * cm]))
    E.append(P(
        "Regional detail exists only in the supply module. Prices returned from "
        "the market solve are uniform across all 248 regions, so statements "
        "about regional coverage describe the supply side alone.", "cap"))
    E.append(P(
        "On region counts: this installation of CAPRI defines 288 NUTS-2 units, "
        "of which CAPRI-Python covers 248 -- the EU27 plus Norway. The 40 not "
        "covered are non-EU (Turkey, the Western Balkans) and out of scope by "
        "design, not a resolution gap. Within the EU27 the two models share "
        "essentially the same NUTS-2 granularity. CAPRI can disaggregate further "
        "to 1x1km HSMU units for spatial-downscaling work, a separate layer not "
        "relevant to the economic model."))

    E.append(P("Equations that transferred unchanged", "h2"))
    E.append(P(
        "The PMP formulation is a close port. CAPRI's elasticity relation"))
    E.append(P(
        "<i>elas = revenue / (LEVL &#215; shareTerm &#215; (pmpQuadTechn + "
        "pmpQuadPact))</i>", "note"))
    E.append(P(
        "rearranges to exactly the diagonal the Python calibrator builds, which "
        "is why CAPRI's dampening rule and share term dropped in without "
        "restructuring. The same relation, inverted, was later used to recover "
        "elasticities for activities PELA does not cover."))
    E.append(P(
        "CAPRI's own parameters now drive the calibration directly: "
        "p_pmpQuadTechn supplies the diagonal for 192 regions, p_pmpQuadPact "
        "and the PELA cross-price estimates supply the off-diagonals for 173. "
        "The heuristic they replaced was a uniform positive constant; the real "
        "terms are 57 to 71% negative, i.e. genuine substitutes."))

    E.append(PageBreak())

    # ------------------------------------------------------------- 5 gaps
    E.append(P("5. Remaining gaps", "h1"))
    E.append(P("Definitional, not extraction problems", "h2"))
    E.append(table([
        ["Item", "The problem"],
        ["GRAS yields",
         "capreg reports 410.9 for Germany where COCO2 national reports 17,770 "
         "for the same year. The two modules mean different things by the word. "
         "No conversion is applied until that is documented"],
        ["CHES, SKIM, BUTR world prices",
         "Processed products. The producer-price arbitrage check cannot reach "
         "them, because MPRI carries only farm-gate activities. Resolving them "
         "needs a processing-margin relation"],
        ["COTT, OFIB, OFOD base areas",
         "CAPRI aggregates fibre crops as TEXT and fodder as OFAR and ROOF. "
         "Splitting them needs a documented rule; they remain flat constants"],
        ["8 livestock activities",
         "Data exists under CAPRI names. Several are many-to-one and need herd "
         "weights rather than a rename"],
    ], [4.4 * cm, 12.6 * cm]))

    E.append(P("Coverage limits", "h2"))
    E.append(table([
        ["Item", "The problem"],
        ["56 regions",
         "Not represented in capreg at all. Scattered across 15 countries with "
         "no pattern, so probably modelled at coarser resolution in CAPRI"],
        ["Livestock elasticities",
         "pmppar carries no livestock terms, so nothing verifies dairy, beef or "
         "pig supply response. The one genuinely unverified block"],
        ["PELA vintage",
         "The series ends in 2005, twelve years before the base year. Supply "
         "elasticities are structural enough for that to be defensible, but it "
         "should be stated"],
        ["OLIV and SHGM world prices",
         "Model values sit well above the EU producer price with no CAPRI value "
         "to compare against. Now the least defensible entries in that file"],
    ], [4.4 * cm, 12.6 * cm]))

    E.append(P("A gap that turned out not to be one", "h2"))
    E.append(P(
        "The model shows a strong asymmetry in supply response: a cereal price "
        "shock puts around 90% of its acreage reallocation into arable land. "
        "This was recorded through most of the project as a data gap, on the "
        "reasoning that real elasticities existed for arable crops only while "
        "permanent crops sat on literature defaults."))
    E.append(P(
        "Inverting CAPRI's own PMP terms tested that. The derived elasticities "
        "for permanent crops are 0.12 to 0.15, essentially identical to the "
        "literature defaults they would have replaced, and reach only 0.24 to "
        "0.31 even after correcting for the derivation's systematic bias. "
        "Against an arable median of 1.43, the asymmetry is real: orchards and "
        "olive groves take years to establish and are genuinely inelastic in "
        "the short run, where arable can be switched annually."))
    E.append(table([
        ["Activity", "Literature default", "CAPRI-derived", "Bias-corrected"],
        ["Apples", "0.12", "0.15", "0.31"],
        ["Citrus", "0.12", "0.15", "0.31"],
        ["Olives", "0.08", "0.12", "0.24"],
        ["Tomatoes", "0.20", "0.45", "0.94"],
        ["Other vegetables", "0.18", "0.45", "0.93"],
        ["Arable, from PELA", "--", "1.43", "--"],
    ], [5.4 * cm, 4.0 * cm, 3.8 * cm, 3.8 * cm], align=[1, 2, 3]))
    E.append(P(
        "Vegetables and tobacco are the exception and their defaults do look "
        "too low. The derived series is not merged: it reproduces PELA to "
        "within a factor of two with weak regional correlation, so replacing "
        "defaults that turn out to be roughly right would be a step backwards.", "cap"))

    E.append(P("6. What would close the remaining gaps", "h1"))
    E.append(table([
        ["Priority", "Action"],
        ["High", "Establish what GRAS means in capreg versus COCO. Grassland is a "
                 "large share of EU agricultural area"],
        ["High", "Livestock supply elasticities. The only block with no verification "
                 "at all, and it governs how the model responds to meat and dairy "
                 "price changes"],
        ["Medium", "Map the 8 renamed livestock activities, with herd weights for the "
                   "many-to-one cases"],
        ["Medium", "A processing-margin relation for dairy products, to validate CHES, "
                   "SKIM and BUTR world prices"],
        ["Low", "The 56 uncovered regions. Diminishing returns: they are scattered and "
                "individually small"],
    ], [2.4 * cm, 14.6 * cm]))

    doc.build(E)


if __name__ == "__main__":
    build("/mnt/user-data/outputs/CAPRI_Python_input_data_reference.pdf")
    print("built")
