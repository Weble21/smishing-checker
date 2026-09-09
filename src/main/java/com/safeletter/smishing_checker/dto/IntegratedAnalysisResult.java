package com.safeletter.smishing_checker.dto;

import java.util.List;

public record IntegratedAnalysisResult(
        String ocrText,
        TextAnalysis textAnalysis,
        List<UrlAnalysis> urlAnalysis,
        String riskLevel,
        String summary,
        List<String> reasons,
        List<String> actions
) {
    public record TextAnalysis(String label, double riskScore) {
    }

    public record UrlAnalysis(
            String url,
            String hostname,
            String verdict,
            double riskScore,
            List<String> reasons,
            Reputation reputation
    ) {
    }

    public record Reputation(
            String status,
            int malicious,
            int suspicious
    ) {
    }
}
