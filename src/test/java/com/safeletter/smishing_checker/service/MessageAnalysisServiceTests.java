package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.dto.VisionAnalysisResult;
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
