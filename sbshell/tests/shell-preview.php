<?php
// Run: php8.2 sbshell/tests/shell-preview.php
// Verify Bash highlighting and that direct links open source, not a raw file.
require_once __DIR__ . "/../cruff/preview.php";
function check_shell($ok, $message){
    if(!$ok) throw new RuntimeException($message);
}
$root = sys_get_temp_dir() . "/sb-shell-" . bin2hex(random_bytes(6));
mkdir($root);
$router = realpath(__DIR__ . "/../cruff/index.php");
$source = <<<'BASH'
#!/usr/bin/env bash
# shell script comment
if [[ ${FLAG:-off} == "on" ]]; then
    echo "$FLAG"
fi
BASH;
$source .= "\n";
$process = null;
$pipes = [];
try{
    foreach(["sh", "bash"] as $extension){
        $file = "$root/example.$extension";
        file_put_contents($file, $source);
        check_shell(sb_preview_type($file) === "code", ".$extension must be code.");
        check_shell(sb_code_language($file) === "bash", ".$extension must use Bash syntax.");
        ob_start();
        sb_code_file($file);
        $preview = ob_get_clean();
        check_shell(str_contains($preview, 'sb-code-label">bash'), "Bash language label missing.");
        check_shell(str_contains($preview, 'class="sb-syn-keyword">if</span>'), "Bash keywords must be highlighted.");
        check_shell(str_contains($preview, 'class="sb-syn-comment"># shell script comment</span>'), "Shell comments must be highlighted.");
        check_shell(str_contains($preview, 'class="sb-syn-variable">${FLAG:-off}</span>'), "Shell variables must be highlighted.");
    }

    // Start the actual PHP development server to test its file routing.
    $socket = stream_socket_server("tcp://127.0.0.1:0", $errorCode, $errorMessage);
    check_shell($socket !== false, "Cannot reserve a test port: " . $errorMessage);
    $endpoint = stream_socket_get_name($socket, false);
    fclose($socket);
    $port = (int)substr(strrchr($endpoint, ":"), 1);
    $process = proc_open([PHP_BINARY, "-S", "127.0.0.1:$port", "-t", $root, $router],
        [0 => ["pipe", "r"], 1 => ["pipe", "w"], 2 => ["pipe", "w"]], $pipes);
    check_shell(is_resource($process), "Cannot start the PHP server.");
    fclose($pipes[0]);
    foreach(["sh", "bash"] as $extension){
        $url = "http://127.0.0.1:$port/example.$extension";
        $html = false;
        for($attempt = 0; $attempt < 30; $attempt++){
            $html = @file_get_contents($url);
            if($html !== false) break;
            usleep(50000);
        }
        check_shell($html !== false, "Shell source route was not available.");
        check_shell(str_contains($html, "<!doctype html>"), "Direct .$extension link should return an HTML viewer.");
        check_shell(str_contains($html, 'sb-code-label">bash'), "Direct .$extension view should use Bash highlighting.");
        check_shell(str_contains($html, 'class="sb-syn-keyword">if</span>'), "Direct .$extension view should highlight Bash syntax.");
        check_shell(str_contains($html, 'example.' . $extension . '?raw=1'), "Direct .$extension view needs a raw-file link.");
        check_shell(@file_get_contents($url . "?raw=1") === $source, "Raw .$extension request must preserve original bytes.");
    }
    echo "SB Shell .sh/.bash highlighting, source viewer and raw access passed.\n";
}finally{
    if(is_resource($process)){
        proc_terminate($process);
        foreach([1, 2] as $i) if(isset($pipes[$i]) && is_resource($pipes[$i])) fclose($pipes[$i]);
        proc_close($process);
    }
    foreach(glob("$root/*") ?: [] as $file) unlink($file);
    rmdir($root);
}
