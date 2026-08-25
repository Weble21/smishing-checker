package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.dto.VisionAnalysisResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import com.safeletter.smishing_checker.exception.OcrUnavailableException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Base64;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MessageAnalysisServiceTests {

    private static final byte[] ONE_PIXEL_PNG = Base64.getDecoder().decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    );

    @Test
    void returnsVisionAnalysisAsNonMockResult() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) ->
                new VisionAnalysisResult(
                        "HIGH",
                        "위험 가능성이 있습니다.",
                        List.of("송금을 요구합니다."),
                        List.of("118에 문의하세요.")
                );
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "계좌로 송금해 주세요.",
                        0.95,
                        1
                )
        );
        MockMultipartFile image = new MockMultipartFile(
                "image",
                "message.png",
                "image/png",
                ONE_PIXEL_PNG
        );

        var result = service.analyze(image);

        assertEquals("HIGH", result.riskLevel());
        assertFalse(result.mock());
        assertEquals("SUCCESS", result.analysisStatus());
    }

    @Test
    void rejectsNonImageContent() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) -> {
            throw new AssertionError("검증 실패 파일은 AI에 전달되면 안 됩니다.");
        };
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> {
                    throw new AssertionError("검증 실패 파일은 OCR에 전달되면 안 됩니다.");
                }
        );
        MockMultipartFile image = new MockMultipartFile(
                "image",
                "message.txt",
                "text/plain",
                "not an image".getBytes()
        );

        assertThrows(IllegalArgumentException.class, () -> service.analyze(image));
    }

    @Test
    void rejectsCorruptedImageWithAllowedContentType() {
        MessageAnalysisService service = service(
                (bytes, contentType, ocr, rules) -> {
                    throw new AssertionError("손상 이미지는 AI에 전달되면 안 됩니다.");
                },
                (bytes, contentType) -> {
                    throw new AssertionError("손상 이미지는 OCR에 전달되면 안 됩니다.");
                }
        );
        MockMultipartFile image = new MockMultipartFile(
                "image",
                "broken.png",
                "image/png",
                "not a png".getBytes()
        );

        assertThrows(IllegalArgumentException.class, () -> service.analyze(image));
    }

    @Test
    void rejectsImageLargerThanTenMegabytes() {
        MessageAnalysisService service = service(
                (bytes, contentType, ocr, rules) -> {
                    throw new AssertionError("대용량 이미지는 AI에 전달되면 안 됩니다.");
                },
                (bytes, contentType) -> {
                    throw new AssertionError("대용량 이미지는 OCR에 전달되면 안 됩니다.");
                }
        );
        MockMultipartFile image = new MockMultipartFile(
                "image",
                "large.png",
                "image/png",
                new byte[10 * 1024 * 1024 + 1]
        );

        assertThrows(IllegalArgumentException.class, () -> service.analyze(image));
    }

    @Test
    void returnsReviewRequiredWhenOcrIsUnavailable() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) -> {
            throw new AssertionError("OCR 실패 이미지는 AI에 전달되면 안 됩니다.");
        };
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> {
                    throw new OcrUnavailableException("offline");
                }
        );

        var result = service.analyze(validImage());

        assertEquals("REVIEW_REQUIRED", result.riskLevel());
        assertEquals("OCR_ERROR", result.analysisStatus());
        assertEquals("OCR_UNAVAILABLE", result.errorCode());
    }

    @Test
    void returnsReviewRequiredForLowConfidenceOcr() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) -> {
            throw new AssertionError("불확실한 OCR 결과는 AI에 전달되면 안 됩니다.");
        };
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult("문자", 0.2, 1)
        );

        var result = service.analyze(validImage());

        assertEquals("REVIEW_REQUIRED", result.riskLevel());
        assertEquals("OCR_UNCERTAIN", result.analysisStatus());
        assertEquals("OCR_LOW_CONFIDENCE", result.errorCode());
    }

    @Test
    void ruleBasedHighRiskOverridesLowAiRisk() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) ->
                new VisionAnalysisResult(
                        "LOW",
                        "특별한 위험 신호가 없습니다.",
                        List.of("일상적인 문자입니다."),
                        List.of()
                );
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "엄마, 계좌로 48만원 보내줘.",
                        0.98,
                        1
                )
        );

        var result = service.analyze(validImage());

        assertEquals("HIGH", result.riskLevel());
        assertTrue(result.actions().stream().anyMatch(
                action -> action.contains("118") || action.contains("112")
        ));
    }

    @Test
    void keepsRoutineDeliveryNoticeLow() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) ->
                new VisionAnalysisResult(
                        "LOW",
                        "일반적인 배송 예정 안내입니다.",
                        List.of("링크, 송금, 개인정보 요구가 없습니다."),
                        List.of("주문한 쇼핑몰 공식 앱에서 확인하세요.")
                );
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "OO택배 상품이 오늘 오후 도착 예정입니다. 공식 앱에서 확인해 주세요.",
                        0.98,
                        1
                )
        );

        var result = service.analyze(validImage());

        assertEquals("LOW", result.riskLevel());
    }

    @Test
    void mediumRiskIncludes118Or112Guidance() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) ->
                new VisionAnalysisResult(
                        "MEDIUM",
                        "확인이 필요한 링크가 있습니다.",
                        List.of("문자에 URL이 있습니다."),
                        List.of("공식 앱에서 확인하세요.")
                );
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "배송 현황 https://example.com/order",
                        0.98,
                        1
                )
        );

        var result = service.analyze(validImage());

        assertEquals("MEDIUM", result.riskLevel());
        assertTrue(result.actions().stream().anyMatch(
                action -> action.contains("118") || action.contains("112")
        ));
    }

    @Test
    void returnsReviewRequiredWhenAiFails() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) -> {
            throw new ExternalApiException("timeout");
        };
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "택배가 오늘 도착 예정입니다.",
                        0.98,
                        1
                )
        );

        var result = service.analyze(validImage());

        assertEquals("REVIEW_REQUIRED", result.riskLevel());
        assertTrue(result.summary().contains("확인"));
        assertEquals("AI_ERROR", result.analysisStatus());
        assertEquals("UPSTREAM_ERROR", result.errorCode());
    }

    @Test
    void preservesRuleBasedHighRiskWhenAiFails() {
        VisionAnalyzer analyzer = (bytes, contentType, ocr, rules) -> {
            throw new ExternalApiException("RATE_LIMIT", "rate limited");
        };
        MessageAnalysisService service = service(
                analyzer,
                (bytes, contentType) -> new OcrResult(
                        "안전계좌로 전액 이체하세요.",
                        0.98,
                        1
                )
        );

        var result = service.analyze(validImage());

        assertEquals("HIGH", result.riskLevel());
        assertEquals("AI_ERROR", result.analysisStatus());
        assertEquals("RATE_LIMIT", result.errorCode());
    }

    private MessageAnalysisService service(
            VisionAnalyzer analyzer,
            OcrAnalyzer ocrAnalyzer
    ) {
        return new MessageAnalysisService(
                analyzer,
                ocrAnalyzer,
                new MessageRiskRuleChecker(),
                0.55
        );
    }

    private MockMultipartFile validImage() {
        return new MockMultipartFile(
                "image",
                "message.png",
                "image/png",
                ONE_PIXEL_PNG
        );
    }
}
