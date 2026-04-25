# run.ps1 — lwt wrapper for this wiki. Usage: .\run.ps1 <command> [args]
param(
    [string]$Command = "help",
    [Parameter(ValueFromRemainingArguments=$true)]$Rest
)

switch ($Command) {
    "ingest" { lwt ingest @Rest --wiki-dir wiki }
    "serve"  { lwt deploy --target mkdocs --wiki-dir wiki @Rest }
    "build"  { lwt deploy --target mkdocs --build --wiki-dir wiki @Rest }
    "lint"   { lwt lint --structural --wiki-dir wiki }
    "search" { lwt search @Rest --wiki-dir wiki }
    default  {
        Write-Host "Usage: .\run.ps1 <command> [args]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  ingest <file-or-url>   Convert source -> wiki\.tmp\ then open claude"
        Write-Host "  serve                  Serve wiki at http://localhost:8000"
        Write-Host "  build                  Build static site -> .build\site\"
        Write-Host "  lint                   Check for broken links and orphaned pages"
        Write-Host "  search <query>         BM25 keyword search over wiki pages"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run.ps1 ingest raw\paper.pdf"
        Write-Host "  .\run.ps1 serve"
        Write-Host "  .\run.ps1 search 'attention mechanism'"
    }
}
