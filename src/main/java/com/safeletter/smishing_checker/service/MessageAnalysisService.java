package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.AnalysisResponse;
import com.safeletter.smishing_checker.dto.IntegratedAnalysisResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import java.io.IOException;
import java.util.List;
import java.util.Set;

@Service
public class MessageAnalysisService {

    private static final long MAX_FILE_SIZE = 10 * 1024 * 1024;
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "image/jpeg",
            "image/png"
    );

    private final AiAnalysisClient analysisClient;

    public MessageAnalysisService(AiAnalysisClient analysisClient) {
        this.analysisClient = analysisClient;
    }

    public AnalysisResponse analyze(MultipartFile image) {
        validateImage(image);
        try {
            byte[] imageBytes = image.getBytes();
            IntegratedAnalysisResult result = analysisClient.analyze(
                    imageBytes,
                    image.getContentType()
            );
            return new AnalysisResponse(
                    result.riskLevel(),
                    result.summary(),
                    List.copyOf(result.reasons()),
                    List.copyOf(result.actions()),
                    false,
                    "SUCCESS",
                    null
            );
        } catch (ExternalApiException exception) {
            return unavailableResponse(exception.errorCode());
        } catch (IOException exception) {
            throw new IllegalArgumentException(
                    "사진을 읽는 중 오류가 발생했습니다."
            );
        }
    }

    private AnalysisResponse unavailableResponse(String errorCode) {
        return new AnalysisResponse(
                "REVIEW_REQUIRED",
                "자동 분석을 완료하지 못해 직접 확인이 필요합니다.",
                List.of("현재 분석 결과를 신뢰할 수 없어 위험도를 확정하지 않았습니다."),
                List.of(
                        "문자 속 링크를 누르거나 송금·개인정보 요구에 응하지 마세요.",
                        "잠시 후 다시 검사하거나 국번 없이 118에 문의하세요."
                ),
                false,
                "AI_ERROR",
                errorCode
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
