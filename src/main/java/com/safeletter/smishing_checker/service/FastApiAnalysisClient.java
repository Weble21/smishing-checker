package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.IntegratedAnalysisResult;
import com.safeletter.smishing_checker.exception.ExternalApiException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Set;

@Component
public class FastApiAnalysisClient implements AiAnalysisClient {

    private static final Set<String> ALLOWED_RISK_LEVELS = Set.of(
            "HIGH", "MEDIUM", "LOW"
    );

    private final RestClient restClient;
    private final String endpoint;

    @Autowired
    public FastApiAnalysisClient(
            @Value("${ai.base-url:http://127.0.0.1:8000}") String baseUrl,
            @Value("${ai.connect-timeout:3s}") Duration connectTimeout,
            @Value("${ai.read-timeout:60s}") Duration readTimeout
    ) {
        this(createRestClient(connectTimeout, readTimeout), baseUrl);
    }

    FastApiAnalysisClient(RestClient restClient, String baseUrl) {
        this.restClient = restClient;
        this.endpoint = stripTrailingSlash(baseUrl) + "/analyze";
    }

    @Override
    public IntegratedAnalysisResult analyze(
            byte[] imageBytes,
            String contentType
    ) {
        HttpHeaders partHeaders = new HttpHeaders();
        partHeaders.setContentType(MediaType.parseMediaType(contentType));
        HttpEntity<NamedByteArrayResource> imagePart = new HttpEntity<>(
                new NamedByteArrayResource(
                        imageBytes,
                        filenameFor(contentType)
                ),
                partHeaders
        );
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("image", imagePart);

        try {
            IntegratedAnalysisResult result = restClient.post()
                    .uri(endpoint)
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .onStatus(
                            status -> status.isError(),
                            (request, response) -> {
                                String code = response.getStatusCode().value() == 504
                                        || response.getStatusCode().value() == 408
                                        ? "TIMEOUT"
                                        : "UPSTREAM_ERROR";
                                throw new ExternalApiException(
                                        code,
                                        "분석 서비스가 요청을 처리하지 못했습니다."
                                );
                            }
                    )
                    .body(IntegratedAnalysisResult.class);
            validate(result);
            return result;
        } catch (ExternalApiException exception) {
            throw exception;
        } catch (ResourceAccessException exception) {
            throw new ExternalApiException(
                    isTimeout(exception) ? "TIMEOUT" : "CONNECTION_ERROR",
                    "분석 서비스에 연결할 수 없습니다.",
                    exception
            );
        } catch (RestClientException exception) {
            throw new ExternalApiException(
                    "INVALID_RESPONSE",
                    "분석 서비스 응답을 확인할 수 없습니다.",
                    exception
            );
        }
    }

    private static RestClient createRestClient(
            Duration connectTimeout,
            Duration readTimeout
    ) {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(connectTimeout)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        JdkClientHttpRequestFactory requestFactory =
                new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(readTimeout);
        return RestClient.builder().requestFactory(requestFactory).build();
    }

    private void validate(IntegratedAnalysisResult result) {
        if (result == null
                || !ALLOWED_RISK_LEVELS.contains(result.riskLevel())
                || result.summary() == null
                || result.summary().isBlank()
                || result.reasons() == null
                || result.actions() == null) {
            throw new ExternalApiException(
                    "INVALID_RESPONSE",
                    "분석 서비스 응답 형식이 올바르지 않습니다."
            );
        }
    }

    private boolean isTimeout(Throwable throwable) {
        Throwable current = throwable;
        while (current != null) {
            if (current instanceof java.net.http.HttpTimeoutException
                    || current instanceof java.net.SocketTimeoutException) {
                return true;
            }
            current = current.getCause();
        }
        return false;
    }

    private String filenameFor(String contentType) {
        return MediaType.IMAGE_JPEG_VALUE.equals(contentType)
                ? "message.jpg"
                : "message.png";
    }

    private static String stripTrailingSlash(String value) {
        String result = value == null ? "" : value.strip();
        while (result.endsWith("/")) {
            result = result.substring(0, result.length() - 1);
        }
        return result;
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
