<?php
// One-time data seeder. Run via: php seed.php
// On Railway: use the "Run command" panel once after first deploy.
require_once 'includes/db.php';

$data_dir = __DIR__ . '/data/';
$files = glob($data_dir . '*_prices.csv');
$imported = 0; $skipped = 0;

foreach ($files as $price_file) {
    $base = basename($price_file, '_prices.csv');
    // extract AppID: last underscore-separated numeric token
    if (!preg_match('/^(.+)_(\d+)$/', $base, $m)) continue;
    $game_name = str_replace('_', ' ', $m[1]);
    $app_id    = $m[2];

    // review file
    $rev_file = $data_dir . $base . '_reviews.csv';

    // upsert game
    $esc = mysqli_real_escape_string($conn, $game_name);
    mysqli_query($conn, "INSERT IGNORE INTO games (name) VALUES ('$esc')");
    $res = mysqli_query($conn, "SELECT id FROM games WHERE name='$esc' LIMIT 1");
    $row = mysqli_fetch_assoc($res);
    if (!$row) { $skipped++; continue; }
    $gid = $row['id'];

    // prices
    if (($fh = fopen($price_file, 'r')) !== false) {
        $header = true;
        while (($cols = fgetcsv($fh)) !== false) {
            if ($header) { $header = false; continue; }
            if (count($cols) < 2) continue;
            $date  = mysqli_real_escape_string($conn, trim($cols[0]));
            $price = floatval(trim($cols[1]));
            mysqli_query($conn, "INSERT IGNORE INTO price_history (game_id,price_date,price)
                                  VALUES ($gid,'$date',$price)");
        }
        fclose($fh);
    }

    // reviews
    if (file_exists($rev_file) && ($fh = fopen($rev_file, 'r')) !== false) {
        $header = true;
        while (($cols = fgetcsv($fh)) !== false) {
            if ($header) { $header = false; continue; }
            if (count($cols) < 3) continue;
            $date = mysqli_real_escape_string($conn, trim($cols[0]));
            $pos  = intval(trim($cols[1]));
            $neg  = intval(trim($cols[2]));
            $cat  = isset($cols[3]) ? mysqli_real_escape_string($conn, trim($cols[3])) : '';
            mysqli_query($conn, "INSERT IGNORE INTO review_history (game_id,review_date,pos_reviews,neg_reviews)
                                  VALUES ($gid,'$date',$pos,$neg)");
            if ($cat) mysqli_query($conn, "UPDATE games SET category='$cat' WHERE id=$gid AND (category IS NULL OR category='')");
        }
        fclose($fh);
    }
    $imported++;
}

echo "Done. Imported: $imported games, skipped: $skipped\n";
