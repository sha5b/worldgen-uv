# File: worldgen-uv/provision-worldgen-wsl.ps1
# Purpose: PowerShell automation to provision a reproducible WSL2 Ubuntu environment for WorldGen using uv.
# Connection: Ensures WSL and Ubuntu-22.04 are available, translates the Windows project path to WSL,
# then invokes the Linux-side setup script `setup-wsl.sh` inside the project.

param(
    [string]$DistroName = "Ubuntu-22.04"
)

$ErrorActionPreference = 'Stop'

function Ensure-WSL {
    Write-Host "[WSL] Checking WSL installation..."
    try {
        wsl -l -v | Out-Null
    } catch {
        Write-Host "[WSL] WSL not found. Enabling optional components and installing WSL..."
        # Enable features (requires admin)
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart | Out-Null
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart | Out-Null
        Write-Host "[WSL] Installing default WSL..."
        wsl --install
        Write-Warning "[WSL] A reboot may be required. Please reboot and re-run this script if prompted."
    }
}

function Ensure-Distro {
    param([string]$Name)
    Write-Host "[WSL] Ensuring distro '$Name' exists..."
    $list = wsl -l -v 2>$null
    if ($list -notmatch [regex]::Escape($Name)) {
        Write-Host "[WSL] Installing $Name..."
        wsl --install -d $Name
        Write-Warning "[WSL] If this is the first install, you may need to create a UNIX user and then re-run this script."
    } else {
        Write-Host "[WSL] Distro '$Name' found."
    }
}

function Convert-ToWSLPath {
    param([string]$WinPath)
    # Convert e.g. C:\Users\Name\repo to /mnt/c/Users/Name/repo
    $drive = $WinPath.Substring(0,1).ToLower()
    $rest = $WinPath.Substring(2).Replace('\\','/')
    return "/mnt/$drive/$rest"
}

Ensure-WSL
Ensure-Distro -Name $DistroName

# Determine project root (directory containing this script)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WSLPath = Convert-ToWSLPath -WinPath $ProjectRoot

Write-Host "[WSL] Project directory (Windows): $ProjectRoot"
Write-Host "[WSL] Project directory (WSL):     $WSLPath"

# Ensure setup script has execute permission and run it
$Command = "cd $WSLPath && chmod +x ./setup-wsl.sh && bash ./setup-wsl.sh"
Write-Host "[WSL] Running setup inside '$DistroName'..."
wsl -d $DistroName -- bash -lc $Command
