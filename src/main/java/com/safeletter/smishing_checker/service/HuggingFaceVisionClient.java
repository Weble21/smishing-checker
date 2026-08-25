package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.VisionAnalysisResult;
import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.dto.RuleCheckResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Base64;
import java.util.List;
import java.util.Map;

@Component
public class HuggingFaceVisionClient implements VisionAnalyzer {

    private static final String ANALYSIS_PROMPT = """
            이 이미지는 사용자가 받은 문자 메시지의 화면 캡처입니다.
            스미싱 위험을 분석하고 한국어로 답하세요.

            다음 원칙을 반드시 지키세요.
            - 이미지와 서버 OCR 텍스트를 서로 비교해 문자를 정확히 읽습니다.
            - URL, 송금 요구, 개인정보 또는 인증정보 요구, 긴급성 유도를 확인합니다.
            - 서버 규칙 검사에서 발견한 위험 신호를 반드시 판단 근거에 반영합니다.
            - 안전을 확정하거나 '100% 안전'이라고 표현하지 않습니다.
            - 이미지와 OCR 결과가 크게 다르거나 판단 근거가 부족하면 REVIEW_REQUIRED로 분류합니다.
            - HIGH이면 링크를 누르지 말 것과 118 또는 112 문의를 actions에 포함합니다.
            - 이미지에 없는 사실을 추측하지 않습니다.
            """;

    private static final Map<String, Object> RESPONSE_SCHEMA = Map.of(
            "type", "object",
            "additionalProperties", false,
            "properties", Map.of(
                    "riskLevel", Map.of(
                            "type", "string",
                            "enum", List.of(
                                    "HIGH", "MEDIUM", "LOW", "REVIEW_REQUIRED"
                            )
                    ),
                    "summary", Map.of("type", "string"),
                    "reasons", Map.of(
                            "type", "array",
                            "items", Map.of("type", "string")
                    ),
                    "actions", Map.of(
                            "type", "array",
                            "items", Map.of("type", "string")
                    )
            ),
            "required", List.of(
                    "riskLevel", "summary", "reasons", "actions"
            )
    );

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String token;
    private final String apiUrl;
    private final String model;

    public HuggingFaceVisionClient(
            ObjectMapper objectMapper,
            @Value("${huggingface.token:}") String token,
            @Value("${huggingface.api-url}") String apiUrl,
            @Value("${huggingface.model}") String model
    ) {
        String normalizedToken = normalizeToken(token);
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory requestFactory =
                new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(Duration.ofSeconds(45));

        this.restClient = RestClient.builder()
                .requestFactory(requestFactory)
                .defaultHeader("Authorization", "Bearer " + normalizedToken)
                .build();
        this.objectMapper = objectMapper;
        this.token = normalizedToken;
        this.apiUrl = apiUrl;
        this.model = model;
    }

    @Override
    public VisionAnalysisResult analyze(
            byte[] imageBytes,
            String contentType,
            OcrResult ocrResult,
            RuleCheckResult ruleCheckResult
    ) {
        if (token.isBlank()) {
            throw new ExternalApiException(
                    "AI 분석 서비스 설정이 완료되지 않았습니다."
            );
        }

        String imageUrl = "data:" + contentType + ";base64,"
                + Base64.getEncoder().encodeToString(imageBytes);

        Map<String, Object> requestBody = Map.of(
                "model", model,
                "stream", false,
                "temperature", 0,
                "max_tokens", 700,
                "messages", List.of(Map.of(
                        "role", "user",
                        "content", List.of(
                                Map.of(
                                        "type", "text",
                                        "text", buildPrompt(
                                                ocrResult,
                                                ruleCheckResult
                                        )
                                ),
                                Map.of(
                                        "type", "image_url",
                                        "image_url", Map.of("url", imageUrl)
                                )
                        )
                )),
                "response_format", Map.of(
                        "type", "json_schema",
                        "json_schema", Map.of(
                                "name", "smishing_analysis",
                                "strict", true,
                                "schema", RESPONSE_SCHEMA
                        )
                )
        );

        try {
            JsonNode response = restClient.post()
                    .uri(apiUrl)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(requestBody)
                    .retrieve()
                    .onStatus(
                            HttpStatusCode::isError,
                            (request, apiResponse) -> {
                                throw apiError(apiResponse.getStatusCode());
                            }
                    )
                    .body(JsonNode.class);

            return parseAnalysis(response);
        } catch (ExternalApiException exception) {
            throw exception;
        } catch (RestClientException exception) {
            throw new ExternalApiException(
                    "AI 분석 서비스 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.",
                    exception
            );
        }
    }

