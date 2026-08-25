param(
    [string]$BaseUrl = "http://127.0.0.1:18080",
    [string]$ManifestPath = "evaluation/labels.json",
    [string]$ImageDirectory = "evaluation/images",
    [string]$ResultDirectory = "evaluation/results"
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

    Write-Host ("[{0}] expected={1}" -f $case.id, $case.expectedRiskLevel)
    $raw = @(& curl.exe --silent --show-error --max-time 70 `
        --request POST `
        --header "Accept: application/json" `
        --form ("image=@{0};type=image/png" -f $imagePath) `
        --write-out "`n%{http_code}" `
        $endpoint)
    $curlExitCode = $LASTEXITCODE

    if ($curlExitCode -ne 0 -or $raw.Count -lt 2) {
        $results += [PSCustomObject]@{
            id = $case.id
            category = $case.category
            expectedRiskLevel = $case.expectedRiskLevel
            actualRiskLevel = $null
            passed = $false
            httpStatus = $null
            summary = $null
            reasons = @()
            actions = @()
            error = "curl failed with exit code $curlExitCode"
        }
        continue
    }

    $httpStatus = $raw[-1]
    $body = ($raw[0..($raw.Count - 2)] -join "`n")

    try {
        $response = $body | ConvertFrom-Json
        $actualRiskLevel = [string]$response.riskLevel
        $passed = $httpStatus -eq "200" -and `
            $actualRiskLevel -eq [string]$case.expectedRiskLevel

        $results += [PSCustomObject]@{
            id = $case.id
            category = $case.category
            expectedRiskLevel = $case.expectedRiskLevel
            actualRiskLevel = $actualRiskLevel
            passed = $passed
            httpStatus = [int]$httpStatus
            summary = $response.summary
            reasons = @($response.reasons)
            actions = @($response.actions)
            error = $null
        }
    }
    catch {
        $results += [PSCustomObject]@{
            id = $case.id
            category = $case.category
            expectedRiskLevel = $case.expectedRiskLevel
            actualRiskLevel = $null
            passed = $false
            httpStatus = [int]$httpStatus
            summary = $null
            reasons = @()
            actions = @()
            error = $body
        }
    }
}

$passedCount = @($results | Where-Object { $_.passed }).Count
$allowedRiskLevels = @("HIGH", "MEDIUM", "LOW", "REVIEW_REQUIRED")
$schemaValidCount = @($results | Where-Object {
    $_.httpStatus -eq 200 -and
    $allowedRiskLevels -contains $_.actualRiskLevel -and
    -not [string]::IsNullOrWhiteSpace($_.summary) -and
    $_.reasons.Count -gt 0 -and
    $_.actions.Count -gt 0
}).Count
$dangerousResults = @($results | Where-Object { $_.category -ne "SAFE" })
$dangerousNotLowCount = @($dangerousResults | Where-Object {
    $_.actualRiskLevel -ne "LOW"
}).Count
$safeResults = @($results | Where-Object { $_.category -eq "SAFE" })
$safeLowCount = @($safeResults | Where-Object {
    $_.actualRiskLevel -eq "LOW"
}).Count
$highResults = @($results | Where-Object {
    $_.actualRiskLevel -eq "HIGH"
})
$highGuidanceCount = @($highResults | Where-Object {
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
    checks = [PSCustomObject]@{
        schemaValid = $schemaValidCount
        dangerousNotLow = $dangerousNotLowCount
        dangerousTotal = $dangerousResults.Count
        safeCorrectLow = $safeLowCount
        safeTotal = $safeResults.Count
        highWith118Or112 = $highGuidanceCount
        highTotal = $highResults.Count
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
    ("- Accuracy: **{0}/{1}**" -f $passedCount, $results.Count),
    ("- Valid structured responses: **{0}/{1}**" -f $schemaValidCount, $results.Count),
    ("- Dangerous cases not classified LOW: **{0}/{1}**" -f $dangerousNotLowCount, $dangerousResults.Count),
    ("- Safe cases classified LOW: **{0}/{1}**" -f $safeLowCount, $safeResults.Count),
    ("- HIGH results with 118 or 112 guidance: **{0}/{1}**" -f $highGuidanceCount, $highResults.Count),
    ("- Forbidden absolute-safety phrases: **{0}**" -f $forbiddenSafetyCount),
    "",
    "| Case | Category | Expected | Actual | Result |",
    "|---|---|---:|---:|:---:|"
)

foreach ($result in $results) {
    $mark = if ($result.passed) { "PASS" } else { "FAIL" }
    $actual = if ($result.actualRiskLevel) { $result.actualRiskLevel } else { "ERROR" }
    $lines += "| $($result.id) | $($result.category) | $($result.expectedRiskLevel) | $actual | $mark |"
}

$lines += ""
$lines += "## Details"
foreach ($result in $results) {
    $lines += ""
    $lines += "### $($result.id)"
    $lines += ""
    $lines += "- Expected/actual: $($result.expectedRiskLevel) / $($result.actualRiskLevel)"
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
