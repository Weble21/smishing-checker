package com.safeletter.smishing_checker.dto;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;

class AnalysisResponseTests {

    @Test
    void serializesExistingResponseShape() throws Exception {
        AnalysisResponse response = new AnalysisResponse(
                "MEDIUM",
                "주의가 필요합니다.",
                List.of("확인이 필요한 URL입니다."),
                List.of("공식 앱에서 확인하세요."),
                false,
                "SUCCESS",
                null
        );

        String json = new ObjectMapper().writeValueAsString(response);

        assertTrue(json.contains("\"riskLevel\":\"MEDIUM\""));
        assertTrue(json.contains("\"mock\":false"));
    }
}
