# Madden NFL 08 Recompiled - builds the game itself.
# Run by setup.ps1, which it shares its variables and helper functions with.

if (-not $failed) {
    try {
        Write-Host ""
        Write-Host "--- Building the game ---"
        $GameBuildDir = Join-Path $RepoRoot "out\build\win-amd64-relwithdebinfo"
        $GeneratedDir = Join-Path $RepoRoot "generated\default"
        $AssetsDir    = Join-Path $RepoRoot "assets"
        $DistDir      = Join-Path $RepoRoot "dist"

        # 1. Make "assets" point at the game folder (the manifest refers to assets\default.xex)
        $gameFull = (Resolve-Path -LiteralPath $GameDataRoot).Path.TrimEnd('\')
        $item = Get-Item -LiteralPath $AssetsDir -Force -ErrorAction SilentlyContinue
        if ($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            $current = [string](@($item.Target)[0])
            if ($current.TrimEnd('\') -ieq $gameFull) {
                Ok "assets already points at your game files"
            } else {
                [IO.Directory]::Delete($AssetsDir)
            }
        } elseif ($item) {
            if (-not (Test-Path -LiteralPath (Join-Path $AssetsDir "default.xex"))) {
                throw "A folder named 'assets' already exists here but has no default.xex in it. Move it away and run setup again."
            }
            Ok "using the game files already in the assets folder"
        }
        if (-not (Test-Path -LiteralPath $AssetsDir)) {
            try { New-Item -ItemType Junction -Path $AssetsDir -Target $gameFull | Out-Null }
            catch { throw ("Could not link your game folder (it has to be on a local drive): " + $_.Exception.Message) }
            Ok "assets now points at $gameFull"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $AssetsDir "default.xex"))) { throw "default.xex cannot be reached through the assets folder" }

        # 2. Configure
        Import-VsEnvironment
        $prefix = $SdkInstallDir.Replace('\', '/')
        $gameCfg = @("--preset", "win-amd64-relwithdebinfo", ("-DCMAKE_PREFIX_PATH=" + $prefix))
        Invoke-Step -Label "Configuring the game" -Exe "cmake" -ToolArgs $gameCfg -WorkDir $RepoRoot -LogName "game-configure"

        # 3. Generate the code from default.xex, then configure again so it is included
        Invoke-Step -Label "Generating the game's code from your default.xex" -Exe "cmake" -ToolArgs @("--build", $GameBuildDir, "--target", "madden08_codegen") -WorkDir $RepoRoot -LogName "game-codegen"
        if (-not (Test-Path (Join-Path $GeneratedDir "sources.cmake"))) { throw "Code generation finished, but generated\default\sources.cmake was not created" }
        $genFiles = @(Get-ChildItem $GeneratedDir -Recurse -File)
        Ok ("generated code: {0} files, {1:N0} MB" -f $genFiles.Count, (($genFiles | Measure-Object Length -Sum).Sum / 1MB))
        Invoke-Step -Label "Configuring the game again (to include the generated code)" -Exe "cmake" -ToolArgs $gameCfg -WorkDir $RepoRoot -LogName "game-configure2"

        # A precompiled header older than the regenerated header makes the compiler refuse to build.
        $pch = Join-Path $GameBuildDir "CMakeFiles\madden08_recomp.dir\cmake_pch.hxx.pch"
        $pchHdr = Join-Path $GeneratedDir "madden08_pch.h"
        if ((Test-Path $pch) -and (Test-Path $pchHdr) -and ((Get-Item $pchHdr).LastWriteTime -gt (Get-Item $pch).LastWriteTime)) { Remove-Item $pch -Force }

        # 4. Compile
        $ramGB = [int][math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
        $jobs = [int][math]::Max(2, [math]::Min(6, [math]::Floor($ramGB / 4)))
        $jobs = [int][math]::Min($jobs, [Environment]::ProcessorCount)
        Write-Host "Compiling with $jobs parallel jobs (this PC has $ramGB GB of RAM). This is the longest step."
        Invoke-Step -Label "Building the game" -Exe "cmake" -ToolArgs @("--build", $GameBuildDir, "--parallel", [string]$jobs) -WorkDir $RepoRoot -LogName "game-build"

        # 5. Stage the dist folder
        $exe = Join-Path $GameBuildDir "madden08.exe"
        if (-not (Test-Path $exe)) { throw "The build finished but madden08.exe was not created" }
        New-Item -ItemType Directory -Force $DistDir | Out-Null
        Copy-Item $exe $DistDir -Force
        foreach ($dll in @("rexruntimerd.dll", "rexgpu-xenosrd.dll", "TracyClientrd.dll")) {
            $src = Join-Path $SdkInstallDir ("bin\" + $dll)
            if (-not (Test-Path $src)) { throw "missing in the SDK: $dll" }
            Copy-Item $src $DistDir -Force
        }
        $bat = "@echo off`r`ncd /d `"%~dp0`"`r`nstart `"`" `"%~dp0madden08.exe`" --game_data_root=`"$AssetsDir`" --gpu_plugin=xenos --mnk_mode=true --render_target_path_d3d12=rov --log_level=error`r`n"
        Set-Content -Path (Join-Path $DistDir "Launch Madden NFL 08.bat") -Value $bat -Encoding ascii
        Ok ("game built: dist\madden08.exe ({0:N1} MB)" -f ((Get-Item (Join-Path $DistDir "madden08.exe")).Length / 1MB))
    } catch {
        Bad $_.Exception.Message
        $bl = Join-Path $LogDir "game-build.out.log"
        if (Test-Path $bl) {
            Write-Host "---- first errors in the game build log ----"
            Select-String -Path $bl -Pattern 'error' | Select-Object -First 8 | ForEach-Object { $_.Line }
        }
    }
}
