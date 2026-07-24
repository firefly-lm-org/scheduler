# ── Fix requirements.txt BOM ──────────────────────────────────────────
$f = "requirements.txt"
$raw = [System.IO.File]::ReadAllBytes((Resolve-Path $f).Path)
if ($raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
    $clean = $raw[3..($raw.Length-1)]
    [System.IO.File]::WriteAllBytes($f, $clean)
    echo "BOM stripped from requirements.txt"
} else {
    echo "No BOM in requirements.txt"
}

# ── Helper: create blob via gh ─────────────────────────────────────
function New-GhBlob {
    param($file, $destPath)
    $sha = (gh api repos/firefly-lm-org/scheduler/git/blobs `
        --field content=@$file `
        --field encoding=base64 2>$null | ConvertFrom-Json).sha
    echo "BLOB $destPath => $sha"
    return $sha
}

# ── Step 1: Create blobs ──────────────────────────────────────────
echo "Creating blobs..."
$reqSha = New-GhBlob "requirements.txt" "requirements.txt"
$nodeSha = New-GhBlob "app/routers/node.py" "app/routers/node.py"
$minioSha = New-GhBlob "app/utils/minio_client.py" "app/utils/minio_client.py"

# ── Step 2: Get current HEAD ──────────────────────────────────────
$refJson = gh api repos/firefly-lm-org/scheduler/git/ref/heads/main 2>$null | ConvertFrom-Json
$headSha = $refJson.object.sha
$commitJson = gh api repos/firefly-lm-org/scheduler/git/commits/$headSha 2>$null | ConvertFrom-Json
$baseTree = $commitJson.tree.sha
echo "HEAD=$headSha base_tree=$baseTree"

# ── Step 3: Create tree ────────────────────────────────────────────
$treeTmp = "$env:TEMP\_tree.json"
@{
    base_tree = $baseTree
    tree = @(
        @{path="requirements.txt"; sha=$reqSha; mode="100644"; type="blob"},
        @{path="app/routers/node.py"; sha=$nodeSha; mode="100644"; type="blob"},
        @{path="app/utils/minio_client.py"; sha=$minioSha; mode="100644"; type="blob"}
    )
} | ConvertTo-Json -Depth 5 | ForEach-Object { $_ -replace '(?<!\\)\\n', "`n" } | Set-Content $treeTmp -Encoding UTF8

$treeJson = gh api repos/firefly-lm-org/scheduler/git/trees -Method POST --input $treeTmp 2>$null | ConvertFrom-Json
Remove-Item $treeTmp -Force
echo "New tree=$($treeJson.sha)"

# ── Step 4: Create commit ──────────────────────────────────────────
$commitTmp = "$env:TEMP\_commit.json"
$msg = "fix: bcrypt pin, ORM query, datetime, minio timedelta

- Pin bcrypt==4.0.1 (bcrypt>=4.1 breaks passlib backend detection)
- node.py: select(Node) instead of Node.__table__.select() -> scalar_one_or_none()
  (was returning Row object -> AttributeError on node.status=)
- node.py: node.last_heartbeat = time.strftime() -> datetime.utcnow()
  (asyncpg requires datetime, not str for DateTime columns)
- minio_client.py: presigned URL expires=int -> timedelta(seconds=int)
  (minio library requires timedelta, not raw int)"

@{message=$msg; tree=$treeJson.sha; parents=@($headSha)} | ConvertTo-Json | Set-Content $commitTmp -Encoding UTF8
$commitJson = gh api repos/firefly-lm-org/scheduler/git/commits -Method POST --input $commitTmp 2>$null | ConvertFrom-Json
Remove-Item $commitTmp -Force
echo "New commit=$($commitJson.sha)"

# ── Step 5: Update branch ─────────────────────────────────────────
gh api repos/firefly-lm-org/scheduler/git/refs/heads/main -Method PATCH -f sha=$($commitJson.sha) 2>$null | Out-Null
echo "Branch main updated!"
