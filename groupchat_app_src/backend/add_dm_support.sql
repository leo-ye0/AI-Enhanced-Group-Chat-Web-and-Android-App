-- Add DM support to messages table
ALTER TABLE messages ADD COLUMN dm_user_id INT NULL;
ALTER TABLE messages ADD CONSTRAINT fk_dm_user FOREIGN KEY (dm_user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE messages ADD INDEX idx_dm_user (dm_user_id);
