package com.safeletter.smishing_checker.exception;

public class ExternalApiException extends RuntimeException {

    private final String errorCode;

    public ExternalApiException(String message) {
        this("UPSTREAM_ERROR", message);
    }

    public ExternalApiException(String message, Throwable cause) {
        this("UPSTREAM_ERROR", message, cause);
    }

    public ExternalApiException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public ExternalApiException(
            String errorCode,
            String message,
            Throwable cause
    ) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String errorCode() {
        return errorCode;
    }
}
