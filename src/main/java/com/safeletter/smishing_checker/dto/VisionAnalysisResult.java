package com.safeletter.smishing_checker.dto;

import java.util.List;

public record VisionAnalysisResult(
        String riskLevel,
        String summary,
        List<String> reasons,
        List<String> actions
) {
}
