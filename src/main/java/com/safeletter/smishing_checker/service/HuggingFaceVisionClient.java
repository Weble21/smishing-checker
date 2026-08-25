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

            다음 순서로 판단하세요.
            1. URL, 송금 요청, 개인정보 요청, 인증번호 요청, 긴급 행동 요구가 실제로 있는지 각각 확인합니다.
            2. 단순 완료·예정 알림인지, 사용자가 새 행동을 해야 하는 요청인지 구분합니다.
            3. '필요하지 않습니다', '회신하지 않아도 됩니다' 같은 부정 표현을 요청으로 해석하지 않습니다.
            4. 관찰한 위험 신호의 조합으로만 위험도를 결정합니다.

            판정 기준을 반드시 지키세요.
            - 이미지와 서버 OCR 텍스트를 서로 비교해 문자를 정확히 읽습니다.
            - URL, 송금 요구, 개인정보 또는 인증정보 요구, 긴급성 유도를 관찰 가능한 근거로 확인합니다.
            - 서버 규칙 검사에서 발견한 위험 신호를 반드시 판단 근거에 반영합니다.
            - 택배, 은행, 공공기관 등 발신자 이름이나 소재만으로 사칭이라고 판단하지 않습니다.
            - 링크·송금·개인정보 요구가 없는 배송 예정/완료, 예약, 결제 완료 같은 일상 알림은 원칙적으로 LOW입니다.
            - HIGH는 명시적인 송금·개인정보 요구 또는 URL과 사칭/긴급 유도가 함께 있을 때 사용합니다.
            - MEDIUM은 URL은 있으나 추가 위험 신호가 부족하거나 확인이 필요한 경우에 사용합니다.
            - 위험 신호가 없으면 LOW로 분류하고, 근거 없는 주의 문구나 118·112 안내를 추가하지 않습니다.
            - 안전을 확정하거나 '100% 안전'이라고 표현하지 않습니다.
            - 이미지와 OCR 결과가 크게 다르거나 판단 근거가 부족하면 REVIEW_REQUIRED로 분류합니다.
            - HIGH 또는 MEDIUM이면 링크를 누르지 말 것과 118 또는 112 문의를 actions에 포함합니다.
            - 이미지에 없는 사실을 추측하지 않습니다.

            다음 대조 예시를 기준으로 삼으세요.

            [정상 배송 알림]
            문자: 상품이 오늘 오후 도착 예정입니다. 공식 앱에서 확인해 주세요.
            관찰: URL 없음, 송금 없음, 개인정보 요구 없음, 새 행동 요구 없음
            판정: LOW

            [택배 사칭 위험]
            문자: 주소 오류로 반송 예정입니다. 오늘 안에 주소를 입력하세요. hxxps://parcel[.]invalid
            관찰: URL 있음, 개인정보 입력 유도, 긴급 행동 요구
            판정: HIGH

            [정상 입금 알림]
            문자: 계좌에 50,000원이 입금되었습니다. 회신할 필요가 없습니다.
            관찰: 완료 통지, 송금 요청 없음, 부정 표현 있음
            판정: LOW

            [송금 사기 위험]
            문자: 안전계좌로 전액 이체하세요.
            관찰: 명시적인 송금 행동 요구
            판정: HIGH

            summary에는 위험도 단어만 쓰지 말고 판단을 한 문장으로 설명하세요.
            reasons와 actions에는 각각 한 개 이상의 구체적인 문장을 작성하세요.
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
                    "CONFIGURATION_ERROR",
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
                    isTimeout(exception) ? "TIMEOUT" : "CONNECTION_ERROR",
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
            throw new ExternalApiException(
                    "INVALID_RESPONSE",
                    "AI 분석 결과 형식이 올바르지 않습니다."
            );
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
                    "INVALID_RESPONSE",
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
                || result.reasons().isEmpty()
                || result.actions().isEmpty()
                || result.reasons().stream().anyMatch(
                        reason -> reason == null || reason.isBlank()
                )
                || result.actions().stream().anyMatch(
                        action -> action == null || action.isBlank()
                )
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
        if (allText.matches("(?s).*100\\s*%\\s*안전.*")) {
            throw new IllegalArgumentException("금지된 확정 표현이 있습니다.");
        }
    }

    private ExternalApiException apiError(HttpStatusCode statusCode) {
        return switch (statusCode.value()) {
            case 400, 422 -> new ExternalApiException(
                    "INVALID_REQUEST",
                    "AI 분석 요청 형식이 올바르지 않습니다."
            );
            case 401, 403 -> new ExternalApiException(
                    "AUTH_ERROR",
                    "AI 분석 서비스 인증 또는 권한 설정을 확인해 주세요."
            );
            case 402 -> new ExternalApiException(
                    "QUOTA_EXCEEDED",
                    "Hugging Face 무료 사용 한도가 부족합니다."
            );
            case 429 -> new ExternalApiException(
                    "RATE_LIMIT",
                    "AI 분석 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            );
            default -> new ExternalApiException(
                    "UPSTREAM_ERROR",
                    "AI 분석 서비스가 요청을 처리하지 못했습니다."
            );
        };
    }

    private boolean isTimeout(Throwable throwable) {
        Throwable current = throwable;
        while (current != null) {
            if (current.getClass().getSimpleName().contains("Timeout")) {
                return true;
            }
            current = current.getCause();
        }
        return false;
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
