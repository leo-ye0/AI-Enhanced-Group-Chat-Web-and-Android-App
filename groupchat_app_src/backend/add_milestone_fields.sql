-- Add new fields to milestones table
USE groupchat;

ALTER TABLE milestones 
ADD COLUMN description TEXT NULL AFTER end_date,
ADD COLUMN assigned_roles VARCHAR(255) NULL AFTER description,
ADD COLUMN risk_level VARCHAR(50) NULL AFTER assigned_roles,
ADD COLUMN dependencies TEXT NULL AFTER risk_level;
