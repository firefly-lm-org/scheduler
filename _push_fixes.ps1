$GH = "GITHUB_TOKEN_PLACEHOLDER"
$headers = @{
    "Authorization" = "Bearer $GH"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}
$ORG = "firefly-lm-org"
$REPO = "scheduler"
$BRANCH = "main"

# 1. Get current commit SHA
$currentCommit = Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/refs/heads/$BRANCH" -Headers $headers
$currentSha = $currentCommit.object.sha
echo "Current HEAD: $currentSha"

# 2. Get current tree
$commitInfo = Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/commits/$currentSha" -Headers $headers
$baseTreeSha = $commitInfo.tree.sha
echo "Base tree: $baseTreeSha"

# 3. Create blobs for modified files
function New-GitBlob {
    param($path, $file)
    $content = Get-Content $file -Raw -Encoding UTF8
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    $b64 = [Convert]::ToBase64String($bytes)
    $body = @{content=$content; encoding="utf-8"} | ConvertTo-Json -Compress
    $resp = Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/blobs" -Headers $headers -Method POST -ContentType "application/json" -Body $body
    @{path=$path; sha=$resp.sha; mode="100644"; type="blob"}
}

echo "Creating blobs..."
$blob1 = New-GitBlob "requirements.txt" "requirements.txt"
$blob2 = New-GitBlob "app/routers/node.py" "app/routers/node.py"
$blob3 = New-GitBlob "app/utils/minio_client.py" "app/utils/minio_client.py"
echo "Blobs: requirements=$($blob1.sha) node=$($blob2.sha) minio=$($blob3.sha)"

# 4. Create new tree
$newTree = @($blob1, $blob2, $blob3) | ConvertTo-Json -Compress
$treeBody = @{
    base_tree = $baseTreeSha
    tree = @($blob1, $blob2, $blob3)
} | ConvertTo-Json -Depth 5 -Compress

$newTreeResp = Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/trees" -Headers $headers -Method POST -ContentType "application/json" -Body $treeBody
echo "New tree: $($newTreeResp.sha)"

# 5. Create commit
$msg = "fix: bcrypt version pin, ORM query fix, datetime fix, minio timedelta

- Pin bcrypt==4.0.1 (bcrypt>=4.1 breaks passlib backend detection)
- node.py: use select(Node) instead of Node.__table__.select() -> scalar_one_or_none()
  (was returning Row object, causing AttributeError on node.status=)
- node.py: fix node.last_heartbeat = time.strftime() -> datetime.utcnow()
  (asyncpg requires datetime, not str for DateTime columns)
- minio_client.py: fix presigned URL expires=int -> timedelta(seconds=int)
  (minio library requires timedelta, not raw int)"
$commitBody = @{
    message = $msg
    tree = $newTreeResp.sha
    parents = @($currentSha)
} | ConvertTo-Json -Compress

$newCommit = Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/commits" -Headers $headers -Method POST -ContentType "application/json" -Body $commitBody
echo "New commit: $($newCommit.sha)"

# 6. Update branch ref
$refBody = @{ref="refs/heads/$BRANCH"; sha=$newCommit.sha} | ConvertTo-Json -Compress
Invoke-RestMethod "https://api.github.com/repos/$ORG/$REPO/git/refs/heads/$BRANCH" -Headers $headers -Method PUT -ContentType "application/json" -Body $refBody | Out-Null
echo "Branch $BRANCH updated to $($newCommit.sha)"
