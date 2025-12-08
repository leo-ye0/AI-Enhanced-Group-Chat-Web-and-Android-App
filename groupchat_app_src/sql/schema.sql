-- Optional: If you prefer manual SQL instead of SQLAlchemy auto-creation
CREATE DATABASE IF NOT EXISTS groupchat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'chatuser'@'localhost' IDENTIFIED BY 'ChatPass123!';
GRANT ALL PRIVILEGES ON groupchat.* TO 'chatuser'@'localhost';
FLUSH PRIVILEGES;

USE groupchat;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(100) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  content TEXT NOT NULL,
  is_bot BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Project Settings Table
CREATE TABLE IF NOT EXISTS project_settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ship_date DATE NULL,
  group_id INT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_project_settings_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Project Milestones Table
CREATE TABLE IF NOT EXISTS milestones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  description TEXT NULL,
  assigned_roles VARCHAR(255) NULL,
  risk_level VARCHAR(50) NULL,
  dependencies TEXT NULL,
  created_by INT NOT NULL,
  group_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_milestone_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_milestone_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Decision Log for Project Audit Trail
CREATE TABLE IF NOT EXISTS decision_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  decision_text VARCHAR(500) NOT NULL,
  rationale TEXT NOT NULL,
  category ENUM('Methodology', 'Logistics', 'Topic') NOT NULL,
  decision_type ENUM('locked', 'resolved', 'consensus') NOT NULL,
  created_by VARCHAR(100) NOT NULL,
  chat_reference_id INT NULL,
  group_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_decision_log_message FOREIGN KEY (chat_reference_id) REFERENCES messages(id) ON DELETE SET NULL,
  CONSTRAINT fk_decision_log_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dialectic Engine: Decision Log Table
CREATE TABLE IF NOT EXISTS decisions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conflict_id VARCHAR(255) NOT NULL,
  triggering_conflict TEXT NOT NULL,
  selected_option ENUM('A', 'B', 'C') NOT NULL,
  reasoning TEXT NOT NULL,
  decided_by INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_decision_user FOREIGN KEY (decided_by) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_conflict_id (conflict_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Voting System: Active Conflicts Table
CREATE TABLE IF NOT EXISTS active_conflicts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conflict_id VARCHAR(255) NOT NULL UNIQUE,
  user_statement TEXT NOT NULL,
  conflicting_evidence TEXT NOT NULL,
  source_file VARCHAR(255) NOT NULL,
  severity ENUM('low', 'medium', 'high') NOT NULL,
  reason TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  is_resolved BOOLEAN DEFAULT FALSE,
  group_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_conflict_id (conflict_id),
  INDEX idx_expires_at (expires_at),
  CONSTRAINT fk_active_conflicts_group FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Voting System: Votes Table
CREATE TABLE IF NOT EXISTS conflict_votes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conflict_id VARCHAR(255) NOT NULL,
  user_id INT NOT NULL,
  selected_option ENUM('A', 'B', 'C') NOT NULL,
  reasoning TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_vote_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user_vote (conflict_id, user_id),
  INDEX idx_conflict_id (conflict_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
