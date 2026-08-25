param(
    [string]$BaseUrl = "http://127.0.0.1:18080",
    [string]$ManifestPath = "evaluation/labels.json",
    [string]$ImageDirectory = "evaluation/images",
    [string]$ResultDirectory = "evaluation/results",
    [ValidateRange(1, 10)]
    [int]$MaxAttempts = 3,
    [ValidateRange(0, 60000)]
    [int]$RequestDelayMilliseconds = 1500
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$manifestFullPath = Join-Path $projectRoot $ManifestPath
$imageFullPath = Join-Path $projectRoot $ImageDirectory
$resultFullPath = Join-Path $projectRoot $ResultDirectory
$endpoint = $BaseUrl.TrimEnd("/") + "/api/v1/messages/analyze"

New-Item -ItemType Directory -Force -Path $resultFullPath | Out-Null
$cases = Get-Content -Raw -Encoding UTF8 $manifestFullPath | ConvertFrom-Json
$results = @()

foreach ($case in $cases) {
    $imagePath = Join-Path $imageFullPath ($case.id + ".png")
    if (-not (Test-Path $imagePath)) {
        throw "Evaluation image is missing: $imagePath"
    }

    $attempt = 0
    $result = $null
    $shouldRetry = $false

    do {
        $attempt++
        Write-Host ("[{0}] expected={1} attempt={2}/{3}" -f `
            $case.id, $case.expectedRiskLevel, $attempt, $MaxAttempts)

        $raw = @(& curl.exe --silent --show-error --max-time 70 `
            --request POST `
            --header "Accept: application/json" `
            --form ("image=@{0};type=image/png" -f $imagePath) `
            --write-out "`n%{http_code}" `
            $endpoint)
        $curlExitCode = $LASTEXITCODE
        $shouldRetry = $false

        if ($curlExitCode -ne 0 -or $raw.Count -lt 2) {
            $result = [PSCustomObject]@{
                id = $case.id
                category = $case.category
                expectedRiskLevel = $case.expectedRiskLevel
                actualRiskLevel = $null
                passed = $false
                httpStatus = $null
                analysisStatus = "TRANSPORT_ERROR"
                errorCode = "CURL_$curlExitCode"
                attempts = $attempt
                summary = $null
                reasons = @()
                actions = @()
                error = "curl failed with exit code $curlExitCode"
            }
            $shouldRetry = $true
        }
        else {
            $httpStatus = [int]$raw[-1]
            $body = ($raw[0..($raw.Count - 2)] -join "`n")

            try {
                $response = $body | ConvertFrom-Json
                $actualRiskLevel = [string]$response.riskLevel
                $analysisStatus = if ($response.analysisStatus) {
                    [string]$response.analysisStatus
                }
                else {
                    "LEGACY_RESPONSE"
                }
                $errorCode = if ($response.errorCode) {
                    [string]$response.errorCode
                }
                else {
                    $null
                }
                $passed = $httpStatus -eq 200 -and `
                    $actualRiskLevel -eq [string]$case.expectedRiskLevel

                $result = [PSCustomObject]@{
                    id = $case.id
                    category = $case.category
                    expectedRiskLevel = $case.expectedRiskLevel
                    actualRiskLevel = $actualRiskLevel
                    passed = $passed
                    httpStatus = $httpStatus
                    analysisStatus = $analysisStatus
                    errorCode = $errorCode
                    attempts = $attempt
                    summary = $response.summary
                    reasons = @($response.reasons)
                    actions = @($response.actions)
                    error = $null
                }

                $retryableCodes = @(
                    "RATE_LIMIT",
                    "TIMEOUT",
                    "CONNECTION_ERROR",
                    "UPSTREAM_ERROR",
                    "INVALID_RESPONSE"
                )
                $shouldRetry = ($httpStatus -eq 429 -or $httpStatus -ge 500) `
                    -or ($analysisStatus -eq "AI_ERROR" `
                    -and $retryableCodes -contains $errorCode)
            }
            catch {
                $result = [PSCustomObject]@{
                    id = $case.id
                    category = $case.category
                    expectedRiskLevel = $case.expectedRiskLevel
                    actualRiskLevel = $null
                    passed = $false
                    httpStatus = $httpStatus
                    analysisStatus = "INVALID_API_RESPONSE"
                    errorCode = "UNPARSEABLE_JSON"
                    attempts = $attempt
                    summary = $null
                    reasons = @()
                    actions = @()
                    error = $body
                }
                $shouldRetry = $httpStatus -eq 429 -or $httpStatus -ge 500
            }
        }

        if ($shouldRetry -and $attempt -lt $MaxAttempts) {
            $retryDelaySeconds = [math]::Pow(2, $attempt)
            Write-Host ("  retrying after {0}s: {1}" -f `
                $retryDelaySeconds, $result.errorCode)
            Start-Sleep -Seconds $retryDelaySeconds
        }
    } while ($shouldRetry -and $attempt -lt $MaxAttempts)

    $results += $result
    if ($RequestDelayMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $RequestDelayMilliseconds
    }
}

$passedCount = @($results | Where-Object { $_.passed }).Count
$aiCompletedResults = @($results | Where-Object {
    $_.analysisStatus -eq "SUCCESS" -or $_.analysisStatus -eq "LEGACY_RESPONSE"
})
$aiCompletedPassedCount = @($aiCompletedResults | Where-Object {
    $_.passed
}).Count
$aiFailureResults = @($results | Where-Object {
    $_.analysisStatus -eq "AI_ERROR"
})
$ocrFailureResults = @($results | Where-Object {
    $_.analysisStatus -eq "OCR_ERROR" -or `
        $_.analysisStatus -eq "OCR_UNCERTAIN"
})
$allowedRiskLevels = @("HIGH", "MEDIUM", "LOW", "REVIEW_REQUIRED")
$schemaValidCount = @($results | Where-Object {
    $_.httpStatus -eq 200 -and
    ($_.analysisStatus -eq "SUCCESS" -or `
        $_.analysisStatus -eq "LEGACY_RESPONSE") -and
    $allowedRiskLevels -contains $_.actualRiskLevel -and
    -not [string]::IsNullOrWhiteSpace($_.summary) -and
    $_.reasons.Count -gt 0 -and
    $_.actions.Count -gt 0
}).Count
$dangerousResults = @($aiCompletedResults | Where-Object {
    $_.category -ne "SAFE"
})
$dangerousNotLowCount = @($dangerousResults | Where-Object {
    $_.actualRiskLevel -ne "LOW"
}).Count
$safeResults = @($aiCompletedResults | Where-Object {
    $_.category -eq "SAFE"
})
$safeLowCount = @($safeResults | Where-Object {
    $_.actualRiskLevel -eq "LOW"
}).Count
$elevatedRiskResults = @($results | Where-Object {
    $_.actualRiskLevel -eq "HIGH" -or $_.actualRiskLevel -eq "MEDIUM"
})
$elevatedRiskGuidanceCount = @($elevatedRiskResults | Where-Object {
    (($_.actions -join " ") -match "118|112")
}).Count
$forbiddenSafetyPattern = "100%\s*" + [char]0xC548 + [char]0xC804
$forbiddenSafetyCount = @($results | Where-Object {
    ((@($_.summary) + @($_.reasons) + @($_.actions)) -join " ") -match
        $forbiddenSafetyPattern
}).Count
$report = [PSCustomObject]@{
    generatedAt = (Get-Date).ToString("o")
    endpoint = $endpoint
    total = $results.Count
    passed = $passedCount
    failed = $results.Count - $passedCount
    aiCompleted = $aiCompletedResults.Count
    aiFailed = $aiFailureResults.Count
    ocrFailedOrUncertain = $ocrFailureResults.Count
    aiCompletedPassed = $aiCompletedPassedCount
    failureBreakdown = @($results | Where-Object {
        $_.analysisStatus -ne "SUCCESS" -and `
            $_.analysisStatus -ne "LEGACY_RESPONSE"
    } | Group-Object analysisStatus, errorCode | ForEach-Object {
        [PSCustomObject]@{
            type = $_.Name
            count = $_.Count
        }
    })
    checks = [PSCustomObject]@{
        schemaValid = $schemaValidCount
        dangerousNotLow = $dangerousNotLowCount
        dangerousTotal = $dangerousResults.Count
        safeCorrectLow = $safeLowCount
        safeTotal = $safeResults.Count
        elevatedRiskWith118Or112 = $elevatedRiskGuidanceCount
        elevatedRiskTotal = $elevatedRiskResults.Count
        forbiddenAbsoluteSafety = $forbiddenSafetyCount
    }
    results = $results
}

$jsonPath = Join-Path $resultFullPath "latest.json"
$markdownPath = Join-Path $resultFullPath "latest.md"
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonPath

$lines = @(
    "# Vision API evaluation results",
    "",
    ("- Generated at: {0}" -f $report.generatedAt),
    ('- API: `{0}`' -f $endpoint),
    ("- End-to-end exact matches: **{0}/{1}**" -f $passedCount, $results.Count),
    ("- AI completion rate: **{0}/{1}**" -f $aiCompletedResults.Count, $results.Count),
    ("- Accuracy among completed AI analyses: **{0}/{1}**" -f $aiCompletedPassedCount, $aiCompletedResults.Count),
    ("- AI failures after retries: **{0}**" -f $aiFailureResults.Count),
    ("- OCR failures or uncertain results: **{0}**" -f $ocrFailureResults.Count),
    ("- Valid AI structured responses: **{0}/{1}**" -f $schemaValidCount, $results.Count),
    ("- Dangerous cases not classified LOW: **{0}/{1}**" -f $dangerousNotLowCount, $dangerousResults.Count),
    ("- Safe cases classified LOW: **{0}/{1}**" -f $safeLowCount, $safeResults.Count),
    ("- HIGH/MEDIUM results with 118 or 112 guidance: **{0}/{1}**" -f $elevatedRiskGuidanceCount, $elevatedRiskResults.Count),
    ("- Forbidden absolute-safety phrases: **{0}**" -f $forbiddenSafetyCount)
)

if ($report.failureBreakdown.Count -gt 0) {
    $lines += ""
    $lines += "## Failure breakdown"
    foreach ($failure in $report.failureBreakdown) {
        $lines += "- $($failure.type): $($failure.count)"
    }
    $lines += ""
}

$lines += "| Case | Category | Expected | Actual | Analysis | Attempts | Result |"
$lines += "|---|---|---:|---:|---|---:|:---:|"

foreach ($result in $results) {
    $mark = if ($result.passed) { "PASS" } else { "FAIL" }
    $actual = if ($result.actualRiskLevel) { $result.actualRiskLevel } else { "ERROR" }
    $analysis = $result.analysisStatus
    if ($result.errorCode) {
        $analysis += "/$($result.errorCode)"
    }
    $lines += "| $($result.id) | $($result.category) | $($result.expectedRiskLevel) | $actual | $analysis | $($result.attempts) | $mark |"
}

$lines += ""
$lines += "## Details"
foreach ($result in $results) {
    $lines += ""
    $lines += "### $($result.id)"
    $lines += ""
    $lines += "- Expected/actual: $($result.expectedRiskLevel) / $($result.actualRiskLevel)"
    $lines += "- Analysis status: $($result.analysisStatus) / $($result.errorCode)"
    $lines += "- Attempts: $($result.attempts)"
    $lines += "- Summary: $($result.summary)"
    if ($result.error) {
        $lines += "- Error: $($result.error)"
    }
    foreach ($reason in $result.reasons) {
        $lines += "- Reason: $reason"
    }
    foreach ($action in $result.actions) {
        $lines += "- Action: $action"
    }
}

$lines | Set-Content -Encoding UTF8 $markdownPath
Write-Host ("Evaluation complete: {0}/{1} passed" -f $passedCount, $results.Count)
Write-Host $markdownPath

if ($passedCount -ne $results.Count) {
    exit 1
}
