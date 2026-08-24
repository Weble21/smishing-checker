package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.AnalysisResponse;
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

    public AnalysisResponse analyze(MultipartFile image) {
        validateImage(image);

        return new AnalysisResponse(
                "HIGH",
                "위험 가능성이 높은 문자예요.",
                List.of(
                        "출처를 확인하기 어려운 링크가 있어요.",
                        "사용자를 급하게 행동하도록 유도해요."
                ),
                List.of(
                        "링크를 누르지 마세요.",
                        "공식 대표번호로 직접 확인하세요.",
                        "의심되면 국번 없이 118에 문의하세요."
                ),
                true
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