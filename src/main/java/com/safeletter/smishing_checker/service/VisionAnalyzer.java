package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.VisionAnalysisResult;
import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.dto.RuleCheckResult;

public interface VisionAnalyzer {

    VisionAnalysisResult analyze(
            byte[] imageBytes,
            String contentType,
            OcrResult ocrResult,
            RuleCheckResult ruleCheckResult
    );
}
