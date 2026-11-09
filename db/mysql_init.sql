-- Jalankan pada MySQL. Tidak menghapus tabel/data yang sudah ada.
CREATE DATABASE IF NOT EXISTS task_strattegy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE task_strattegy;

CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    daily_quota INT UNSIGNED NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tasks (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    scheduled_time TIME NOT NULL,
    action VARCHAR(100) NOT NULL,
    parameters JSON NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_tasks_due (enabled, scheduled_time)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS task_runs (
    id CHAR(36) PRIMARY KEY,
    task_id CHAR(36) NOT NULL,
    user_id CHAR(36) NOT NULL,
    scheduled_date DATE NOT NULL,
    status ENUM('running','succeeded','failed','rejected_quota') NOT NULL,
    message TEXT,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY one_run_per_task_per_day (task_id, scheduled_date),
    INDEX idx_runs_quota (user_id, scheduled_date)
) ENGINE=InnoDB;
