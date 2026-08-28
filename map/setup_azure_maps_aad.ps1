<#
.SYNOPSIS
    setup_azure_maps_aad.ps1
    (仮称)樹木管理システム ポートフォリオ用
    地図機能(PCF + Entra ID認証)のための、Azure AD側の準備を自動化する。

.DESCRIPTION
    以下を順番に実行する(冪等: 既に存在するものはスキップ)。
    1. Azure ADアプリ登録の作成(SPA向けリダイレクトURI設定込み)
    2. そのアプリのサービスプリンシパル作成
    3. Azure Mapsアカウントの作成(未作成の場合のみ)
    4. サービスプリンシパルへ「Azure Maps Data Reader」ロールを、
       Azure Mapsアカウント単位のスコープで割り当て

.NOTES
    事前準備: Azure CLI (az) がインストール済みで、az login 済みであること。
    実行後、表示される ClientId / TenantId / AzureMapsClientId を
    index.ts の設定値としてそのまま使う。
#>

param(
    [string]$AppDisplayName = "TreeMapPCF",
    [string]$DataverseEnvUrl = "",          # 例: https://orgXXXXXXXX.crm7.dynamics.com
    [string]$PcfSchemaName   = "new_TreeMapControl",
    [string]$ResourceGroup   = "rg-treemap-portfolio",
    [string]$Location        = "japaneast",
    [string]$MapsLocation    = "global",    # Azure Mapsはjapaneast等の地域リージョンに未対応のためglobalを既定値とする
    [string]$MapsAccountName = "treemap-portfolio-maps"
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n----- $msg -----" -ForegroundColor Cyan
}

# ---------------------------------------------------------
# 0. 事前確認
# ---------------------------------------------------------
Write-Step "Azure CLIのログイン状態を確認します"
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "az login を実行してサインインしてください。" -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}
$tenantId = $account.tenantId
Write-Host "テナントID: $tenantId"

if ([string]::IsNullOrWhiteSpace($DataverseEnvUrl)) {
    $DataverseEnvUrl = Read-Host "Dataverse環境のURLを入力してください(例: https://orgXXXXXXXX.crm7.dynamics.com)"
}
$DataverseEnvUrl = $DataverseEnvUrl.TrimEnd("/")
$redirectUri = "$DataverseEnvUrl/webresources/$PcfSchemaName/popup.html"
Write-Host "リダイレクトURI: $redirectUri"

# ---------------------------------------------------------
# 1. Azure ADアプリ登録(SPA)の作成
# ---------------------------------------------------------
Write-Step "Azure ADアプリ登録を確認・作成します"
$existingApp = az ad app list --display-name $AppDisplayName --query "[0]" | ConvertFrom-Json