    private String buildPrompt(
            OcrResult ocrResult,
            RuleCheckResult ruleCheckResult
    ) {
        String ruleReasons = ruleCheckResult.reasons().isEmpty()
                ? "발견된 규칙 기반 위험 신호 없음"
                : String.join("\n- ", ruleCheckResult.reasons());

        return ANALYSIS_PROMPT + """

                [서버 OCR 결과]
                신뢰도: %.2f
                ---
                %s
                ---

                [서버 규칙 검사]
                최소 위험도: %s
                - %s
                """.formatted(
                ocrResult.confidence(),
                ocrResult.text(),
                ruleCheckResult.minimumRiskLevel(),
                ruleReasons
        );
    }

    private VisionAnalysisResult parseAnalysis(JsonNode response) {
        JsonNode content = response == null
                ? null
                : response.path("choices").path(0).path("message").path("content");
        if (content == null || !content.isTextual() || content.asText().isBlank()) {
            throw new ExternalApiException("AI 분석 결과 형식이 올바르지 않습니다.");
        }

        try {
            VisionAnalysisResult result = objectMapper.readValue(
                    content.asText(),
                    VisionAnalysisResult.class
            );
            validateResult(result);
            return result;
        } catch (JacksonException | IllegalArgumentException exception) {
            throw new ExternalApiException(
                    "AI 분석 결과 형식이 올바르지 않습니다.",
                    exception
            );
        }
    }

    private void validateResult(VisionAnalysisResult result) {
        if (result == null
                || result.riskLevel() == null
                || result.summary() == null
                || result.summary().isBlank()
                || result.reasons() == null
                || result.actions() == null
                || !List.of(
                        "HIGH", "MEDIUM", "LOW", "REVIEW_REQUIRED"
                ).contains(result.riskLevel())) {
            throw new IllegalArgumentException("필수 분석 결과가 없습니다.");
        }

        String allText = String.join(
                " ",
                result.summary(),
                String.join(" ", result.reasons()),
                String.join(" ", result.actions())
        );
        if (allText.contains("100% 안전")) {
            throw new IllegalArgumentException("금지된 확정 표현이 있습니다.");
        }
    }

    private ExternalApiException apiError(HttpStatusCode statusCode) {
        return switch (statusCode.value()) {
            case 400, 422 -> new ExternalApiException(
                    "AI 분석 요청 형식이 올바르지 않습니다."
            );
            case 401, 403 -> new ExternalApiException(
                    "AI 분석 서비스 인증 또는 권한 설정을 확인해 주세요."
            );
            case 402 -> new ExternalApiException(
                    "Hugging Face 무료 사용 한도가 부족합니다."
            );
            case 429 -> new ExternalApiException(
                    "AI 분석 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            );
            default -> new ExternalApiException(
                    "AI 분석 서비스가 요청을 처리하지 못했습니다."
            );
        };
    }

    private String normalizeToken(String token) {
        if (token == null) {
            return "";
        }

        String value = token.trim();
        if (value.length() >= 2
                && ((value.startsWith("\"") && value.endsWith("\""))
                || (value.startsWith("'") && value.endsWith("'")))) {
            return value.substring(1, value.length() - 1).trim();
        }
        return value;
    }
}
