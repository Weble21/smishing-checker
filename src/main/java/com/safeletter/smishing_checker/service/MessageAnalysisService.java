package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.AnalysisResponse;
import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.dto.RuleCheckResult;
import com.safeletter.smishing_checker.dto.VisionAnalysisResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import com.safeletter.smishing_checker.exception.OcrUnavailableException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

@Service
public class MessageAnalysisService {

    private static final long MAX_FILE_SIZE = 10 * 1024 * 1024;

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "image/jpeg",
            "image/png"
    );

    private final VisionAnalyzer visionAnalyzer;
    private final OcrAnalyzer ocrAnalyzer;
    private final MessageRiskRuleChecker ruleChecker;
    private final double minimumOcrConfidence;

    public MessageAnalysisService(
            VisionAnalyzer visionAnalyzer,
            OcrAnalyzer ocrAnalyzer,
            MessageRiskRuleChecker ruleChecker,
            @Value("${ocr.minimum-confidence:0.55}")
            double minimumOcrConfidence
    ) {
        this.visionAnalyzer = visionAnalyzer;
        this.ocrAnalyzer = ocrAnalyzer;
        this.ruleChecker = ruleChecker;
        this.minimumOcrConfidence = minimumOcrConfidence;
    }

    public AnalysisResponse analyze(MultipartFile image) {
        validateImage(image);

        try {
            byte[] imageBytes = image.getBytes();
            OcrResult ocrResult;

            try {
                ocrResult = ocrAnalyzer.extract(
                        imageBytes,
                        image.getContentType()
                );
            } catch (OcrUnavailableException exception) {
                return ocrUnavailableResponse();
            }

            if (ocrResult.text().isBlank()
                    || ocrResult.confidence() < minimumOcrConfidence) {
                return uncertainOcrResponse(ocrResult);
            }

            RuleCheckResult ruleResult = ruleChecker.check(ocrResult.text());
            VisionAnalysisResult aiResult;
            try {
                aiResult = visionAnalyzer.analyze(
                        imageBytes,
                        image.getContentType(),
                        ocrResult,
                        ruleResult
                );
            } catch (ExternalApiException exception) {
                return aiUnavailableResponse(ruleResult, exception.errorCode());
            }
            VisionAnalysisResult result = merge(aiResult, ruleResult);

            return new AnalysisResponse(
                    result.riskLevel(),
                    result.summary(),
                    result.reasons(),
                    result.actions(),
                    false,
                    "SUCCESS",
                    null
            );
        } catch (IOException exception) {
            throw new IllegalArgumentException(
                    "사진을 읽는 중 오류가 발생했습니다."
            );
        }
    }

    private VisionAnalysisResult merge(
            VisionAnalysisResult aiResult,
            RuleCheckResult ruleResult
    ) {
        String riskLevel = aiResult.riskLevel();
        String summary = aiResult.summary();

        if ("HIGH".equals(ruleResult.minimumRiskLevel())
                && !"HIGH".equals(riskLevel)) {
            riskLevel = "HIGH";
            summary = "문자에서 위험 신호가 확인되어 스미싱 가능성이 높습니다.";
        } else if ("MEDIUM".equals(ruleResult.minimumRiskLevel())
                && "LOW".equals(riskLevel)) {
            riskLevel = "MEDIUM";
            summary = "문자에서 확인이 필요한 위험 신호가 발견되었습니다.";
        }

        LinkedHashSet<String> reasons = new LinkedHashSet<>();
        reasons.addAll(ruleResult.reasons());
        reasons.addAll(aiResult.reasons());

        LinkedHashSet<String> actions = new LinkedHashSet<>();
        actions.addAll(ruleResult.actions());
        actions.addAll(aiResult.actions());
        if (("HIGH".equals(riskLevel) || "MEDIUM".equals(riskLevel))
                && actions.stream().noneMatch(
                action -> action.contains("118") || action.contains("112")
        )) {
            actions.add("의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.");
        }

        return new VisionAnalysisResult(
                riskLevel,
                summary,
                List.copyOf(reasons),
                List.copyOf(actions)
        );
    }

    private AnalysisResponse aiUnavailableResponse(
            RuleCheckResult ruleResult,
            String errorCode
    ) {
        LinkedHashSet<String> actions = new LinkedHashSet<>(ruleResult.actions());
        actions.add("문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.");
        actions.add("의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.");

        String ruleRiskLevel = ruleResult.minimumRiskLevel();
        boolean hasDeterministicRisk = "HIGH".equals(ruleRiskLevel)
                || "MEDIUM".equals(ruleRiskLevel);

        return new AnalysisResponse(
                hasDeterministicRisk ? ruleRiskLevel : "REVIEW_REQUIRED",
                hasDeterministicRisk
                        ? "AI 분석은 완료하지 못했지만 서버 규칙에서 위험 신호를 확인했습니다."
                        : "AI 분석을 완료하지 못해 확인이 필요합니다.",
                ruleResult.reasons().isEmpty()
                        ? List.of("현재 자동 분석 결과를 신뢰할 수 없습니다.")
                        : ruleResult.reasons(),
                List.copyOf(actions),
                false,
                "AI_ERROR",
                errorCode
        );
    }

    private AnalysisResponse ocrUnavailableResponse() {
        return new AnalysisResponse(
                "REVIEW_REQUIRED",
                "문자를 읽는 서비스에 연결할 수 없어 확인이 필요합니다.",
                List.of("현재 이미지에서 문자 내용을 추출하지 못했습니다."),
                List.of(
                        "잠시 후 다시 검사해 주세요.",
                        "의심되는 링크나 송금 요청에는 응하지 마세요."
                ),
                false,
                "OCR_ERROR",
                "OCR_UNAVAILABLE"
        );
    }

    private AnalysisResponse uncertainOcrResponse(OcrResult ocrResult) {
        String reason = ocrResult.text().isBlank()
                ? "이미지에서 읽을 수 있는 문자를 찾지 못했습니다."
                : "문자 인식 신뢰도가 낮아 내용을 확정하기 어렵습니다.";

        return new AnalysisResponse(
                "REVIEW_REQUIRED",
                "이미지의 문자 내용이 불분명하여 확인이 필요합니다.",
                List.of(reason),
                List.of(
                        "문자 영역이 선명하게 보이도록 다시 촬영해 주세요.",
                        "의심되는 링크나 송금 요청에는 응하지 마세요."
                ),
                false,
                "OCR_UNCERTAIN",
                ocrResult.text().isBlank()
                        ? "OCR_EMPTY_TEXT"
                        : "OCR_LOW_CONFIDENCE"
        );
    }

    private void validateImage(MultipartFile image) {
        if (image == null || image.isEmpty()) {
            throw new IllegalArgumentException("사진을 선택해주세요.");
        }

        if (image.getSize() > MAX_FILE_SIZE) {
            throw new IllegalArgumentException(
                    "사진은 10MB 이하만 업로드할 수 있어요."
            );
        }

        String contentType = image.getContentType();

        if (contentType == null
                || !ALLOWED_CONTENT_TYPES.contains(contentType)) {
            throw new IllegalArgumentException(
                    "JPG 또는 PNG 사진만 업로드할 수 있어요."
            );
        }

        try {
            if (ImageIO.read(image.getInputStream()) == null) {
                throw new IllegalArgumentException(
                        "올바른 이미지 파일이 아니에요."
                );
            }
        } catch (IOException exception) {
            throw new IllegalArgumentException(
                    "사진을 확인하는 중 오류가 발생했어요."
            );
        }
    }
}
