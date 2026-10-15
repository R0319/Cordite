<#
.SYNOPSIS
  生成したモデルを作者の作業フォルダへ配置し、残す銃以外のモデルを作業フォルダの外へ退避する。

.DESCRIPTION
  1. 生成モデル（下の $Install）を -ModelsDir へコピーする（同名は上書き）。腕の待機ポーズ（<銃ID>.animation.json）は
     作業フォルダに同名のファイルが無いときだけ置く（作者のアニメーションを上書きしない）。
  2. -ModelsDir 直下のファイル・フォルダのうち、名前が -Keep の銃ID で始まらないものを -ArchiveDir へ移動する。
     消さないので、退避フォルダから戻せる。
  -Apply を付けないと「何をするか」の一覧を表示するだけで、何も変更しない。

  退避先は syncGunAssets の同期元（local.properties の cordite.assetDir）の外でなければならない
  （中に置くと、退避したモデルもゲームへ同期されてしまう）。中にある場合は止まる。

.EXAMPLE
  # まず一覧だけ確認
  .\tools\modelgen\install_models.ps1 -ModelsDir <作業フォルダの models>
  # 問題なければ実行
  .\tools\modelgen\install_models.ps1 -ModelsDir <作業フォルダの models> -Apply
#>
param(
    [Parameter(Mandatory = $true)] [string] $ModelsDir,
    [string] $ArchiveDir = "",
    [string[]] $Keep = @("glock", "m1911", "ak_47", "m4a1", "m249", "m249_stanag", "mp5", "m24", "p90", "m1912", "awm", "m79", "m2", "g3a3", "hk416"),
    [switch] $Apply
)
$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$gen = Join-Path $PSScriptRoot "generated"
# 配置するモデル: 生成フォルダ → ファイル名（銃ID）。簡略版（m4a1_mesh_lite）は出力名が m4a1 と重なるので、
# 出力名を分けるまで対象外
$Install = @(
    @{ Dir = "ak_47_mesh";       Id = "ak_47" },   # 作業フォルダの旧版の AK を置き換える（作者了承済み）
    @{ Dir = "m4a1_mesh";        Id = "m4a1" },
    @{ Dir = "m249_mesh";        Id = "m249" },
    @{ Dir = "m249_stanag_mesh"; Id = "m249_stanag" },
    @{ Dir = "mp5_mesh";         Id = "mp5" },
    @{ Dir = "m24_mesh";         Id = "m24" },
    @{ Dir = "p90_mesh";         Id = "p90" },
    @{ Dir = "m1912_mesh";       Id = "m1912" },
    @{ Dir = "awm_mesh";         Id = "awm" },
    @{ Dir = "m79_mesh";         Id = "m79" },
    @{ Dir = "m2_mesh";          Id = "m2" },      # 三脚（m3_tripod_mesh）は銃ではないので配置しない（銃のモデルとして読み込まれる）
    @{ Dir = "g3a3_mesh";        Id = "g3a3" },
    @{ Dir = "hk416_mesh";       Id = "hk416" }
)

if (-not (Test-Path $ModelsDir -PathType Container)) { throw "作業フォルダが見つからない: $ModelsDir" }
$ModelsDir = (Resolve-Path $ModelsDir).Path
if ($ArchiveDir -eq "") {
    # 既定: 作業フォルダの 2 つ上（assets の外）に日時付きで作る
    $ArchiveDir = Join-Path (Split-Path (Split-Path $ModelsDir -Parent) -Parent) ("_model_archive_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
}
$ArchiveFull = [System.IO.Path]::GetFullPath($ArchiveDir)

# 退避先が同期元（cordite.assetDir）の中なら止める
$props = Join-Path $repo "local.properties"
if (Test-Path $props) {
    $line = Get-Content $props | Where-Object { $_ -match '^\s*cordite\.assetDir\s*=' } | Select-Object -First 1
    if ($line) {
        # local.properties は \\ でエスケープされている。区切り文字は OS に合わせてそろえてから比べる
        $raw = ($line -replace '^\s*cordite\.assetDir\s*=\s*', '').Trim().Replace('\\', '\')
        $sep = [System.IO.Path]::DirectorySeparatorChar
        $assetDir = [System.IO.Path]::GetFullPath($raw.Replace('\', $sep).Replace('/', $sep)).TrimEnd($sep)
        if (($ArchiveFull.TrimEnd($sep) + $sep).StartsWith($assetDir + $sep, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "退避先が同期元（cordite.assetDir = $assetDir）の中にある。-ArchiveDir で外を指定すること"
        }
    }
}

function Test-Kept([string] $name) {
    $base = $name.Split('.')[0].ToLower()
    foreach ($k in $Keep) {
        if ($base -eq $k -or $base.StartsWith($k + "_")) { return $true }
    }
    return $false
}

$mode = if ($Apply) { "実行" } else { "確認のみ（-Apply で実行）" }
Write-Host "== モデルの配置と整理: $mode"
Write-Host "   作業フォルダ: $ModelsDir"
Write-Host "   退避先      : $ArchiveFull"

# 1. 退避（先に一覧を作る。これから配置するファイルは残す銃IDなので対象外）
$move = Get-ChildItem -LiteralPath $ModelsDir | Where-Object { -not (Test-Kept $_.Name) }
Write-Host "`n-- 退避する（$($move.Count) 件）"
foreach ($m in $move) { Write-Host "   $($m.Name)" }
$kept = Get-ChildItem -LiteralPath $ModelsDir | Where-Object { Test-Kept $_.Name }
Write-Host "`n-- 残す（$($kept.Count) 件）"
foreach ($k in $kept) { Write-Host "   $($k.Name)" }

# 2. 配置
Write-Host "`n-- 配置する"
$copies = @()
foreach ($i in $Install) {
    foreach ($suffix in @(".geo.json", ".png", "_modelshot.png")) {
        $src = Join-Path (Join-Path $gen $i.Dir) ($i.Id + $suffix)
        if (-not (Test-Path $src)) { throw "生成物が無い（python3 build.py を先に実行）: $src" }
        $copies += @{ Src = $src; Dst = (Join-Path $ModelsDir ($i.Id + $suffix)) }
        Write-Host "   $($i.Id + $suffix)"
    }
    # 腕の待機ポーズ（仮置きの idle）。作者のアニメーションがすでにあれば上書きしない（作者の制作物を消さない）
    $anim = $i.Id + ".animation.json"
    $src = Join-Path (Join-Path $gen $i.Dir) $anim
    $dst = Join-Path $ModelsDir $anim
    if (Test-Path $dst) {
        Write-Host "   $anim は配置しない（作業フォルダにすでにある）"
    } elseif (Test-Path $src) {
        $copies += @{ Src = $src; Dst = $dst }
        Write-Host "   $anim（仮の待機ポーズ）"
    }
}

if (-not $Apply) {
    Write-Host "`n確認のみ。問題なければ -Apply を付けて実行する。"
    return
}

if ($move.Count -gt 0) {
    New-Item -ItemType Directory -Path $ArchiveFull -Force | Out-Null
    foreach ($m in $move) { Move-Item -LiteralPath $m.FullName -Destination $ArchiveFull }
}
foreach ($c in $copies) { Copy-Item -LiteralPath $c.Src -Destination $c.Dst -Force }
Write-Host "`n完了。退避したものは $ArchiveFull から戻せる。"
Write-Host "注意: syncGunAssets は src/main/resources 側の古いファイルを消さない。退避した銃のモデルが"
Write-Host "      src/main/resources/assets/cordite/models/gun などに残っていれば、そちらは別途消すこと。"
