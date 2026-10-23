"""CAPRI-MOD data pipeline (docs/design/CAPTRD_MOD.md): COCO-like and CAPREG-like databases and CAPTRD-MOD.

One-way dependency (CAPTRD_MOD.md section 9): the pipeline writes files and the model reads files; the model never
imports this package. With the pipeline absent or switched off the model runs exactly as before.

Subpackages:
    captrd   CAPRI's baseline trend projection (CAPTRD), ported step by step from the GAMS code
"""
