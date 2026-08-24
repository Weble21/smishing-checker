package com.safeletter.smishing_checker.controller;

import com.safeletter.smishing_checker.dto.AnalysisResponse;
import com.safeletter.smishing_checker.service.MessageAnalysisService;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/messages")
public class MessageAnalysisController {

    private final MessageAnalysisService messageAnalysisService;

    public MessageAnalysisController(
            MessageAnalysisService messageAnalysisService
    ) {
        this.messageAnalysisService = messageAnalysisService;
    }

    @PostMapping(
            value = "/analyze",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public ResponseEntity<AnalysisResponse> analyze(
            @RequestPart("image") MultipartFile image
    ) {
        AnalysisResponse response =
                messageAnalysisService.analyze(image);

        return ResponseEntity.ok(response);
    }
}