if ($existingApp) {
    Write-Host "アプリ登録『$AppDisplayName』は既に存在します。スキップします。"
    $appId = $existingApp.appId
    $appObjectId = $existingApp.id
} else {
    $body = @{
        displayName    = $AppDisplayName
        signInAudience = "AzureADMyOrg"
        spa            = @{ redirectUris = @($redirectUri) }
    } | ConvertTo-Json -Depth 5 -Compress

    $tmpFile = New-TemporaryFile
    Set-Content -Path $tmpFile -Value $body -Encoding utf8

    $created = az rest --method POST `
        --uri "https://graph.microsoft.com/v1.0/applications" `
        --headers "Content-Type=application/json" `
        --body "@$tmpFile" | ConvertFrom-Json

    Remove-Item $tmpFile

    $appId = $created.appId
    $appObjectId = $created.id
    Write-Host "アプリ登録『$AppDisplayName』を作成しました。"
}
Write-Host "ClientId(appId): $appId"

# ---------------------------------------------------------
# 2. サービスプリンシパルの作成
# ---------------------------------------------------------
Write-Step "サービスプリンシパルを確認・作成します"
$existingSp = az ad sp list --filter "appId eq '$appId'" --query "[0]" | ConvertFrom-Json
if ($existingSp) {
    Write-Host "サービスプリンシパルは既に存在します。スキップします。"
    $spObjectId = $existingSp.id
} else {
    $sp = az ad sp create --id $appId | ConvertFrom-Json
    $spObjectId = $sp.id
    Write-Host "サービスプリンシパルを作成しました。"
}

# ---------------------------------------------------------
# 3. リソースグループ / Azure Mapsアカウントの作成
# ---------------------------------------------------------
Write-Step "リソースグループを確認・作成します"
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "false") {
    az group create --name $ResourceGroup --location $Location | Out-Null
    Write-Host "リソースグループ『$ResourceGroup』を作成しました。"
} else {
    Write-Host "リソースグループ『$ResourceGroup』は既に存在します。スキップします。"
}

Write-Step "Azure Mapsアカウント(Gen2)を確認・作成します"
$prevPref = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$mapsAccount = az maps account show --name $MapsAccountName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
$ErrorActionPreference = $prevPref

if ($mapsAccount) {
    Write-Host "Azure Mapsアカウント『$MapsAccountName』は既に存在します。スキップします。"
} else {
    $mapsAccount = az maps account create `
        --name $MapsAccountName `
        --resource-group $ResourceGroup `
        --location $MapsLocation `
        --sku G2 `
        --kind Gen2 `
        --accept-tos | ConvertFrom-Json

    if (-not $mapsAccount -or -not $mapsAccount.id) {
        Write-Host "[エラー] Azure Mapsアカウントの作成に失敗しました。上に表示されたエラー内容を確認してください。" -ForegroundColor Red
        exit 1
    }
    Write-Host "Azure Mapsアカウント『$MapsAccountName』を作成しました(リージョン: $MapsLocation、Gen2、無料枠あり)。"
}
$mapsAccountId = $mapsAccount.id

# ---------------------------------------------------------
# 4. RBACロール割り当て(Azure Maps Data Reader)
# ---------------------------------------------------------
Write-Step "『Azure Maps Data Reader』ロールを割り当てます"

if (-not $mapsAccountId) {
    Write-Host "[エラー] Azure MapsアカウントIDが取得できていないため、ロール割り当てをスキップします。" -ForegroundColor Red
    exit 1
}

$existingAssignment = az role assignment list `
    --assignee $appId `
    --scope $mapsAccountId `
    --role "Azure Maps Data Reader" | ConvertFrom-Json

if ($existingAssignment -and $existingAssignment.Count -gt 0) {
    Write-Host "ロール割り当ては既に存在します。スキップします。"
} else {
    $assignResult = az role assignment create `
        --assignee-object-id $spObjectId `
        --assignee-principal-type ServicePrincipal `
        --role "Azure Maps Data Reader" `
        --scope $mapsAccountId | ConvertFrom-Json

    if (-not $assignResult) {
        Write-Host "[エラー] ロール割り当てに失敗しました。上に表示されたエラー内容を確認してください。" -ForegroundColor Red
        exit 1
    }
    Write-Host "『Azure Maps Data Reader』ロールを割り当てました(スコープ: このAzure Mapsアカウントのみ)。"
}

# ---------------------------------------------------------
# 結果まとめ
# ---------------------------------------------------------
Write-Step "完了しました。以下の値を index.ts の設定に使ってください"
Write-Host "TenantId        : $tenantId"
Write-Host "ClientId        : $appId"
Write-Host "RedirectUri     : $redirectUri"
Write-Host "AzureMapsClientId(=このAzure Mapsアカウントのクライアント/マップID): "
Write-Host ($mapsAccount | ConvertTo-Json -Depth 5)

# 後続スクリプト(verify_aad_setup.py等)が参照できるよう、設定値をJSONで保存
$outFile = Join-Path $PSScriptRoot "aad_setup_result.json"
@{
    tenantId      = $tenantId
    clientId      = $appId
    appObjectId   = $appObjectId
    spObjectId    = $spObjectId
    redirectUri   = $redirectUri
    resourceGroup = $ResourceGroup
    mapsAccountName = $MapsAccountName
    mapsAccountId   = $mapsAccountId
} | ConvertTo-Json | Set-Content -Path $outFile -Encoding utf8

Write-Host "`n設定値を $outFile に保存しました。"
