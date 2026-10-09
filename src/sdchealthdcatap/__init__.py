"""Describe a published Semantic Data Charter model's governed data records in HealthDCAT-AP (Release 8).

One or more models in, one dcat:Catalog out at a declared access level: a Dataset per model with the health
extension, its variables as a CSVW table group built from the record's leaves, its coding systems from the model's
bindings, and the data holder's facts from declared input. Validated with the HealthData@EU validator's own shape set
for the level, at a pinned commit.
"""
from sdcreader import ModelPackage, load_package, fetch_package, read_model
from .healthdcatap import build_health_catalog, load_declared, DeclaredInputError

__version__ = "4.0.0"
__all__ = ["ModelPackage", "load_package", "fetch_package", "read_model", "build_health_catalog", "load_declared", "DeclaredInputError", "__version__"]
