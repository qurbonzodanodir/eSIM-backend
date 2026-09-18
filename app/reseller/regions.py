REGION_COUNTRIES: dict[str, frozenset[str]] = {
    "europe": frozenset(
        "AD AL AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI GR "
        "HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS "
        "RU SE SI SJ SK SM UA VA XK".split()
    ),
    "middle_east": frozenset("AE BH EG IL IQ IR JO KW LB OM PS QA SA SY YE".split()),
    "asia": frozenset(
        "AF AM AZ BD BN BT CC CN CX GE HK ID IN IO JP KG KH KP KR KZ LA LK "
        "MM MN MO MV MY NP PH PK SG TH TJ TL TM TR TW UZ VN".split()
    ),
}

COUNTRY_REGIONS = {
    code: region for region, codes in REGION_COUNTRIES.items() for code in codes
}


def region_for_country(country_code: str) -> str:
    return COUNTRY_REGIONS.get(country_code.strip().upper(), "other")
