<?php
// Railway env vars take precedence; falls back to localhost defaults.
$db_host = getenv('MYSQLHOST')     ?: 'localhost';
$db_user = getenv('MYSQLUSER')     ?: 'root';
$db_pass = getenv('MYSQLPASSWORD') ?: '';
$db_name = getenv('MYSQLDATABASE') ?: 'steam_tracker';
$db_port = (int)(getenv('MYSQLPORT') ?: 3306);

$conn = mysqli_connect($db_host, $db_user, $db_pass, $db_name, $db_port);
if (!$conn) die("Connection failed: " . mysqli_connect_error());
mysqli_set_charset($conn, 'utf8mb4');

// Auto-create tables on first connection.
mysqli_query($conn, "CREATE TABLE IF NOT EXISTS games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(500),
    cluster_label VARCHAR(100),
    is_anomaly BOOLEAN DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

mysqli_query($conn, "CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    price_date DATE NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

mysqli_query($conn, "CREATE TABLE IF NOT EXISTS review_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    review_date DATE NOT NULL,
    pos_reviews INT DEFAULT 0,
    neg_reviews INT DEFAULT 0,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

mysqli_query($conn, "CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

mysqli_query($conn, "CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    UNIQUE KEY uq_wishlist (user_id, game_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

mysqli_query($conn, "CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    UNIQUE KEY uq_cart (user_id, game_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
