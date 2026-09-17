package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.IntegratedAnalysisResult;
import com.safeletter.smishing_checker.dto.DynamicAnalysisJob;
import com.safeletter.smishing_checker.exception.ExternalApiException;

public interface AiAnalysisClient {

    IntegratedAnalysisResult analyze(byte[] imageBytes, String contentType);

    default DynamicAnalysisJob getDynamicJob(String jobId) {
        throw new ExternalApiException("DYNAMIC_UNAVAILABLE", "동적 분석 결과를 조회할 수 없습니다.");
    }
}
