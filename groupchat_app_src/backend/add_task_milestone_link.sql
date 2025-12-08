-- Add milestone_id to tasks table
USE groupchat;

ALTER TABLE tasks 
ADD COLUMN milestone_id INT NULL AFTER due_date,
ADD CONSTRAINT fk_task_milestone FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE SET NULL;
