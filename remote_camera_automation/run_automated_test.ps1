# Set the paths for the text file and the Python virtual environment
$filePath = "C:\Users\Natasha_\Desktop\automate.txt"
#$venvPath = 'C:\Users\Louis\Desktop\camera_alignment\venv'


# Read the content of the text file
$content = Get-Content -Path $filePath

# Define the Python interpreter command
$pythonCommand = 'C:\Users\Natasha_\AppData\Local\Programs\Python\Python311\python.exe' # Change Directory for username here

# Run each instance of the Python script in the background
foreach ($line in $content) {
    $processParams = @{
        FilePath = $pythonCommand
        ArgumentList = @("C:\Users\Natasha_\Desktop\automated_test_script.py", $line) 
        Wait = $false
    }
    Start-Process @processParams
    Start-Sleep -Seconds 20
}


# Wait for all background jobs to finish
Get-Job | Wait-Job