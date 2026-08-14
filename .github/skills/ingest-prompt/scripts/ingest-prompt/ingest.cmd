@echo off
REM ingest.cmd - Windows-native launcher for the ingest-prompt binary.
REM Pass a file path as %1, or pipe input via stdin.
"%~dp0ingest-prompt.exe" %*
