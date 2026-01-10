# Register Windows Scheduled Task for Continuous Live Trading
# Run this in PowerShell as Administrator to schedule continuous trading

Param(
    [string]$TaskName = "AITrading_ContinuousLiveTrading",
    [string]$ScriptPath = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\run_continuous_trading.py",
    [string]$PythonExe = "python",
    [string]$WorkingDir = "$(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition))",
    [string]$Interval = "3600",  # 1 hour in seconds
    [string]$MinProfitBp = "4.0",
    [string]$MinConfidence = "0.65",
    [switch]$Aggressive
)

Write-Host "Registering scheduled task for continuous live trading..."
Write-Host "Task Name: $TaskName"
Write-Host "Script: $ScriptPath"
Write-Host "Working Directory: $WorkingDir"
Write-Host "Interval (seconds): $Interval"

# Build command line arguments
$Arguments = "`"$ScriptPath`" --interval $Interval --min-profit-bp $MinProfitBp --min-confidence $MinConfidence"
if ($Aggressive) {
    $Arguments += " --aggressive"
}

# Create scheduled task action
$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument $Arguments `
    -WorkingDirectory $WorkingDir

# Create trigger - run at startup and every X minutes
$trigger = New-ScheduledTaskTrigger -AtStartup
# For recurring, we'll let the Python script handle the loop

# Create principal with high privileges
$principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Force `
        -ErrorAction Stop
    
    Write-Host "✓ Successfully registered scheduled task: $TaskName"
    Write-Host "  The task will start automatically at system boot"
    Write-Host "  and run continuously with $Interval second intervals"
    Write-Host ""
    Write-Host "To check the task status:"
    Write-Host "  Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "To view the task logs:"
    Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "To manually start the task:"
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "To stop the task:"
    Write-Host "  Stop-ScheduledTask -TaskName '$TaskName'"
}
catch {
    Write-Host "✗ Failed to register task: $_"
    Write-Host "Make sure you're running PowerShell as Administrator"
    exit 1
}
