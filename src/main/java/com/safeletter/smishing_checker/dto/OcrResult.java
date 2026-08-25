package com.safeletter.smishing_checker.dto;

public record OcrResult(
        String text,
        double confidence,
        int lineCount
) {

    public OcrResult {
        text = text == null ? "" : text.strip();
        confidence = Math.max(0, Math.min(1, confidence));
        lineCount = Math.max(0, lineCount);
    }
}
