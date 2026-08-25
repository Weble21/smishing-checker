package com.safeletter.smishing_checker.dto;

import java.util.List;

public record RuleCheckResult(
        String minimumRiskLevel,
        List<String> reasons,
        List<String> actions
) {

    public RuleCheckResult {
        minimumRiskLevel = minimumRiskLevel == null
                ? "NONE"
                : minimumRiskLevel;
        reasons = reasons == null ? List.of() : List.copyOf(reasons);
        actions = actions == null ? List.of() : List.copyOf(actions);
    }
}
