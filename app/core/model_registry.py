def load_models() -> None:
    from app.auth import models as auth_models
    from app.catalog import models as catalog_models
    from app.profile import models as profile_models
    from app.reseller import catalog_models as reseller_catalog_models
    from app.reseller import country_models, models as reseller_models

    _ = (
        auth_models,
        catalog_models,
        profile_models,
        reseller_catalog_models,
        country_models,
        reseller_models,
    )
