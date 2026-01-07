Param(
    [string] $TaskName = "AITrading_DailyFeatureMonitor",
    [string] $ScriptPath = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)\\daily_feature_monitor.py",
    [string] $PythonExe = "python"
)

# Registers a scheduled task to run the daily monitor at 06:00 local time.
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force

Write-Output "Registered scheduled task '$TaskName' to run $ScriptPath daily at 06:00."
