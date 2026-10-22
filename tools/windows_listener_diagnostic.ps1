param(
    [ValidateSet('wake','dictation')][string]$Mode = 'wake',
    [string]$WakeWord = 'Yu',
    [double]$Timeout = 60,
    [string]$AudioPath = ''
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
function Emit($value) { [Console]::WriteLine(($value | ConvertTo-Json -Compress -Depth 4)); [Console]::Out.Flush() }
$engine = $null
try {
    Add-Type -AssemblyName System.Speech
    $info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Where-Object { $_.Culture.TwoLetterISOLanguageName -eq 'es' } | Select-Object -First 1
    if (-not $info) { throw 'No hay reconocedor de voz de Windows en espanol instalado.' }
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($info)
    $engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(600)
    $engine.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(1000)
    $engine.BabbleTimeout = [TimeSpan]::FromSeconds(15)
    if ($Mode -eq 'wake') {
        $aliases = New-Object System.Speech.Recognition.Choices
        $aliases.Add([string[]]@($WakeWord, 'iu', ('y' + [char]250)))
        $name = New-Object System.Speech.Recognition.GrammarBuilder
        $name.Culture = $info.Culture
        $name.Append($aliases)
        $single = New-Object System.Speech.Recognition.Grammar($name)
        $single.Name = 'wake'
        $engine.LoadGrammar($single)
        $phrase = New-Object System.Speech.Recognition.GrammarBuilder
        $phrase.Culture = $info.Culture
        $phrase.Append($aliases)
        $phrase.AppendDictation()
        $full = New-Object System.Speech.Recognition.Grammar($phrase)
        $full.Name = 'wake_command'
        $engine.LoadGrammar($full)
    } else {
        $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    }
    if ($AudioPath) { $engine.SetInputToWaveFile($AudioPath) }
    else { $engine.SetInputToDefaultAudioDevice() }
    Emit @{type='ready'; culture=$info.Culture.Name; mode=$Mode}
    $deadline = [DateTime]::UtcNow.AddSeconds($Timeout)
    while ([DateTime]::UtcNow -lt $deadline) {
        $remaining = [Math]::Min(2, ($deadline - [DateTime]::UtcNow).TotalSeconds)
        if ($remaining -le 0) { break }
        $result = $engine.Recognize([TimeSpan]::FromSeconds($remaining))
        if ($result) {
            Emit @{type='result'; text=$result.Text; confidence=[double]$result.Confidence; grammar=$result.Grammar.Name}
            if ($result.Confidence -ge 0.60) { break }
        }
        if ($AudioPath) { break }
    }
} catch {
    Emit @{type='error'; message=$_.Exception.Message}
    exit 1
} finally {
    if ($engine) { $engine.Dispose() }
}
