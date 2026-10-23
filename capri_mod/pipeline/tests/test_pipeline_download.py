"""Tests of the download layer (capri_mod/pipeline: config, manifest, store, catalogue, ingest/eurostat, fetch).

Offline tests use a stored Eurostat answer (tests/data/eurostat_apro_cpsh1_sample.csv.gz: apro_cpsh1, soft wheat,
AT and BE, 2015-2026, as received on 23 October 2026). The live test runs only with CAPRI_ONLINE_TESTS=1
(marker "online").
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from capri_mod.pipeline import manifest, store
from capri_mod.pipeline.ingest import eurostat

SAMPLE = Path(__file__).parent / "data" / "eurostat_apro_cpsh1_sample.csv.gz"


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAPRI_PIPELINE_STORE", str(tmp_path / "store"))
    return tmp_path / "store"


def _raw():
    return eurostat.RawDownload(url="https://example/apro_cpsh1", query="q", data=SAMPLE.read_bytes(), ext="csv.gz")


def test_eurostat_parse_keeps_dimensions_values_and_flags():
    df = eurostat.parse(_raw())
    assert list(df.columns[:4]) == ["freq", "crops", "strucpro", "geo"]
    assert set(df.geo) == {"AT", "BE"} and set(df.crops) == {"C1110"}
    v = df[(df.geo == "AT") & (df.strucpro == "AR_THS_HA") & (df.time == "2015")].value
    assert float(v.iloc[0]) == pytest.approx(283.89)
    assert eurostat.provider_updated(df) == "28/09/26 23:00:00"


def test_eurostat_missing_cell_is_nan_with_flag_not_zero():
    text = ("DATAFLOW,LAST UPDATE,freq,geo,TIME_PERIOD,OBS_VALUE,OBS_FLAG,CONF_STATUS\n"
            "ESTAT:X(1.0),01/01/26 00:00:00,A,AT,2020,,c,C\n"
            "ESTAT:X(1.0),01/01/26 00:00:00,A,AT,2021,0,,\n")
    df = eurostat.parse(eurostat.RawDownload("u", "q", text.encode(), "csv"))
    assert np.isnan(df.value.iloc[0]) and df.flag.iloc[0] == "c"
    assert df.value.iloc[1] == 0.0


def test_eurostat_key_follows_dimension_order_and_rejects_unknown_names():
    dims = ["freq", "crops", "strucpro", "geo"]
    assert eurostat.build_key(dims, {"crops": "C1110", "geo": ["AT", "BE"]}) == ".C1110..AT+BE"
    with pytest.raises(ValueError, match="no dimension"):
        eurostat.build_key(dims, {"country": "AT"})


def test_store_appends_versions_and_latest_selects_the_newest(tmp_store):
    df = eurostat.parse(_raw())
    a, b = df.assign(download_id="eurostat-x-20260101T000000Z"), df.assign(download_id="eurostat-x-20260102T000000Z")
    b.loc[b.index[0], "value"] = -1.0
    assert store.write(a, "raw", "eurostat", "x") == 0
    assert store.write(b, "raw", "eurostat", "x") == 1
    assert len(store.read("raw", "eurostat", "x")) == 2 * len(df)
    last = store.latest("raw", "eurostat", "x")
    assert len(last) == len(df) and (last.download_id == "eurostat-x-20260102T000000Z").all()
    assert store.read("raw", "eurostat", "x", version=0).value.iloc[0] != -1.0
    out = store.export_csv("raw", "eurostat", "x", tmp_store / "x.csv")
    assert len(pd.read_csv(out)) == len(df)


def test_fetch_stores_raw_file_table_and_manifest(tmp_store, monkeypatch):
    from capri_mod.pipeline import fetch as F
    monkeypatch.setattr(eurostat, "fetch", lambda dataset, filters=None, start=None, end=None: _raw())
    r = F.fetch("eurostat", "apro_cpsh1")
    assert r.rows == len(eurostat.parse(_raw()))
    m = manifest.read()
    assert len(m) == 1 and m[0]["dataset"] == "apro_cpsh1" and manifest.verify(m[0])
    assert m[0]["licence"].startswith("Eurostat")
    (tmp_store / m[0]["raw_path"]).write_bytes(b"changed")
    assert not manifest.verify(m[0])


def test_catalogue_rejects_unknown_provider_keys_and_bad_filters(tmp_path):
    from capri_mod.pipeline import catalogue
    p = tmp_path / "c.toml"
    p.write_text('[[dataset]]\nprovider = "nowhere"\ndataset = "x"\nstatus = "available"\n')
    with pytest.raises(ValueError, match="unknown provider"):
        catalogue.load(p)
    p.write_text('[[dataset]]\nprovider = "eurostat"\ndataset = "x"\nstatus = "available"\ncolour = 1\n')
    with pytest.raises(ValueError, match="unknown keys"):
        catalogue.load(p)
    p.write_text('[[dataset]]\nprovider = "eurostat"\ndataset = "x"\nstatus = "available"\nfilters = "geo=AT"\n')
    with pytest.raises(ValueError, match="filters must be a table"):
        catalogue.load(p)
    p.write_text('[[dataset]]\nprovider = "eurostat"\ndataset = "apro_cpsh1"\nstatus = "available"\n'
                 'filters = { geo = ["AT"] }\nstart = 2015\n')
    e = catalogue.load(p)[0]
    assert e.filters == {"geo": ["AT"]} and e.start == 2015 and e.end is None


@pytest.mark.online
@pytest.mark.skipif(os.environ.get("CAPRI_ONLINE_TESTS") != "1", reason="live API test: CAPRI_ONLINE_TESTS=1")
def test_eurostat_live_small_query(tmp_store):
    from capri_mod.pipeline import fetch as F
    r = F.fetch("eurostat", "apro_cpsh1", {"crops": "C1110", "geo": "AT"}, start=2020, end=2021)
    assert r.rows > 0
    df = store.latest("raw", "eurostat", "apro_cpsh1")
    assert set(df.geo) == {"AT"}


def test_catalogue_of_coco_inputs_loads():
    from capri_mod.pipeline import catalogue
    rows = catalogue.load()
    assert len(rows) > 100
    assert {"eurostat", "faostat"} <= {e.provider for e in rows}
    assert {e.status for e in rows} <= {"available", "discontinued", "replaced_partially", "unknown"}


FAO_SAMPLE = Path(__file__).parent / "data" / "faostat_RL_sample.zip"


def _fao_raw(filters=None, start=None, end=None):
    from capri_mod.pipeline.ingest import faostat
    return faostat.RawDownload(url="https://bulks-faostat.fao.org/x.zip", query="q", data=FAO_SAMPLE.read_bytes(),
                               ext="zip", meta={"DateUpdate": "2026-10-02T00:00:00"}, filters=filters or {},
                               start=start, end=end)


def test_faostat_bulk_parse_filters_and_years():
    """A real excerpt of FAOSTAT's land-use bulk file (RL, 2 October 2026): Germany (79) and Italy (106)."""
    from capri_mod.pipeline.ingest import faostat
    df = faostat.parse(_fao_raw())
    assert {"area_code", "item_code", "element_code", "time", "value", "flag", "unit"} <= set(df.columns)
    assert set(df.area_code) == {"79", "106"}
    de = faostat.parse(_fao_raw({"Area Code": "79"}, start=1970, end=1975))
    assert set(de.area_code) == {"79"} and de.time.astype(int).between(1970, 1975).all()
    with pytest.raises(ValueError, match="no column"):
        faostat.parse(_fao_raw({"Country": "79"}))


def test_faostat_fetch_writes_chunks_and_manifest(tmp_store, monkeypatch):
    from capri_mod.pipeline import fetch as F
    from capri_mod.pipeline.ingest import faostat
    monkeypatch.setattr(faostat, "fetch", lambda dataset, filters=None, start=None, end=None: _fao_raw(filters))
    r = F.fetch("faostat", "RL", {"Area Code": "106"})
    assert r.rows == 20
    m = manifest.read()[-1]
    assert m["provider_updated"] == "2026-10-02T00:00:00" and m["licence"].startswith("FAO") and manifest.verify(m)
    assert set(store.latest("raw", "faostat", "RL").area_code) == {"106"}
