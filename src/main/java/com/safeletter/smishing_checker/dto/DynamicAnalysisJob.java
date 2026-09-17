package com.safeletter.smishing_checker.dto;

import java.util.List;

public record DynamicAnalysisJob(
        String jobId,
        String status,
        String requestedUrl,
        String verdict,
        String riskLevel,
        String summary,
        List<String> reasons
) {
}
