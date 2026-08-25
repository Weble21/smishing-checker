package com.safeletter.smishing_checker.dto;

import java.util.List;

public record AnalysisResponse(
        String riskLevel,
        String summary,
        List<String> reasons,
        List<String> actions,
        boolean mock,
        String analysisStatus,
        String errorCode
) {
}
