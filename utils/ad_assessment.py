import pandas as pd


def assess_single_compound_ad(feature_row, ad_reference):
    checked_features = []
    outside_features = []

    for feature_name, stats in ad_reference.items():
        if feature_name not in feature_row.index:
            continue
        value = feature_row[feature_name]
        try:
            value = float(value)
            min_value = float(stats["min"])
            max_value = float(stats["max"])
        except Exception:
            continue

        checked_features.append(feature_name)
        if value < min_value or value > max_value:
            outside_features.append(feature_name)

    total_checked = len(checked_features)

    if total_checked == 0:
        return {
            "applicability_domain": "AD not available",
            "ad_inside_ratio": 0.0,
            "ad_features_checked": 0,
            "ad_outside_features_count": 0,
            "ad_outside_features_preview": ""
        }

    inside_count = total_checked - len(outside_features)
    inside_ratio = inside_count / total_checked

    if inside_ratio >= 0.90:
        ad_status = "Inside AD"
    elif inside_ratio >= 0.75:
        ad_status = "Borderline AD"
    else:
        ad_status = "Outside AD"

    return {
        "applicability_domain": ad_status,
        "ad_inside_ratio": round(inside_ratio, 3),
        "ad_features_checked": total_checked,
        "ad_outside_features_count": len(outside_features),
        "ad_outside_features_preview": ", ".join(outside_features[:8])
    }


def assess_applicability_domain_for_features(X_model, ad_reference):
    ad_rows = []
    for _, row in X_model.iterrows():
        ad_rows.append(assess_single_compound_ad(feature_row=row, ad_reference=ad_reference))
    return pd.DataFrame(ad_rows)
