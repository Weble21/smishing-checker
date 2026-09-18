package com.safeletter.smishing_checker.controller;

import com.safeletter.smishing_checker.dto.AnalysisResponse;
import com.safeletter.smishing_checker.dto.DynamicAnalysisJob;
import com.safeletter.smishing_checker.service.MessageAnalysisService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MessageAnalysisController.class)
class MessageAnalysisControllerTests {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private MessageAnalysisService messageAnalysisService;

    @Test
    void acceptsImageUploadAndKeepsResponseShape() throws Exception {
        when(messageAnalysisService.analyze(any())).thenReturn(
                new AnalysisResponse(
                        "MEDIUM",
                        "주의가 필요합니다.",
                        List.of("확인이 필요한 링크입니다."),
                        List.of("공식 앱에서 확인하세요."),
                        false,
                        "SUCCESS",
                        null,
                        0.82,
                        List.of()
                )
        );
        MockMultipartFile image = new MockMultipartFile(
                "image",
                "message.png",
                "image/png",
                new byte[]{1, 2, 3}
        );

        mockMvc.perform(multipart("/api/v1/messages/analyze").file(image))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.riskLevel").value("MEDIUM"))
                .andExpect(jsonPath("$.summary").value("주의가 필요합니다."))
                .andExpect(jsonPath("$.textRiskScore").value(0.82))
                .andExpect(jsonPath("$.mock").value(false));
    }

    @Test
    void returnsDynamicAnalysisStatus() throws Exception {
        String jobId = "a".repeat(32);
        when(messageAnalysisService.getDynamicJob(jobId)).thenReturn(
                new DynamicAnalysisJob(
                        jobId, "COMPLETED", "https://example.com/",
                        "SUSPICIOUS", "HIGH", "민감정보 입력 폼이 확인되었습니다.",
                        List.of("비밀번호 입력 항목이 있습니다."),
                        List.of("최종 URL: https://example.com/login")
                )
        );

        mockMvc.perform(get("/api/v1/messages/dynamic/{jobId}", jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.riskLevel").value("HIGH"))
                .andExpect(jsonPath("$.evidence[0]").value("최종 URL: https://example.com/login"));
    }
}
