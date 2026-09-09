package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.IntegratedAnalysisResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Base64;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

class MessageAnalysisServiceTests {

    private static final byte[] ONE_PIXEL_PNG = Base64.getDecoder().decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    );

    @Test
    void convertsSuccessfulFastApiResponse() {
        AiAnalysisClient client = (bytes, contentType) -> successResult();
        MessageAnalysisService service = new MessageAnalysisService(client);

        var result = service.analyze(validImage());

        assertEquals("HIGH", result.riskLevel());
        assertEquals("위험 신호가 확인되었습니다.", result.summary());
        assertFalse(result.mock());
        assertEquals("SUCCESS", result.analysisStatus());
    }

    @Test
    void returnsReviewRequiredWhenFastApiConnectionFails() {
        AiAnalysisClient client = (bytes, contentType) -> {
            throw new ExternalApiException(
                    "CONNECTION_ERROR",
                    "offline"
            );
        };
        MessageAnalysisService service = new MessageAnalysisService(client);

        var result = service.analyze(validImage());

        assertEquals("REVIEW_REQUIRED", result.riskLevel());
        assertEquals("AI_ERROR", result.analysisStatus());
        assertEquals("CONNECTION_ERROR", result.errorCode());
    }

    @Test
    void returnsReviewRequiredWhenFastApiTimesOut() {
        AiAnalysisClient client = (bytes, contentType) -> {
            throw new ExternalApiException("TIMEOUT", "timeout");
        };
        MessageAnalysisService service = new MessageAnalysisService(client);

        var result = service.analyze(validImage());

        assertEquals("REVIEW_REQUIRED", result.riskLevel());
        assertEquals("TIMEOUT", result.errorCode());
    }

    @Test
    void rejectsNonImageContent() {
        MessageAnalysisService service = new MessageAnalysisService(
                (bytes, contentType) -> {
                    throw new AssertionError("검증 실패 파일은 전달되면 안 됩니다.");
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
        MessageAnalysisService service = new MessageAnalysisService(
                (bytes, contentType) -> {
                    throw new AssertionError("손상 이미지는 전달되면 안 됩니다.");
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
        MessageAnalysisService service = new MessageAnalysisService(
                (bytes, contentType) -> {
                    throw new AssertionError("대용량 이미지는 전달되면 안 됩니다.");
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

    private IntegratedAnalysisResult successResult() {
        return new IntegratedAnalysisResult(
                "계좌로 송금해 주세요.",
                new IntegratedAnalysisResult.TextAnalysis("RISK", 0.98),
                List.of(),
                "HIGH",
                "위험 신호가 확인되었습니다.",
                List.of("송금을 요구합니다."),
                List.of("118에 문의하세요.")
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
