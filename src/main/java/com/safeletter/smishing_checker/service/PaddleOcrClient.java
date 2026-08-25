package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.OcrResult;
import com.safeletter.smishing_checker.exception.OcrUnavailableException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.net.http.HttpClient;
import java.time.Duration;

@Component
public class PaddleOcrClient implements OcrAnalyzer {

    private final RestClient restClient;
    private final String apiUrl;

    public PaddleOcrClient(@Value("${ocr.api-url}") String apiUrl) {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        JdkClientHttpRequestFactory requestFactory =
                new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(Duration.ofSeconds(30));

        this.restClient = RestClient.builder()
                .requestFactory(requestFactory)
                .build();
        this.apiUrl = apiUrl;
    }

    @Override
    public OcrResult extract(byte[] imageBytes, String contentType) {
        HttpHeaders partHeaders = new HttpHeaders();
        partHeaders.setContentType(MediaType.parseMediaType(contentType));
        HttpEntity<NamedByteArrayResource> imagePart = new HttpEntity<>(
                new NamedByteArrayResource(imageBytes, filenameFor(contentType)),
                partHeaders
        );
        MultiValueMap<String, Object> multipartBody = new LinkedMultiValueMap<>();
        multipartBody.add("image", imagePart);

        try {
            OcrApiResponse response = restClient.post()
                    .uri(apiUrl)
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(multipartBody)
                    .retrieve()
                    .onStatus(
                            status -> status.isError(),
                            (request, apiResponse) -> {
                                throw new OcrUnavailableException(
                                        "OCR 서비스가 이미지를 처리하지 못했습니다."
                                );
                            }
                    )
                    .body(OcrApiResponse.class);

            if (response == null) {
                throw new OcrUnavailableException(
                        "OCR 서비스 응답이 비어 있습니다."
                );
            }

            return new OcrResult(
                    response.text(),
                    response.confidence(),
                    response.lineCount()
            );
        } catch (OcrUnavailableException exception) {
            throw exception;
        } catch (RestClientException exception) {
            throw new OcrUnavailableException(
                    "OCR 서비스에 연결할 수 없습니다.",
                    exception
            );
        }
    }

    private String filenameFor(String contentType) {
        return MediaType.IMAGE_JPEG_VALUE.equals(contentType)
                ? "message.jpg"
                : "message.png";
    }

    private record OcrApiResponse(
            String text,
            double confidence,
            int lineCount
    ) {
    }

    private static class NamedByteArrayResource extends ByteArrayResource {

        private final String filename;

        NamedByteArrayResource(byte[] byteArray, String filename) {
            super(byteArray);
            this.filename = filename;
        }

        @Override
        public String getFilename() {
            return filename;
        }
    }
}
