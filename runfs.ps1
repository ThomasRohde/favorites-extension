# Docker Container Management Script

# Define variables
$containerName = "intelligent-favorites-server"
$imageName = "intelligent-favorites-server"
$dockerfilePath = "."  # Adjust this if your Dockerfile is in a different directory
$logFile = "docker_management.log"

# Initialize logging
function Write-Log {
    param(
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $logFile
    Write-Host $Message
}

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        $null = docker info
        return $true
    }
    catch {
        Write-Log "Error: Docker is not running or not accessible."
        return $false
    }
}

# Function to stop the container
function Stop-Container {
    if (docker ps -q -f name=$containerName) {
        Write-Log "Stopping container $containerName..."
        docker stop $containerName
        if ($?) {
            Write-Log "Container stopped successfully."
        }
        else {
            Write-Log "Failed to stop container."
        }
    }
    else {
        Write-Log "Container $containerName is not running."
    }
}

# Function to remove the container
function Remove-Container {
    if (docker ps -a -q -f name=$containerName) {
        Write-Log "Removing container $containerName..."
        docker rm $containerName
        if ($?) {
            Write-Log "Container removed successfully."
        }
        else {
            Write-Log "Failed to remove container."
        }
    }
    else {
        Write-Log "Container $containerName does not exist."
    }
}

# Function to remove the image
function Remove-Image {
    if (docker images -q $imageName) {
        Write-Log "Removing image $imageName..."
        docker rmi $imageName
        if ($?) {
            Write-Log "Image removed successfully."
        }
        else {
            Write-Log "Failed to remove image."
        }
    }
    else {
        Write-Log "Image $imageName does not exist."
    }
}

# Function to build the image
function Build-Image {
    Write-Log "Building image $imageName..."
    docker build -t $imageName $dockerfilePath
    if ($?) {
        Write-Log "Image built successfully."
    }
    else {
        Write-Log "Failed to build image."
        exit 1
    }
}

# Function to start the container
function Start-Container {
    Write-Log "Starting container $containerName..."
    docker run -d --name $containerName `
        -p 8000:8000 `
        -v "${HOME}/Favorites/sqlite:/data/sqlite" `
        -v "${HOME}/Favorites/chroma:/data/chroma" `
        -e SQLITE_DIR=/data/sqlite `
        -e CHROMA_DIR=/data/chroma `
        -e ANTHROPIC_API_KEY=$env:ANTHROPIC_API_KEY `
        $imageName
    if ($?) {
        Write-Log "Container started successfully."
    }
    else {
        Write-Log "Failed to start container."
        exit 1
    }
}

# Main execution
Write-Log "Starting Docker management script..."

if (-not (Test-DockerRunning)) {
    exit 1
}

# Confirm before proceeding
$confirm = Read-Host "This script will stop, remove, rebuild, and restart the $containerName container. Do you want to proceed? (y/n)"
if ($confirm -ne "y") {
    Write-Log "Operation cancelled by user."
    exit 0
}

Stop-Container
Remove-Container
Remove-Image
Build-Image
Start-Container

Write-Log "Docker management script completed."