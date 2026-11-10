# Synthetic evaluation fixtures only; these are TTS, not microphone recordings.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$projectRoot = Split-Path -Parent $PSScriptRoot
$audioDir = Join-Path $projectRoot 'tmp\synthetic-audio'
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.SelectVoice('Microsoft Zira Desktop')
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $samples = @{
        'english' = 'I bought a mixer grinder online for three thousand five hundred rupees. It arrived damaged. I have the invoice and photos. I want a refund.'
        'hinglish' = 'Maine landlord ko twenty thousand rupees security deposit diya tha. Room khaali kar diya, lekin paise wapas nahi mile.'
    }
    foreach ($name in @('english','hinglish')) {
        $synth.SetOutputToWaveFile((Join-Path $audioDir ($name + '.wav')), $format)
        $synth.Speak($samples[$name])
        $synth.SetOutputToNull()
    }
    Write-Output 'Created two local synthetic TTS recordings; no API calls.'
} finally { $synth.Dispose() }
