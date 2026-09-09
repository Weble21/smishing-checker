package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.IntegratedAnalysisResult;

public interface AiAnalysisClient {

    IntegratedAnalysisResult analyze(byte[] imageBytes, String contentType);
}
