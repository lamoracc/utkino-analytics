param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"

$inputPath = Resolve-Path -LiteralPath $InputFile
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$outputPath = Resolve-Path -LiteralPath $OutputDir

$excel = $null
$workbook = $null

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false

    $workbook = $excel.Workbooks.Open($inputPath.Path)
    $exports = @()

    foreach ($worksheet in $workbook.Worksheets) {
        $worksheet.Activate()
        $safeName = $worksheet.Name -replace '[\\/:*?"<>|]', '_'
        $csvPath = Join-Path $outputPath.Path ($safeName + ".csv")
        $worksheet.SaveAs($csvPath, 6)
        $exports += $csvPath
    }

    $exports
}
finally {
    if ($workbook -ne $null) {
        $workbook.Close($false)
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null
    }

    if ($excel -ne $null) {
        $excel.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    }
}

