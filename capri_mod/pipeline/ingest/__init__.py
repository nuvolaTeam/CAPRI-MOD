"""Provider adapters of the download layer, one per provider, behind one interface (docs/design/CAPTRD_MOD.md
section 7): fetch(dataset, ...) downloads the provider's file and returns it with its URL and metadata; parse(...)
turns it into a long table (the provider's own dimension codes, time, value, flag). The fetch entry point
(capri_mod.pipeline.fetch) stores both and writes the manifest row.

    eurostat   Eurostat dissemination API, SDMX-CSV (synchronous; asynchronous extraction for large requests)
    faostat    FAOSTAT bulk files (zip of the normalized CSV), filtered and stored in chunks
"""
from capri_mod.pipeline.ingest import eurostat, faostat

ADAPTERS = {"eurostat": eurostat, "faostat": faostat}
