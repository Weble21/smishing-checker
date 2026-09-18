package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.exception.ExternalApiException;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class FastApiAnalysisClientTests {

    @Test
    void parsesIntegratedResponse() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://localhost:8000/analyze"))
                .andRespond(withSuccess("""
                        {
                          "ocrText": "문자",
                          "textAnalysis": {"label": "NORMAL", "riskScore": 0.1},
                          "urlAnalysis": [],
                          "riskLevel": "LOW",
                          "summary": "뚜렷한 위험 요소가 없습니다.",
                          "reasons": ["위험 신호가 없습니다."],
                          "actions": ["공식 연락처로 확인하세요."]
                        }
                        """, MediaType.APPLICATION_JSON));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(),
                "http://localhost:8000/"
        );

        var result = client.analyze(new byte[]{1, 2, 3}, "image/png");

        assertEquals("LOW", result.riskLevel());
        assertEquals("NORMAL", result.textAnalysis().label());
        server.verify();
    }

    @Test
    void rejectsMalformedJson() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://localhost:8000/analyze"))
                .andRespond(withSuccess("not-json", MediaType.APPLICATION_JSON));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(),
                "http://localhost:8000"
        );

        ExternalApiException exception = assertThrows(
                ExternalApiException.class,
                () -> client.analyze(new byte[]{1}, "image/png")
        );
        assertEquals("INVALID_RESPONSE", exception.errorCode());
    }

    @Test
    void fetchesDynamicAnalysisStatus() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String jobId = "a".repeat(32);
        server.expect(requestTo("http://localhost:8000/dynamic/jobs/" + jobId))
                .andRespond(withSuccess("""
                        {
                          "jobId": "%s",
                          "status": "COMPLETED",
                          "requestedUrl": "https://example.com/",
                          "verdict": "SUSPICIOUS",
                          "riskLevel": "HIGH",
                          "summary": "민감정보 입력 폼이 확인되었습니다.",
                          "reasons": ["비밀번호 입력 항목이 있습니다."],
                          "evidence": ["최종 URL: https://example.com/login"]
                        }
                        """.formatted(jobId), MediaType.APPLICATION_JSON));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(), "http://localhost:8000"
        );

        var result = client.getDynamicJob(jobId);

        assertEquals("HIGH", result.riskLevel());
        assertEquals(List.of("비밀번호 입력 항목이 있습니다."), result.reasons());
        assertEquals(List.of("최종 URL: https://example.com/login"), result.evidence());
        server.verify();
    }

    @Test
    void preservesMissingDynamicJobAsNotFound() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String jobId = "a".repeat(32);
        server.expect(requestTo("http://localhost:8000/dynamic/jobs/" + jobId))
                .andRespond(withStatus(HttpStatus.NOT_FOUND));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(), "http://localhost:8000"
        );

        ResponseStatusException exception = assertThrows(
                ResponseStatusException.class,
                () -> client.getDynamicJob(jobId)
        );
        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
        server.verify();
    }

    @Test
    void rejectsMissingRiskLevel() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://localhost:8000/analyze"))
                .andRespond(withSuccess("""
                        {"summary": "분석 결과", "reasons": [], "actions": []}
                        """, MediaType.APPLICATION_JSON));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(), "http://localhost:8000"
        );

        ExternalApiException exception = assertThrows(
                ExternalApiException.class,
                () -> client.analyze(new byte[]{1}, "image/png")
        );
        assertEquals("INVALID_RESPONSE", exception.errorCode());
        server.verify();
    }

    @Test
    void mapsTimeout() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://localhost:8000/analyze"))
                .andRespond(withException(new SocketTimeoutException("timeout")));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(),
                "http://localhost:8000"
        );

        ExternalApiException exception = assertThrows(
                ExternalApiException.class,
                () -> client.analyze(new byte[]{1}, "image/png")
        );
        assertEquals("TIMEOUT", exception.errorCode());
    }

    @Test
    void mapsConnectionFailure() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://localhost:8000/analyze"))
                .andRespond(withException(new IOException("connection refused")));
        FastApiAnalysisClient client = new FastApiAnalysisClient(
                builder.build(),
                "http://localhost:8000"
        );

        ExternalApiException exception = assertThrows(
                ExternalApiException.class,
                () -> client.analyze(new byte[]{1}, "image/png")
        );
        assertEquals("CONNECTION_ERROR", exception.errorCode());
    }
}
