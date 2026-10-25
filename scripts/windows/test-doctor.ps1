$ErrorActionPreference = 'Stop'
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$fixture = Join-Path $tempBase ("investment-doctor-" + [guid]::NewGuid().ToString('N'))
$bin = Join-Path $fixture 'bin'
$project = Join-Path $fixture 'project'
$scripts = Join-Path $project 'scripts/windows'
$venv = Join-Path $project '.venv/Scripts'
$originalPath = $env:PATH
try {
    New-Item -ItemType Directory -Path $bin, $scripts, $venv, (Join-Path $project 'apps/web/node_modules') -Force | Out-Null
    Copy-Item (Join-Path $PSScriptRoot 'doctor.ps1') (Join-Path $scripts 'doctor.ps1')
    Set-Content (Join-Path $project '.env.example') ''

    # A real executable lets the unmodified doctor probe the project venv path.
    $fakePython = @'
using System;
public static class FakePython {
    public static void Main(string[] args) {
        if (args.Length > 0 && args[0] == "--version")
            Console.WriteLine("Python " + Environment.GetEnvironmentVariable("FAKE_VENV_VERSION"));
        else if (args.Length > 0 && args[0] == "-c")
            Console.WriteLine(Environment.GetEnvironmentVariable("FAKE_VENV_BITS"));
        else Environment.Exit(2);
    }
}
'@
    Add-Type -TypeDefinition $fakePython -OutputAssembly (Join-Path $venv 'python.exe') -OutputType ConsoleApplication
    Set-Content (Join-Path $bin 'node.cmd') '@echo v%FAKE_NODE_VERSION%'
    Set-Content (Join-Path $bin 'npm.cmd') '@echo %FAKE_NPM_VERSION%'
    Set-Content (Join-Path $bin 'git.cmd') '@echo git version %FAKE_GIT_VERSION%'
    Set-Content (Join-Path $bin 'python.cmd') @('@echo off', 'if "%1"=="-c" (echo %FAKE_PYTHON_BITS%) else (echo Python %FAKE_PYTHON_VERSION%)')
    $env:PATH = "$bin;$env:SystemRoot\System32;$env:SystemRoot"

    $cases = @(
        @{ Name = 'supported'; Node = '24.1.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '64'; Exit = 0; Signal = 'Local prerequisite checks passed' },
        @{ Name = 'old node'; Node = '22.11.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '64'; Exit = 1; Signal = 'UNSUPPORTED tool: node' },
        @{ Name = 'missing node'; Node = '24.1.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '64'; MissingNode = $true; Exit = 1; Signal = 'MISSING tool: node' },
        @{ Name = 'old npm'; Node = '24.1.0'; Npm = '10.9.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '64'; Exit = 1; Signal = 'UNSUPPORTED tool: npm.cmd' },
        @{ Name = 'old git'; Node = '24.1.0'; Git = '1.9.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '64'; Exit = 1; Signal = 'UNSUPPORTED tool: git' },
        @{ Name = 'old python'; Node = '24.1.0'; Python = '3.10.9'; Venv = '3.11.6'; Bits = '64'; Exit = 1; Signal = 'UNSUPPORTED tool: python' },
        @{ Name = 'mismatched venv'; Node = '24.1.0'; Python = '3.11.6'; Venv = '3.9.18'; Bits = '64'; Exit = 1; Signal = 'UNSUPPORTED tool: venv python' },
        @{ Name = '32-bit venv'; Node = '24.1.0'; Python = '3.11.6'; Venv = '3.11.6'; Bits = '32'; Exit = 1; Signal = 'UNSUPPORTED tool: venv python' }
    )
    foreach ($case in $cases) {
        if ($case.ContainsKey('MissingNode')) { Remove-Item (Join-Path $bin 'node.cmd') }
        elseif (-not (Test-Path (Join-Path $bin 'node.cmd'))) { Set-Content (Join-Path $bin 'node.cmd') '@echo v%FAKE_NODE_VERSION%' }
        $env:FAKE_NODE_VERSION = $case.Node
        $env:FAKE_NPM_VERSION = if ($case.ContainsKey('Npm')) { $case.Npm } else { '11.12.1' }
        $env:FAKE_GIT_VERSION = if ($case.ContainsKey('Git')) { $case.Git } else { '2.56.0' }
        $env:FAKE_PYTHON_VERSION = $case.Python
        $env:FAKE_PYTHON_BITS = '64'
        $env:FAKE_VENV_VERSION = $case.Venv
        $env:FAKE_VENV_BITS = $case.Bits
        $output = & (Join-Path $PSHOME 'powershell.exe') -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scripts 'doctor.ps1') 2>&1 | Out-String
        $actualExit = $LASTEXITCODE
        if ($actualExit -ne $case.Exit -or -not $output.Contains($case.Signal)) {
            throw "FAIL $($case.Name): exit=$actualExit, expected=$($case.Exit), output=$output"
        }
        Write-Output "PASS $($case.Name): exit=$actualExit, $($case.Signal)"
    }
} finally {
    $env:PATH = $originalPath
    foreach ($name in @('FAKE_NODE_VERSION', 'FAKE_NPM_VERSION', 'FAKE_GIT_VERSION', 'FAKE_PYTHON_VERSION', 'FAKE_PYTHON_BITS', 'FAKE_VENV_VERSION', 'FAKE_VENV_BITS')) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    $resolved = [IO.Path]::GetFullPath($fixture)
    if ($resolved.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -like 'investment-doctor-*') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
