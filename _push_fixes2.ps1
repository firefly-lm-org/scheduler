$headers = @{
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}
$GH = "GITHUB_TOKEN_PLACEHOLDER"
$ORG = "firefly-lm-org"
$REPO = "scheduler"
$BRANCH = "main"
$ENDPOINT = "https://api.github.com"

# Helper: create blob and return SHA
function New-Blob {
    param($filePath)
    $b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes((Resolve-Path $filePath)))
    $tmp = "$env:TEMP\_blob_$([guid]::NewGuid().ToString('N')).json"
    @{content=$b64;encoding="utf-8"} | ConvertTo-Json > $tmp
    $sha = (gh api $ENDPOINT/repos/$ORG/$REPO/git/blobs --header "Authorization: Bearer $GH" --header "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" --input $tmp 2>$null | ConvertFrom-Json).sha
    Remove-Item $tmp -Force
    echo $sha
}

# 1. Get current HEAD
$refJson = gh api $ENDPOINT/repos/$ORG/$REPO/git/ref/heads/$BRANCH --header "Authorization: Bearer $GH" 2>$null | ConvertFrom-Json
$headSha = $refJson.object.sha
echo "HEAD: $headSha"

# 2. Get current tree SHA
$commitJson = gh api $ENDPOINT/repos/$ORG/$REPO/git/commits/$headSha --header "Authorization: Bearer $GH" 2>$null | ConvertFrom-Json
$baseTree = $commitJson.tree.sha
echo "Base tree: $baseTree"

# 3. Create blobs
echo "Creating blobs..."
$reqBlob = New-Blob "requirements.txt"
$nodeBlob = New-Blob "app/routers/node.py"
$minioBlob = New-Blob "app/utils/minio_client.py"
echo "req=$reqBlob node=$nodeBlob minio=$minioBlob"

# 4. Build tree JSON and create tree
$treeItems = @(
    @{path="requirements.txt"; sha=$reqBlob; mode="100644"; type="blob"},
    @{path="app/routers/node.py"; sha=$nodeBlob; mode="100644"; type="blob"},
    @{path="app/utils/minio_client.py"; sha=$minioBlob; mode="100644"; type="blob"}
)
$treeTmp = "$env:TEMP\_tree_$([guid]::NewGuid().ToString('N')).json"
$treeBody = @{base_tree=$baseTree; tree=$treeItems} | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($treeTmp, $treeBody, [System.Text.Encoding]::UTF8)
$treeJson = gh api $ENDPOINT/repos/$ORG/$REPO/git/trees --header "Authorization: Bearer $GH" -Method POST --input $treeTmp 2>$null | ConvertFrom-Json
Remove-Item $treeTmp -Force
echo "New tree: $($treeJson.sha)"

# 5. Create commit
$msg = "fix: bcrypt pin, ORM query, datetime, minio timedelta

- Pin bcrypt==4.0.1 (bcrypt>=4.1 breaks passlib backend detection)
- node.py: select(Node) instead of Node.__table__.select() -> scalar_one_or_none()
  (was returning Row object -> AttributeError on node.status=)
- node.py: node.last_heartbeat = time.strftime() -> datetime.utcnow()
  (asyncpg requires datetime, not str for DateTime columns)
- minio_client.py: presigned URL expires=int -> timedelta(seconds=int)
  (minio library requires timedelta)"

$commitTmp = "$env:TEMP\_commit_$([guid]::NewGuid().ToString('N')).json"
$commitBody = @{message=$msg; tree=$treeJson.sha; parents=@($headSha)} | ConvertTo-Json
[System.IO.File]::WriteAllText($commitTmp, $commitBody, [System.Text.Encoding]::UTF8)
$commitJson = gh api $ENDPOINT/repos/$ORG/$REPO/git/commits --header "Authorization: Bearer $GH" -Method POST --input $commitTmp 2>$null | ConvertFrom-Json
Remove-Item $commitTmp -Force
echo "New commit: $($commitJson.sha)"

# 6. Update branch
gh api $ENDPOINT/repos/$ORG/$REPO/git/refs/heads/$BRANCH --header "Authorization: Bearer $GH" -Method PATCH -f sha=$commitJson.sha 2>$null | Out-Null
echo "Branch $BRANCH updated!"

# Verify CI
Start-Sleep 5
$ciRun = gh api $ENDPOINT/repos/$ORG/$REPO/actions/runs --header "Authorization: Bearer $GH" 2>$null | ConvertFrom-Json
$latest = $ciRun.workflow_runs[0]
echo "Latest CI run: #$($latest.run_number) status=$($latest.status) conclusion=$($latest.conclusion)"
