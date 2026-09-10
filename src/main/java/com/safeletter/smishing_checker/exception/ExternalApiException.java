package com.safeletter.smishing_checker.exception;

public class ExternalApiException extends RuntimeException {

    private final String errorCode;

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
