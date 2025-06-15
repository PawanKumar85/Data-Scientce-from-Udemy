-- USER table 
CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- UPLOADED resumes tracking 
CREATE TABLE IF NOT EXISTS uploaded_resumes(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    upload_status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- PARSED resume data
CREATE TABLE IF NOT EXISTS parsed_data(
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    skills TEXT,
    education TEXT,
    experience TEXT,
    raw_text TEXT,
    parsing_status VARCHAR(50) DEFAULT 'pending', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES uploaded_resumes(id) ON DELETE CASCADE
);

-- JOB DESCRIPTION data
CREATE TABLE IF NOT EXISTS jd_data(
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL,
    jb_text TEXT,
    required_skills TEXT,
    experience_level VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES uploaded_resumes(id) ON DELETE CASCADE
);

-- ANALYTICES RESULTS
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL,
    skill_match_percentage DECIMAL(5,2),
    experience_score DECIMAL(5,2),
    pie_chart_path VARCHAR(500),
    bar_chart_path VARCHAR(500),
    analytics_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES uploaded_resumes(id) ON DELETE CASCADE
);

-- PROCESSING status tracking
CREATE TABLE IF NOT EXISTS processing_status(
    id SERIAL PRIMARY KEY,
    resume_id INTEGER NOT NULL,
    upload_status BOOLEAN DEFAULT FALSE,
    parsing_status BOOLEAN DEFAULT FALSE,
    analytics_status BOOLEAN DEFAULT FALSE,
    ai_feedback_status BOOLEAN DEFAULT FALSE,
    finalized_status BOOLEAN DEFAULT FALSE,
    current_step VARCHAR(100) DEFAULT 'uploaded',
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES uploaded_resumes(id) ON DELETE CASCADE
);

-- Create Indexes for better performances
CREATE INDEX IF NOT EXISTS idx_uploaded_resumes_user_id ON uploaded_resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_parsed_data_resume_id ON parsed_data(resume_id);
CREATE INDEX IF NOT EXISTS idx_analytics_resume_id ON analytics(resume_id);
CREATE INDEX IF NOT EXISTS idx_processing_status_resume_id ON processing_status(resume_id);

