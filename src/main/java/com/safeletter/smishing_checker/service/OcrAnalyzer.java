package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.OcrResult;

public interface OcrAnalyzer {

    OcrResult extract(byte[] imageBytes, String contentType);
}
