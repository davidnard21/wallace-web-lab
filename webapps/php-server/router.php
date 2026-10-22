<?php
// Router for the built-in PHP server (php -S).
// - "/"            -> 302 redirect to /feed
// - "/feed"        -> serves /srv/feed.mp4 (the "TV feed") with Range support
// - anything else  -> fall through to the built-in server (serves /uploads)

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($uri === '/' || $uri === '/index.php') {
    header('Location: /feed', true, 302);
    exit;
}

if ($uri === '/feed') {
    $file = '/srv/feed.mp4';
    $size = filesize($file);

    header('Content-Type: video/mp4');
    header('Accept-Ranges: bytes');
    header('Cache-Control: no-cache');

    // Minimal Range support so browsers can seek in the video
    $start = 0;
    $end = $size - 1;
    $status = 200;

    if (isset($_SERVER['HTTP_RANGE']) && preg_match('/bytes=(\d*)-(\d*)/', $_SERVER['HTTP_RANGE'], $m)) {
        if ($m[1] !== '') {
            $start = (int)$m[1];
        }
        if ($m[2] !== '') {
            $end = min((int)$m[2], $size - 1);
        }
        if ($start > $end || $start >= $size) {
            http_response_code(416);
            header("Content-Range: bytes */$size");
            exit;
        }
        $status = 206;
        http_response_code(206);
        header("Content-Range: bytes $start-$end/$size");
    }

    header("Content-Length: " . ($end - $start + 1));

    $fp = fopen($file, 'rb');
    fseek($fp, $start);
    $remaining = $end - $start + 1;
    while ($remaining > 0 && !feof($fp)) {
        $chunk = fread($fp, min(8192, $remaining));
        echo $chunk;
        $remaining -= strlen($chunk);
        flush();
    }
    fclose($fp);
    exit;
}

// Let the built-in server handle everything else (static files in /uploads)
return false;
